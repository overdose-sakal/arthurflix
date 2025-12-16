# users/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import string

# CRITICAL IMPORTS FOR SINGLE SESSION LOGIC
from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in 
from django.dispatch import receiver
from django.contrib.auth import get_user_model

# The key length (32 characters)
KEY_LENGTH = 32
User = get_user_model() # Get the currently active user model

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
            return ''.join(secrets.choice(chars) for _ in range(KEY_LENGTH))

def get_default_expiry_date():
    """Returns the default expiry date (1 year from now)."""
    # Keys should not have a default expiry date unless they are used
    return None 

class MembershipKey(models.Model):
    """
    A 32-character key that grants membership access to the site.
    """
    key = models.CharField(
        max_length=KEY_LENGTH,
        unique=True,
        default=generate_unique_key,
        help_text=f"The unique {KEY_LENGTH}-character key."
    )
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='membership_key',
        help_text="The user who activated this key. (Null if unactivated)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether the key is currently usable for activation/membership. Allows manual deactivation."
    )
    expiry_date = models.DateField(
        null=True, 
        blank=True, 
        help_text="The date this key will expire. (Null if not yet activated)"
    )
    notes = models.TextField(
        blank=True, 
        help_text="Internal notes about the key (e.g., source, price, reason for deactivation)."
    )

    class Meta:
        verbose_name = 'Membership Key'
        verbose_name_plural = 'Membership Keys'

    def __str__(self):
        return self.key

    @property
    def is_valid(self):
        """Checks if the key is active, linked to a user, and not expired."""
        
        if not self.is_active:
            return False
            
        if self.expiry_date is None:
            return False
        
        return self.expiry_date >= timezone.now().date()


class Avatar(models.Model):
    """
    Stores predefined avatars from Cloudinary.
    """
    name = models.CharField(max_length=100, unique=True)
    image_url = models.URLField(max_length=500) 

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    Extends the default User model to store the selected avatar.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ForeignKey(
        'Avatar', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="The selected avatar for the user."
    )
    
    @property
    def membership_expires_at(self):
        """
        Returns the expiry date of the user's currently active membership key.
        """
        try:
            key = MembershipKey.objects.get(user=self.user, is_active=True)
            
            if key.is_valid:
                return key.expiry_date
                
            return None
            
        except MembershipKey.DoesNotExist:
            return None
    

    def __str__(self):
        return f"Profile for {self.user.username}"


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
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    def __str__(self):
        return f"Session tracker for {self.user.username}"


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """
    Updates the user's active session key upon successful login.
    """
    if not request.session.session_key:
        request.session.save()
        
    tracker, created = UserSessionTracker.objects.get_or_create(user=user)
    
    if tracker.session_key and tracker.session_key != request.session.session_key:
        try:
            Session.objects.get(session_key=tracker.session_key).delete()
        except Session.DoesNotExist:
            pass
            
    tracker.session_key = request.session.session_key
    tracker.save()


from movies.models import Movies


class UserCatalogueItem(models.Model):
    """
    Tracks user's movie catalogue with only 'finished' and 'watchlist' statuses.
    """
    STATUS_CHOICES = [
        ('finished', 'Finished'),
        ('watchlist', 'Watchlist'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='catalogue_items'
    )

    movie = models.ForeignKey(
        Movies,
        on_delete=models.CASCADE,
        related_name='user_entries'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} → {self.movie.title} ({self.status})"


class MovieVisit(models.Model):
    """
    Tracks when a user visits a movie detail page.
    Stores only the last 3 visits per user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='movie_visits'
    )
    
    movie = models.ForeignKey(
        Movies,
        on_delete=models.CASCADE,
        related_name='visits'
    )
    
    visited_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-visited_at']
        unique_together = ('user', 'movie')
    
    def __str__(self):
        return f"{self.user.username} visited {self.movie.title}"
    
    @classmethod
    def record_visit(cls, user, movie):
        """
        Record a visit and maintain only the last 3 visits per user.
        """
        # Update or create the visit
        visit, created = cls.objects.update_or_create(
            user=user,
            movie=movie,
            defaults={'visited_at': timezone.now()}
        )
        
        # Keep only the last 3 visits
        user_visits = cls.objects.filter(user=user)
        if user_visits.count() > 3:
            # Delete visits beyond the 3rd one
            visits_to_delete = user_visits[3:]
            cls.objects.filter(id__in=[v.id for v in visits_to_delete]).delete()
        
        return visit