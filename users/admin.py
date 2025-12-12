# users/admin.py

from django.contrib import admin
from .models import MembershipKey

# Custom Admin class for the MembershipKey model
class MembershipKeyAdmin(admin.ModelAdmin):
    # This list must only contain fields that actually exist on the MembershipKey model.
    # We include 'user' because it is now defined in users/models.py.
    list_display = ('key', 'is_active', 'expiry_date', 'user', 'created_at')
    
    list_filter = ('is_active', 'expiry_date')
    
    # Allows searching by key, associated username, and notes
    search_fields = ('key', 'user__username', 'notes')
    
    readonly_fields = ('created_at',)
    
    # Fields to display/edit on the change form
    fields = ('key', 'is_active', 'expiry_date', 'user', 'notes')

# Register the model with the Admin site
admin.site.register(MembershipKey, MembershipKeyAdmin)