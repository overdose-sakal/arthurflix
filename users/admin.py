# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import Avatar, UserProfile, MembershipKey, UserSessionTracker 

User = get_user_model()


# --- 1. Admin Registration for Avatar (for data entry) ---

@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    """Admin interface for managing the predefined avatar images."""
    list_display = ('id', 'name', 'image_url')
    search_fields = ('name',)
    readonly_fields = ('id',) 
    fields = ('name', 'image_url')


# --- 2. Inlines to attach to the default User Admin ---

class UserProfileInline(admin.StackedInline):
    """Allows editing the UserProfile directly on the User edit page."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('avatar',)
    
class MembershipKeyInline(admin.StackedInline):
    """Allows editing the MembershipKey directly on the User edit page."""
    model = MembershipKey
    can_delete = False
    verbose_name_plural = 'Membership Key'
    # 'is_active' is now editable by removing it from readonly_fields
    fields = ('key', 'expiry_date', 'is_active', 'is_valid') 
    readonly_fields = ('is_valid',) # Only 'is_valid' remains read-only

# --- 3. Custom User Admin ---

class CustomUserAdmin(BaseUserAdmin):
    """Custom UserAdmin to include UserProfile and MembershipKey inlines."""
    inlines = (UserProfileInline, MembershipKeyInline)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Unregister the default User admin, then register the custom one
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass 

admin.site.register(User, CustomUserAdmin)


# --- 4. Admin Registration for other models ---

@admin.register(MembershipKey)
class MembershipKeyAdmin(admin.ModelAdmin):
    """Admin for managing keys separately from user inline."""
    # 'is_active' is now editable
    list_display = ('key', 'user', 'is_active', 'expiry_date')
    list_filter = ('is_active', 'expiry_date')
    search_fields = ('key', 'user__username')
    readonly_fields = () # Removed 'is_active' to allow manual editing
    # Added 'is_active' to fields to make it visible and editable on the change form
    fields = ('key', 'user', 'expiry_date', 'is_active', 'notes') 


@admin.register(UserSessionTracker)
class UserSessionTrackerAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('user', 'session_key',)