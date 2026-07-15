#!/bin/sh
set -eu

umask 077

python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py hydra_readiness

exec gunicorn \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
    --access-logfile - \
    --error-logfile - \
    horilla.wsgi:application
