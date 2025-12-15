# users/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta
import secrets
import string

# CRITICAL IMPORTS FOR SINGLE SESSION LOGIC
from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in 
from django.dispatch import receiver

# The key length (32 characters)
KEY_LENGTH = 32

def generate_unique_key():
    """Generates a unique 32-character key for membership."""
    chars = string.ascii_letters + string.digits
    while True:
        try:
            key = ''.join(secrets.choice(chars) for _ in range(KEY_LENGTH))
            # Checks if the generated key already exists
            if not MembershipKey.objects.filter(key=key).exists():
                return key
        except models.exceptions.AppRegistryNotReady:
            # Safely return a key even if the model registry isn't fully ready
            return ''.join(secrets.choice(chars) for _ in range(KEY_LENGTH))

def get_default_expiry_date():
    """Returns the default expiry date (1 year from now)."""
    return timezone.now() + timedelta(days=365)

class MembershipKey(models.Model):
    """
    A 32-character key that grants membership access to the site.
    """
    key = models.CharField(
        max_length=KEY_LENGTH,
        unique=True,
        default=generate_unique_key,
        help_text=f"The {KEY_LENGTH}-character unique membership key."
    )
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField(
        default=get_default_expiry_date 
    )
    
    # Optional link to a Django User (e.g., for Admin tracking)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Optional: Link to the Django User who owns/used this key."
    )
    
    notes = models.TextField(blank=True, help_text="Internal notes about key source or user.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membership Key"
        verbose_name_plural = "Membership Keys"
        ordering = ['-created_at']

    def __str__(self):
        return self.key

    def is_valid(self):
        """Checks if the key is active and not expired."""
        return self.is_active and timezone.now() < self.expiry_date

# --- NEW: Concurrent Session Tracking Model ---

class UserSessionTracker(models.Model):
    """
    Tracks the active session key for a user to enforce single login.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_tracker',
        help_text="The user whose active session is being tracked."
    )
    # Stores the session key of the currently active session
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    def __str__(self):
        return f"Session tracker for {self.user.username}"

# --- NEW: Signal to update the session key on login ---

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """
    Updates the user's active session key upon successful login.
    This deletes the previous active session, ensuring only one device can use the account.
    """
    # CRITICAL STEP: Ensure the current session key is generated and saved 
    if not request.session.session_key:
        request.session.save()
        
    tracker, created = UserSessionTracker.objects.get_or_create(user=user)
    
    # Invalidate old sessions by deleting the corresponding Django Session object
    if tracker.session_key and tracker.session_key != request.session.session_key:
        try:
            # Delete the old session from the database
            Session.objects.get(session_key=tracker.session_key).delete()
        except Session.DoesNotExist:
            pass
            
    # Store the NEW, active session key
    tracker.session_key = request.session.session_key
    tracker.save()