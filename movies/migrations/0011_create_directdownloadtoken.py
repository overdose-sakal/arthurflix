# movies/migrations/000X_create_directdownloadtoken.py
# Generated migration file - adjust the number (000X) based on your last migration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0001_initial'),  # Change this to your last migration file
    ]

    operations = [
        migrations.CreateModel(
            name='DirectDownloadToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=12, unique=True)),
                ('quality', models.CharField(max_length=5)),
                ('original_link', models.URLField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('access_count', models.IntegerField(default=0)),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='movies.movies')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='directdownloadtoken',
            index=models.Index(fields=['token'], name='movies_dire_token_idx'),
        ),
        migrations.AddIndex(
            model_name='directdownloadtoken',
            index=models.Index(fields=['expires_at'], name='movies_dire_expires_idx'),
        ),
    ]