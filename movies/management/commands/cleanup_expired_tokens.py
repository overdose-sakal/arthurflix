# movies/management/commands/cleanup_expired_tokens.py
# Create the directory structure: movies/management/commands/
# Don't forget to add __init__.py files in management/ and commands/

from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.models import DirectDownloadToken, DownloadToken

class Command(BaseCommand):
    help = 'Clean up expired download tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Clean up DirectDownloadTokens
        expired_direct = DirectDownloadToken.objects.filter(expires_at__lt=now)
        direct_count = expired_direct.count()
        
        # Clean up regular DownloadTokens
        expired_regular = DownloadToken.objects.filter(expires_at__lt=now)
        regular_count = expired_regular.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {direct_count} expired DirectDownloadTokens '
                    f'and {regular_count} expired DownloadTokens'
                )
            )
        else:
            # Actually delete
            expired_direct.delete()
            expired_regular.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {direct_count} expired DirectDownloadTokens '
                    f'and {regular_count} expired DownloadTokens'
                )
            )
        
        # Show statistics
        active_direct = DirectDownloadToken.objects.filter(expires_at__gte=now).count()
        active_regular = DownloadToken.objects.filter(expires_at__gte=now).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nActive tokens remaining:'
                f'\n  - DirectDownloadTokens: {active_direct}'
                f'\n  - DownloadTokens: {active_regular}'
            )
        )