# BF/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponse, Http404
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import quote  
from datetime import timedelta # <-- NEW: Added for standard token expiry management

# Import necessary third-party libraries
import requests 

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

# Import models and utilities
from movies.models import Movies, DownloadToken, DirectDownloadToken
from movies.telegram_utils import TelegramFileManager
from movies.serializers import MovieSerializer
# from .views import series_stream_page

# NEW IMPORTS FOR MEMBERSHIP KEY SYSTEM
from users.views import membership_required # <-- NEW

import json
import logging
from telegram import Update
from telegram.ext import Application
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Simple bot initialization for webhook
from telegram import Update
from telegram.ext import Application, CommandHandler
from django.views.decorators.csrf import csrf_exempt
import json

from users.models import MovieVisit


from datetime import timedelta # <-- NEW: Added for standard token expiry management
# ⬇️ ADD THIS IMPORT ⬇️
from django.views.decorators.cache import never_cache

from movies.models import Movies, DownloadToken, DirectDownloadToken, Episodes

telegram_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
initialized = False

async def init_bot():
    global initialized
    if initialized:
        return
    
    from movies.bot_handlers import handle_start_command
    telegram_app.add_handler(CommandHandler("start", handle_start_command))

    await telegram_app.initialize()   # REQUIRED in webhook mode

    initialized = True
    print("Telegram bot initialized")


# --- CORE VIEWS ---

@membership_required # <-- NEW: Membership required to view home page
@never_cache 
def Home(request):
    query = request.GET.get("q", "")
    if query:
        all_movies = Movies.objects.filter(title__icontains=query)
    else:
        all_movies = Movies.objects.all().order_by('-upload_date')
    
    paginator = Paginator(all_movies, 12)
    page = request.GET.get('page')
    movies_page = paginator.get_page(page)

    return render(request, "index.html", {
        "movies": movies_page,
        "query": query,
    })

@membership_required # <-- NEW: Membership required to view movie details
@membership_required
def Movie(request, slug):
    movie = get_object_or_404(Movies, slug=slug)

    # ✅ RECORD LAST VISITED MOVIE
    if request.user.is_authenticated:
        MovieVisit.record_visit(request.user, movie)

    # Check if download is available via Telegram file_id OR direct link
    sd_download_url = bool(movie.SD_telegram_file_id or movie.SD_link)
    hd_download_url = bool(movie.HD_telegram_file_id or movie.HD_link)

    return render(request, "movie_detail.html", {
        "movie": movie,
        "sd_download_url": sd_download_url,
        "hd_download_url": hd_download_url,
    })



@membership_required
def series_stream_page(request, slug):
    """
    Handles the merged Series Stream Page (Player + Episode List).
    Uses URL query params: ?e=<episode_num>&q=<quality>
    """
    movie = get_object_or_404(Movies, slug=slug)
    
    if movie.type not in ['tv', 'anime']:
         # If not a series, redirect back to the detail page.
         return redirect('movie_detail', slug=slug)

    # 1. Get all episodes
    episodes = movie.episodes_set.all().order_by('episode_number')
    if not episodes:
        return render(request, 'episode.html', {'movie': movie, 'episodes': []})

    # 2. Determine initial episode and quality from query params or default
    current_episode = episodes.first() # Default to the first episode
    episode_num = current_episode.episode_number
    current_quality = 'SD'
    stream_url = ""

    try:
        # Check for query parameters (?e=X&q=Y)
        requested_ep_num = int(request.GET.get('e', episode_num))
        requested_quality = request.GET.get('q', current_quality).upper()
        
        # Try to find the requested episode
        current_episode = episodes.get(episode_number=requested_ep_num)
        episode_num = requested_ep_num
        current_quality = requested_quality

        # 3. Get stream URL
        if current_quality == 'SD':
            stream_url = current_episode.streamSD_link
        elif current_quality == 'HD':
            stream_url = current_episode.streamHD_link
        
        # Fallback to the other quality if the requested one is missing
        if not stream_url:
            if current_quality == 'SD' and current_episode.streamHD_link:
                stream_url = current_episode.streamHD_link
                current_quality = 'HD'
            elif current_quality == 'HD' and current_episode.streamSD_link:
                stream_url = current_episode.streamSD_link
                current_quality = 'SD'
        
    except (ValueError, TypeError, Episodes.DoesNotExist):
        # Fallback to first episode's default quality if query params fail
        current_episode = episodes.first()
        episode_num = current_episode.episode_number
        current_quality = 'SD'
        stream_url = current_episode.streamSD_link or current_episode.streamHD_link or ""


    context = {
        'movie': movie,
        'episodes': episodes,
        'stream_url': stream_url,
        'current_episode': current_episode,
        'current_quality': current_quality,
    }
    
    # Renders the combined stream/episode list page
    return render(request, 'episode.html', context)


# --- NEW: Direct Movie Stream View ---
# This is the destination when a user clicks 'Stream SD/HD' on a Movie detail page.
def stream_movie_view(request, quality, slug):
    movie = get_object_or_404(Movies, slug=slug)
    
    quality = quality.upper()
    
    if quality == 'SD':
        stream_url = movie.streamSD_link
        content_name = f"{movie.title} (SD)"
    elif quality == 'HD':
        stream_url = movie.streamHD_link
        content_name = f"{movie.title} (HD)"
    else:
        raise Http404("Invalid quality specified.")

    if not stream_url:
        return HttpResponse("Streaming link unavailable for this quality.", status=404)

    context = {
        'stream_url': stream_url,
        'movie': movie,
        'quality': quality,
        'content_name': content_name,
    }
    
    # Renders the stream.html iframe page
    return render(request, 'stream.html', context)


# def stream_episode_view(request, quality, slug, episode_number):
#     # 1. Get the Movie object
#     movie = get_object_or_404(Movies, slug=slug)
    
#     # 2. Get the specific Episode object
#     try:
#         episode = Episodes.objects.get(movie=movie, episode_number=episode_number)
#     except Episodes.DoesNotExist:
#         raise Http404("Episode not found.")
    
#     # 3. Determine the correct streaming link
#     quality = quality.upper()
#     if quality == 'SD':
#         stream_url = episode.streamSD_link
#         content_name = f"{movie.title} - Episode {episode_number} (SD)"
#     elif quality == 'HD':
#         stream_url = episode.streamHD_link
#         content_name = f"{movie.title} - Episode {episode_number} (HD)"
#     else:
#         raise Http404("Invalid quality specified.")

#     if not stream_url:
#         # Handle case where link is missing
#         return HttpResponse("Streaming link unavailable for this quality.", status=404)

#     context = {
#         'stream_url': stream_url,
#         'movie': movie,
#         'episode': episode,
#         'quality': quality,
#         'content_name': content_name,
#     }
    
#     # Render the stream template
#     return render(request, 'stream.html', context)
    

@membership_required # <-- NEW: Membership required to view category filter
@never_cache 
def category_filter(request, category):
    query = request.GET.get("q", "")
    movies = Movies.objects.filter(type=category)

    if query:
        movies = movies.filter(title__icontains=query)

    paginator = Paginator(movies, 12)
    page = request.GET.get('page')
    movies_page = paginator.get_page(page)

    return render(request, "category.html", {
        "movies": movies_page,
        "query": query,
        "category": category,
    })


# @membership_required 
# def stream_movie_view(request, quality, slug):
#     """
#     Renders the stream.html page with the appropriate streaming link.
#     """
#     movie = get_object_or_404(Movies, slug=slug)
#     quality = quality.upper()
#     stream_url = None
    
#     if quality == 'SD' and movie.streamSD_link:
#         stream_url = movie.streamSD_link
#     elif quality == 'HD' and movie.streamHD_link:
#         stream_url = movie.streamHD_link
    
#     if not stream_url:
#         logger.warning(f"Stream link requested for {slug} ({quality}) but no link available.")
#         # Raise 404 or render an error page
#         raise Http404("Streaming link is not available for this quality.")

#     # The movie object is needed in the template for title and back link
#     return render(request, "stream.html", {
#         "movie": movie,
#         "quality": quality,
#         "stream_url": stream_url,
#     })


# --- DOWNLOAD TOKEN VIEWS (DIRECT REDIRECT - NO SHRINKEARN) ---
@membership_required
def download_token_view(request, quality, slug):
    """
    Generates a token and redirects user DIRECTLY to download page.
    No ShrinkEarn redirection - goes straight to download.html.
    """
    # START NEW AUTH LOGIC
    # if not request.session.get('membership_key_id'): 
    #     # If not authenticated, use the decorator's logic to redirect to login_key
    #     return membership_required(lambda r: None)(request)
    # END NEW AUTH LOGIC

    movie = get_object_or_404(Movies, slug=slug)
    quality = quality.upper()

    # 1. Check file availability (Telegram file_id OR direct link)
    file_id = None
    has_telegram = False
    has_direct_link = False
    
    if quality == 'SD':
        if movie.SD_telegram_file_id:
            file_id = movie.SD_telegram_file_id
            has_telegram = True
        if movie.SD_link:
            has_direct_link = True
    elif quality == 'HD':
        if movie.HD_telegram_file_id:
            file_id = movie.HD_telegram_file_id
            has_telegram = True
        if movie.HD_link:
            has_direct_link = True
    
    # If neither Telegram nor direct link is available, show error
    if not has_telegram and not has_direct_link:
        logger.warning(f"Download link requested for {slug} ({quality}) but no file_id or direct link available.")
        return HttpResponseForbidden("Download link is not available for this quality.")

    # 2. Create the Download Token (use file_id if available, otherwise use a placeholder)
    token_instance = DownloadToken.objects.create(
        movie=movie, 
        quality=quality,
        file_id=file_id or 'direct_link_only',  # Placeholder if only direct link exists
    )

    logger.info(f"🎫 Token created: {token_instance.token}")

    # 3. Redirect DIRECTLY to download page (no ShrinkEarn)
    download_url = (
        f"/download.html?token={token_instance.token}&"
        f"title={quote(movie.title)}&"
        f"quality={quality}"
    )
    
    logger.info(f"✅ Redirecting directly to download page: {download_url}")
    return redirect(download_url)


def download_file_redirect(request, token):
    """
    Called after the user completes ShrinkEarn redirection.
    It verifies the token and redirects the user to the file-ready page.
    NOTE: This may no longer be used if you remove ShrinkEarn completely,
    but keeping it for backward compatibility with old links.
    """
    logger.info(f"📥 User landed on download_file_redirect with token: {token}")
    
    try:
        token_instance = get_object_or_404(DownloadToken, token=token)
    except Http404:
        logger.error(f"❌ Invalid token requested: {token}")
        return render(request, 'download_error.html', {
            'error_message': 'Invalid or expired download link. Please get a new link from the movie page.'
        }, status=410)

    # Check if the token is still valid (not expired)
    if not token_instance.is_valid():
        logger.warning(f"⏰ Expired token: {token}")
        token_instance.delete()
        return render(request, 'download_error.html', {
            'error_message': 'Your download link has expired. Please get a new link from the movie page.'
        }, status=410)
    
    logger.info(f"✅ Valid token, redirecting to download page")
    
    # Redirect to final download page with Telegram deep link
    return redirect(
        f"/download.html?token={token_instance.token}&"
        f"title={quote(token_instance.movie.title)}&"
        f"quality={token_instance.quality}"
    )

@membership_required
def download_page_view(request):
    """
    Renders the final download page (download.html).
    This shows the Telegram deep link and/or direct download button.
    """
    # START NEW AUTH LOGIC: Check authentication on the final download page
    # if not request.session.get('membership_key_id'): 
    #     # If not authenticated, use the decorator's logic to redirect to login_key
    #     return membership_required(lambda r: None)(request)
    # END NEW AUTH LOGIC

    token = request.GET.get('token')
    movie_title = request.GET.get('title')
    quality = request.GET.get('quality')
    
    logger.info(f"📄 Download page view: token={token}, title={movie_title}, quality={quality}")
    
    if not token or not movie_title or not quality:
        return render(request, 'download_error.html', {
            'error_message': 'Missing download parameters.'
        }, status=400)
    
    # Get the token instance to retrieve movie details
    try:
        token_instance = get_object_or_404(DownloadToken, token=token)
        movie = token_instance.movie
        
        # Check what's actually available for this movie
        quality_upper = quality.upper()
        has_telegram = False
        has_direct_link = False
        
        if quality_upper == 'SD':
            has_telegram = bool(movie.SD_telegram_file_id)
            has_direct_link = bool(movie.SD_link)
        elif quality_upper == 'HD':
            has_telegram = bool(movie.HD_telegram_file_id)
            has_direct_link = bool(movie.HD_link)
        
        # Only generate direct download token if direct link actually exists
        direct_download_url = None
        if has_direct_link:
            direct_token = get_or_create_direct_download_token(movie, quality)
            if direct_token:
                direct_download_url = request.build_absolute_uri(
                    reverse('direct_download_redirect', kwargs={'token': direct_token.token})
                )
        
        logger.info(f"✅ Availability check: Telegram={has_telegram}, Direct={has_direct_link}")
        
    except Http404:
        has_telegram = False
        has_direct_link = False
        direct_download_url = None
    
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'YourBotUsername_placeholder')
    
    context = {
        'token': token,
        'movie_title': movie_title,
        'quality': quality,
        'bot_username': bot_username,
        'telegram_deep_link': f"https://t.me/{bot_username}?start={token}",
        'has_telegram': has_telegram,
        'has_direct_link': has_direct_link,
        'direct_download_url': direct_download_url,
    }
    
    return render(request, 'download.html', context)


# --- DIRECT DOWNLOAD FUNCTIONS ---

def get_or_create_direct_download_token(movie, quality):
    """
    Get existing valid token or create new one for direct download.
    """
    # Get the original link from database
    original_link = None
    if quality.upper() == 'SD' and movie.SD_link:
        original_link = movie.SD_link
    elif quality.upper() == 'HD' and movie.HD_link:
        original_link = movie.HD_link
    
    if not original_link:
        logger.warning(f"No direct link available for {movie.title} ({quality})")
        return None
    
    # Check for existing valid token
    existing_token = DirectDownloadToken.objects.filter(
        movie=movie,
        quality=quality.upper(),
        expires_at__gt=timezone.now()
    ).first()
    
    if existing_token:
        logger.info(f"♻️ Reusing existing direct download token: {existing_token.token}")
        return existing_token
    
    # Create new token
    new_token = DirectDownloadToken.objects.create(
        movie=movie,
        quality=quality.upper(),
        original_link=original_link
    )
    
    logger.info(f"✨ Created new direct download token: {new_token.token}")
    return new_token

@membership_required
def direct_download_redirect(request, token):
    """
    Validates the direct download token and redirects to the actual file.
    """
    # START NEW AUTH LOGIC: Check authentication for final file access
    # if not request.session.get('membership_key_id'): 
    #     return membership_required(lambda r: None)(request)
    # END NEW AUTH LOGIC
    
    logger.info(f"🔗 Direct download requested with token: {token}")
    
    try:
        download_token = get_object_or_404(DirectDownloadToken, token=token)
    except Http404:
        logger.error(f"❌ Invalid direct download token: {token}")
        return render(request, 'download_error.html', {
            'error_message': 'Invalid or expired direct download link. Please get a new link from the movie page.'
        }, status=410)
    
    # Check if token is still valid
    if not download_token.is_valid():
        logger.warning(f"⏰ Expired direct download token: {token}")
        download_token.delete()
        return render(request, 'download_error.html', {
            'error_message': 'Your direct download link has expired (24 hours). Please get a new link from the movie page.'
        }, status=410)
    
    # Increment access counter
    download_token.increment_access()
    
    logger.info(f"✅ Redirecting to original link: {download_token.original_link}")
    
    # Redirect to the actual file
    return redirect(download_token.original_link)


# @membership_required 
# def episodes_list_view(request, slug):
#     """
#     Renders the episodes.html page for TV shows and Anime.
#     Fetches episodes from the new Episodes model.
#     """
#     movie = get_object_or_404(Movies, slug=slug)
    
#     if movie.type not in ['tv', 'anime']:
#         return redirect('movie_detail', slug=slug)

#     # Use the related manager to fetch all episodes for this movie
#     episodes = movie.episodes_set.all().order_by('episode_number')

#     return render(request, "episodes.html", {
#         "movie": movie,
#         "episodes": episodes,
#     })
# ⬆️ END UPDATED VIEW: episodes_list_view ⬆️


# ⬇️ UPDATE VIEW: stream_content_view ⬇️
@membership_required 
def stream_content_view(request, slug, quality, episode_num=None):
    """
    Handles streaming for both single movies and specific episodes.
    """
    movie = get_object_or_404(Movies, slug=slug)
    quality = quality.upper()
    stream_url = None
    content_name = movie.title # Default name
    
    if movie.type == 'movies' and episode_num is None:
        # 1. Logic for a regular movie
        if quality == 'SD':
            stream_url = movie.streamSD_link
        elif quality == 'HD':
            stream_url = movie.streamHD_link
    
    elif movie.type in ['tv', 'anime'] and episode_num is not None:
        # 2. Logic for a specific episode of a TV show/Anime
        try:
            episode_num = int(episode_num)
        except (TypeError, ValueError):
            raise Http404("Invalid episode number.")

        try:
            # Fetch the specific episode object
            episode = movie.episodes_set.get(episode_number=episode_num)
        except Episodes.DoesNotExist:
            raise Http404(f"Episode {episode_num} not found for {movie.title}.")

        # Determine stream URL based on quality
        if quality == 'SD':
            stream_url = episode.streamSD_link
        elif quality == 'HD':
            stream_url = episode.streamHD_link
            
        content_name = f"{movie.title} - E{episode_num}"
        if episode.title:
            content_name += f": {episode.title}"
    
    else:
        # Catch unexpected flow
        raise Http404("Invalid streaming request flow.")

    if not stream_url:
        logger.warning(f"Stream link requested for {slug} ({quality}, Episode: {episode_num}) but no link available.")
        if movie.type in ['tv', 'anime']:
             return redirect('episodes_list', slug=slug)
        else:
             raise Http404("Streaming link is not available for this quality.")


    return render(request, "stream.html", {
        "movie": movie,
        "quality": quality,
        "stream_url": stream_url,
        "content_name": content_name, 
    })


# --- TELEGRAM WEBHOOK VIEW ---

@csrf_exempt
async def telegram_webhook_view(request):
    if request.method != "POST":
        return HttpResponseForbidden("GET not allowed")
    
    try:
        await init_bot()

        update_json = json.loads(request.body.decode("utf-8"))
        update = Update.de_json(update_json, telegram_app.bot)

        await telegram_app.process_update(update)

        return HttpResponse(status=200)
    
    except Exception as e:
        print("Telegram webhook error:", e)
        return HttpResponse(status=500)


# --- REST API VIEWS ---

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movies.objects.all().order_by('-upload_date')
    serializer_class = MovieSerializer
    
    @action(detail=False, methods=['get'], url_path='search')
    def search_movies(self, request):
        query = request.query_params.get('q', '')
        if query:
            queryset = self.queryset.filter(title__icontains=query)
        else:
            queryset = self.queryset.none()
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


import telegram
print("PTB VERSION:", telegram.__version__)


from users.models import MovieVisit
from django.contrib.auth.decorators import login_required


# Update your movie_detail view to include visit tracking
# Here's an example of what it should look like:
