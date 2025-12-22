# movies/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.conf import settings
from .models import Movies, DownloadToken, DirectDownloadToken, SentFile, Episodes

# ==============================================================================
# 1. Episode Inline and Movies Admin (FIXED: Removed prepopulated_fields)
# ==============================================================================

# Define the Inline for Episodes
class EpisodesInline(admin.TabularInline):
    """Allows adding/editing episodes directly on the Movie/Show detail page."""
    model = Episodes
    extra = 1 
    fields = ['episode_number', 'title', 'streamSD_link', 'streamHD_link']

# Define and Register MoviesAdmin
@admin.register(Movies)
class MoviesAdmin(admin.ModelAdmin):
    # This connects the EpisodesInline to the Movies model admin page
    inlines = [EpisodesInline] 
    
    list_display = (
        'title', 'type', 'upload_date', 'SD_format', 'HD_format', 'num_episodes'
    )
    list_filter = ('type', 'upload_date', 'SD_format', 'HD_format')
    search_fields = ('title', 'description')
    
    # ⚠️ FIX APPLIED: REMOVED prepopulated_fields to fix KeyError. 
    # The slug will still be generated automatically by AutoSlugField on save.
    
    fieldsets = (
        (None, {
            'fields': ('title', 'type', 'description', 'size_mb')
        }),
        ('Download Links', {
            'fields': ('SD_telegram_file_id', 'HD_telegram_file_id', 'SD_link', 'HD_link'),
        }),
        ('Streaming Links (for Movies only)', {
            'fields': ('streamSD_link', 'streamHD_link'),
            'description': 'These links are used only when Type is set to "Movies". For TV/Anime, use the Episodes section below.',
        }),
        ('Visuals', {
            'fields': ('dp', 'screenshot1', 'screenshot2', 'trailer'),
        }),
        ('Formats', {
            'fields': ('SD_format', 'HD_format'),
        }),
        # 'slug' must remain removed from fieldsets to avoid the previous FieldError
        ('Internal', {
            'fields': (), 
        }),
    )
    
    # Custom method to display episode count
    def num_episodes(self, obj):
        # This relies on the fix made to models.py in the previous step
        return obj.num_episodes
    num_episodes.short_description = 'Episodes'


# ==============================================================================
# 2. DirectDownloadToken Admin (LEGACY CODE PRESERVED)
# ==============================================================================

@admin.register(DirectDownloadToken)
class DirectDownloadTokenAdmin(admin.ModelAdmin):
    list_display = [
        'token', 
        'movie_title', 
        'quality', 
        'access_count',
        'created_at', 
        'expires_at',
        'status_badge',
        'copy_link_button'
    ]
    list_filter = ['quality', 'created_at', 'expires_at']
    search_fields = ['token', 'movie__title']
    
    readonly_fields = [
        'token', 
        'created_at', 
        'access_count',
        'time_remaining',
        'full_download_url'
    ]
    
    fieldsets = (
        ('Token Information', {
            'fields': ('token', 'full_download_url', 'access_count')
        }),
        ('Movie Details', {
            'fields': ('movie', 'quality', 'original_link')
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at', 'time_remaining')
        }),
    )
    
    def movie_title(self, obj):
        """Display movie title"""
        return obj.movie.title
    movie_title.short_description = 'Movie'
    
    def status_badge(self, obj):
        """Display status with color badge"""
        if obj.is_valid():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">✗ Expired</span>'
            )
    status_badge.short_description = 'Status'
    
    def time_remaining(self, obj):
        """Calculate and display time remaining"""
        if obj.is_valid():
            remaining = obj.expires_at - timezone.now()
            hours = remaining.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return "Expired"
    time_remaining.short_description = 'Time Remaining'
    
    def full_download_url(self, obj):
        """Display full download URL"""
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        url = f"{base_url}/direct/{obj.token}/"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url, url
        )
    full_download_url.short_description = 'Download URL'
    
    def copy_link_button(self, obj):
        """Add a copy link button"""
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        url = f"{base_url}/direct/{obj.token}/"
        return format_html(
            '<button onclick="navigator.clipboard.writeText(\'{}\');alert(\'Link copied!\');" '
            'style="background-color: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">'
            '📋 Copy Link</button>',
            url
        )
    copy_link_button.short_description = 'Actions'
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('movie')


# Optional: Add action to clean up expired tokens (LEGACY CODE PRESERVED)
@admin.action(description='Delete expired tokens')
def delete_expired_tokens(modeladmin, request, queryset):
    """Admin action to delete expired tokens"""
    expired = queryset.filter(expires_at__lt=timezone.now())
    count = expired.count()
    expired.delete()
    modeladmin.message_user(request, f"Deleted {count} expired tokens.")

DirectDownloadTokenAdmin.actions = [delete_expired_tokens]


# ==============================================================================
# 3. DownloadToken Admin (LEGACY CODE PRESERVED)
# ==============================================================================

@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'movie', 'quality', 'expires_at', 'status']
    list_filter = ['quality', 'expires_at']
    search_fields = ['token', 'movie__title']
    readonly_fields = ['token', 'expires_at']
    
    def status(self, obj):
        if obj.is_valid():
            return format_html(
                '<span style="color: green;">✓ Valid</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Expired</span>'
            )
    status.short_description = 'Status'

# ==============================================================================
# 4. SentFile Admin (Registration added as it was imported but not used)
# ==============================================================================

@admin.register(SentFile)
class SentFileAdmin(admin.ModelAdmin):
    list_display = ['chat_id', 'movie', 'quality', 'sent_at', 'delete_at']
    list_filter = ['quality', 'sent_at']
    search_fields = ['chat_id', 'movie__title']
    readonly_fields = ['sent_at', 'delete_at']




# movies/admin.py

import csv
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from .models import Episodes

class EpisodeCSVImportAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_import"] = True
        return super().changelist_view(request, extra_context=extra_context)


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-csv/", self.import_csv),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")

            if not csv_file.name.endswith(".csv"):
                self.message_user(request, "Please upload a CSV file.", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)

            data = csv_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(data)

            created = 0
            for row in reader:
                _, was_created = Episodes.objects.update_or_create(
                    movie_id=row["movie_id"],
                    episode_number=int(row["episode_number"]),
                    defaults={
                        "streamSD_link": row["streamSD_link"],
                        "streamHD_link": row.get("streamHD_link") or None,
                    },
                )
                if was_created:
                    created += 1

            self.message_user(
                request,
                f"CSV import complete. {created} episodes created/updated.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect("../")

        return render(request, "admin/episodes_import_form.html")



admin.site.register(Episodes, EpisodeCSVImportAdmin)
