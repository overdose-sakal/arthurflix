from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import UserProfile, Avatar
from django.db import transaction
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a UserProfile for all existing users and ensures they have a default name.'

    def handle(self, *args, **options):
        # 1. Check for Avatars to assign a default
        try:
            default_avatar = Avatar.objects.first()
        except Avatar.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "No Avatar objects found. Please populate the Avatar model first."
            ))
            sys.exit(1)
        
        if not default_avatar:
             self.stderr.write(self.style.ERROR(
                "The Avatar model is empty. Cannot assign a default avatar."
            ))
             sys.exit(1)


        # 2. Find Users without Profiles
        users_to_update = User.objects.filter(profile__isnull=True)
        count = users_to_update.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("All existing users already have a UserProfile."))
            return
        
        self.stdout.write(self.style.WARNING(
            f"Found {count} existing users without a UserProfile. Creating/Fixing profiles now..."
        ))

        # 3. Create Profiles and Fix Name Fields in a single transaction
        profiles_created = 0
        names_fixed = 0
        
        with transaction.atomic():
            for user in users_to_update:
                
                # --- FIX 1: Set default name if missing ---
                # Default to the username capitalized if first_name/last_name are empty
                if not user.first_name or not user.last_name:
                    
                    # Use a generic name derived from the username
                    default_name = user.username.capitalize()
                    
                    # Set the names to ensure they are not empty for the profile page
                    if not user.first_name:
                        user.first_name = default_name
                        
                    if not user.last_name:
                        user.last_name = "" # Use empty string for last name if not required
                        
                    user.save(update_fields=['first_name', 'last_name'])
                    names_fixed += 1

                # --- FIX 2: Create the UserProfile ---
                UserProfile.objects.create(
                    user=user,
                    avatar=default_avatar
                )
                profiles_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {profiles_created} UserProfile records."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Successfully fixed names for {names_fixed} existing users."
        ))