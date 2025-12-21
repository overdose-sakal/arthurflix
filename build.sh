#!/usr/bin/env bash
set -o errexit

echo "🔧 Installing dependencies"
pip install -r requirements.txt

echo "📦 Collecting static files"
python manage.py collectstatic --noinput

echo "🧱 Running migrations"
python manage.py migrate

echo "👤 Creating superuser (if not exists)"
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()

username = "sakal"
password = "Salibill1"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=sakal,
        email="mdsakibulhussain08@gmail.com",
        password=Salibill1
    )
    print("✅ Superuser created")
else:
    print("ℹ️ Superuser already exists")
EOF
