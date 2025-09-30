#!/bin/sh
set -euo pipefail

# Default envs
: "${DJANGO_SETTINGS_MODULE:=horilla.settings}"
: "${PORT:=8000}"
: "${DATABASE_URL:=}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn horilla.wsgi:application
