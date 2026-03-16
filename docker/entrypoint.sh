#!/bin/bash
set -e

echo "Starting Horilla HR..."

# Wait for PostgreSQL to be ready (with timeout)
echo "Waiting for PostgreSQL..."
MAX_TRIES=30
COUNT=0
while ! nc -z db 5432; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_TRIES" ]; then
    echo "ERROR: PostgreSQL not available after $MAX_TRIES attempts"
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL is ready!"

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
