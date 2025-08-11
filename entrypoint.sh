#!/bin/sh
set -e

echo "Creating migrations..."
python3 manage.py makemigrations

echo "Applying database migrations..."
python3 manage.py migrate --noinput

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Compiling translations..."
python3 manage.py compilemessages || true

echo "Starting Gunicorn..."
exec gunicorn -c ./deploy/gunicorn.conf.py horilla.wsgi:application
