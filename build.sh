#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python3 manage.py migrate --no-input

# CRITICAL: Collect all static files (CSS, JS, images)
python3 manage.py collectstatic --no-input