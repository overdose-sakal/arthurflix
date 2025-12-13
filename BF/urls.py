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
