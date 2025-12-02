# fix_file_ids.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BF.settings')
django.setup()

from movies.models import Movies
from movies.telegram_utils import TelegramFileManager

# Check all movies
movies = Movies.objects.all()

for movie in movies:
    print(f"\n{movie.title}:")
    print(f"  SD ID: {movie.SD_telegram_file_id}")
    print(f"  HD ID: {movie.HD_telegram_file_id}")
    
    # If IDs look wrong (URLs or too short), flag them
    if movie.SD_telegram_file_id and (
        movie.SD_telegram_file_id.startswith('http') or 
        len(movie.SD_telegram_file_id) < 30
    ):
        print(f"  ⚠️ SD file_id looks invalid!")
    
    if movie.HD_telegram_file_id and (
        movie.HD_telegram_file_id.startswith('http') or 
        len(movie.HD_telegram_file_id) < 30
    ):
        print(f"  ⚠️ HD file_id looks invalid!")