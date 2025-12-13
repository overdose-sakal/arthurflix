# BF/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib import admin
from . import views
from django.views.static import serve
from django.conf import settings

# NEW: Import ALL necessary views from the project-level views.py
from .views import (
    MovieViewSet, 
    Home, 
    Movie, 
    download_token_view, 
    download_file_redirect, 
    telegram_webhook_view,
    download_page_view,
    direct_download_redirect,
    stream_movie_view,
    episodes_list_view, # <-- NEW
    stream_content_view,
    stream_episode_view,
    episode_list_view,        # ⬅️ NEW: For the list of episodes
    stream_movie_view
)

from django.http import HttpResponse

def health(request):
    return HttpResponse("OK", status=200)

# router = DefaultRouter()
# router.register("movies", MovieViewSet, basename="movies")

urlpatterns = [
    # API
    path("movies/", include("movies.urls")),

    # Website pages
    path("", Home, name="home"), 
    path("admin/", admin.site.urls),
    path("movie/<slug:slug>/", Movie, name="movie_detail"), 
    path("category/<str:category>/", views.category_filter, name="category_filter"),

    path("stream/<str:quality>/<slug:slug>/", stream_movie_view, name="stream_movie"),

    path("", include("users.urls")),

    # ⚠️ NEW: Episode List Page (Destination for TV/Anime Stream Button)
    path("episodes/<slug:slug>/", episode_list_view, name="episode_list"),

    # ⚠️ NEW: Direct Movie Stream (Destination for Movie Stream Buttons)
    path("stream/movie/<str:quality>/<slug:slug>/", stream_movie_view, name="stream_movie"),

    # 2. General Stream Player (Used for Movies OR specific Episodes)
    path("stream/episodes/<slug:slug>/", episodes_list_view, name="episodes_list"),

    # path(
    #     "stream/<str:quality>/<slug:slug>/<int:episode_number>/", 
    #     views.stream_episode_view, 
    #     name="stream_episode"
    # ),
    

    # For Movies: /stream/HD/movie-slug/
    path("stream/<str:quality>/<slug:slug>/", stream_content_view, name="stream_movie"), 
    # For Episodes: /stream/SD/tv-show-slug/1/
    path("stream/<str:quality>/<slug:slug>/<int:episode_num>/", stream_content_view, name="stream_episode"),

    path(
        "stream/<str:quality>/<slug:slug>/<int:episode_number>/", 
        stream_episode_view, # Use the function directly or via 'views.stream_episode_view'
        name="stream_episode"
    ),


    # ShrinkEarn → TOKEN VALIDATION
    path("dl/<uuid:token>/", download_file_redirect, name="download_file_redirect"),

    # User clicked Download → Generate ShrinkEarn link
    path("download/<str:quality>/<slug:slug>/", download_token_view, name="download_token"),

    # Final destination → download.html
    path("download.html", download_page_view, name="download_page"),

    # Telegram webhook
    path("telegram/webhook/", telegram_webhook_view, name="telegram_webhook"),

    path("health/", health),

    path("sw.js", serve, {
        "document_root": settings.STATIC_ROOT,
        "path": "sw.js",
    }),

    path("direct/<str:token>/", direct_download_redirect, name="direct_download_redirect"),

]
