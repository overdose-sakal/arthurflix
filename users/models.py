# users/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta
import secrets
import string

# The key length (32 characters)
KEY_LENGTH = 32

def generate_unique_key():
    """Generates a unique 32-character key for membership."""
    chars = string.ascii_letters + string.digits
    while True:
        key = ''.join(secrets.choice(chars) for _ in range(KEY_LENGTH))
        if not MembershipKey.objects.filter(key=key).exists():
            return key
        
# Fix: Defined function for default expiry (instead of lambda)
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
        # CRITICAL CHANGE: Using the named function here
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

    def is_valid(self):
        """Checks if the key is active and not expired."""
        return self.is_active and timezone.now() < self.expiry_date

    def __str__(self):
        status = "ACTIVE" if self.is_valid() else "INACTIVE/EXPIRED"
        return f"{self.key} ({status})"