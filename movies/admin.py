# movies/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Movies, DownloadToken, DirectDownloadToken, SentFile

# Register your existing Movies model
admin.site.register(Movies)


# NEW: Admin configuration for DirectDownloadToken
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
        from django.conf import settings
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        url = f"{base_url}/direct/{obj.token}/"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url, url
        )
    full_download_url.short_description = 'Download URL'
    
    def copy_link_button(self, obj):
        """Add a copy link button"""
        from django.conf import settings
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


# Optional: Add action to clean up expired tokens
@admin.action(description='Delete expired tokens')
def delete_expired_tokens(modeladmin, request, queryset):
    """Admin action to delete expired tokens"""
    expired = queryset.filter(expires_at__lt=timezone.now())
    count = expired.count()
    expired.delete()
    modeladmin.message_user(request, f"Deleted {count} expired tokens.")

DirectDownloadTokenAdmin.actions = [delete_expired_tokens]


# Optional: Register DownloadToken for management
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