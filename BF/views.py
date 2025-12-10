# BF/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponse, Http404
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import quote  

# Import necessary third-party libraries
import requests 

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

# Import models and utilities
from movies.models import Movies, DownloadToken, DirectDownloadToken
from movies.telegram_utils import TelegramFileManager
from movies.serializers import MovieSerializer

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


def Movie(request, slug):
    movie = get_object_or_404(Movies, slug=slug)
    
    # Check if download is available via Telegram file_id OR direct link
    sd_download_url = bool(movie.SD_telegram_file_id or movie.SD_link)
    hd_download_url = bool(movie.HD_telegram_file_id or movie.HD_link)
    
    return render(request, "movie_detail.html", {
        "movie": movie,
        "sd_download_url": sd_download_url,
        "hd_download_url": hd_download_url,
    })


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


# --- SHRINKEARN HELPER FUNCTION ---

def create_shrinkearn_link(destination_url, alias=None):
    """
    Creates a shortened URL using ShrinkEarn API.
    
    Args:
        destination_url: The final destination URL
        alias: Optional custom alias for the shortened URL
    
    Returns:
        The shortened URL or None if failed
    """
    api_url = "https://shrinkearn.com/api"
    
    params = {
        'api': settings.SHRINK_EARN_API_KEY,
        'url': destination_url,
    }
    
    if alias:
        params['alias'] = alias
    
    try:
        logger.info(f"📄 Creating ShrinkEarn link for: {destination_url}")
        logger.info(f"🔑 Request params: api={settings.SHRINK_EARN_API_KEY[:10]}..., url={destination_url}, alias={alias}")
        
        response = requests.get(api_url, params=params, timeout=10)
        logger.info(f"📊 Response status code: {response.status_code}")
        logger.info(f"📄 Response text: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"🔍 Response JSON: {data}")
        
        # ShrinkEarn API returns different formats depending on success
        # Check for various possible response formats
        if data.get('status') == 'success' and data.get('shortenedUrl'):
            shortened_url = data.get('shortenedUrl')
            logger.info(f"✅ ShrinkEarn link created successfully: {shortened_url}")
            return shortened_url
        elif 'shortenedUrl' in data:
            # Sometimes status might not be present but shortenedUrl is
            shortened_url = data.get('shortenedUrl')
            logger.info(f"✅ ShrinkEarn link created: {shortened_url}")
            return shortened_url
        elif 'error' in data:
            error_msg = data.get('error', 'Unknown error')
            logger.error(f"❌ ShrinkEarn API error: {error_msg}")
            return None
        else:
            logger.error(f"❌ Unexpected ShrinkEarn API response format: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ ShrinkEarn API request failed: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse ShrinkEarn API response: {str(e)}")
        logger.error(f"📄 Raw response: {response.text if 'response' in locals() else 'No response'}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error creating ShrinkEarn link: {str(e)}")
        return None


# --- DOWNLOAD TOKEN VIEWS (UPDATED FOR SHRINKEARN) ---

def download_token_view(request, quality, slug):
    """
    Generates a token and redirects user through ShrinkEarn for monetization.
    Now supports both Telegram file_id AND direct links.
    """
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

    # 3. Build the final destination URL (where user goes after ShrinkEarn)
    destination_url = request.build_absolute_uri(
        reverse('download_file_redirect', kwargs={'token': token_instance.token})
    )
    
    logger.info(f"🎯 Destination URL: {destination_url}")
    
    # 4. Create ShrinkEarn link
    shrinkearn_url = create_shrinkearn_link(destination_url, alias=None)
    
    if shrinkearn_url:
        logger.info(f"✅ Redirecting to ShrinkEarn: {shrinkearn_url}")
        return redirect(shrinkearn_url)
    else:
        # Fallback: If ShrinkEarn fails, redirect directly
        logger.warning("⚠️ ShrinkEarn failed, redirecting directly to download")
        return redirect(destination_url)


def download_file_redirect(request, token):
    """
    Called after the user completes ShrinkEarn redirection.
    It verifies the token and redirects the user to the file-ready page.
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


def download_page_view(request):
    """
    Renders the final download page (download.html).
    This shows the Telegram deep link after ShrinkEarn is completed.
    """
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
        
        # Generate or retrieve direct download token
        direct_token = get_or_create_direct_download_token(movie, quality)
        direct_download_url = request.build_absolute_uri(
            reverse('direct_download_redirect', kwargs={'token': direct_token.token})
        ) if direct_token else None
        
    except Http404:
        direct_download_url = None
    
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'YourBotUsername_placeholder')
    
    context = {
        'token': token,
        'movie_title': movie_title,
        'quality': quality,
        'bot_username': bot_username,
        'telegram_deep_link': f"https://t.me/{bot_username}?start={token}",
        'direct_download_url': direct_download_url,
    }
    
    return render(request, 'download.html', context)


# --- NEW: DIRECT DOWNLOAD FUNCTIONS ---

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


def direct_download_redirect(request, token):
    """
    Validates the direct download token and redirects to the actual file.
    """
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