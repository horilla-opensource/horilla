#!/bin/bash
set -e

echo "Starting Horilla HR..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL is ready!"

# Run migrations
python manage.py makemigrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"