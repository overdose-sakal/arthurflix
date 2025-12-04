#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# CRITICAL: Collect all static files (CSS, JS, images)
python3 manage.py collectstatic --no-input

python manage.py migrate --noinput && gunicorn BF.wsgi

python manage.py migrate --noinput && \
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('sakal', 'sakalytshit@gmail.com', 'Salibill1')" | python manage.py shell && \
gunicorn YOUR_PROJECT_NAME.wsgi
