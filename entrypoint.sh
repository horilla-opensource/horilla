#!/bin/bash

set -e  # Exit on any error

echo "Waiting for database to be ready..."
# Wait for database to be ready
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if python3 -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    if connection.is_usable():
        exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
    echo "Database is ready!"
    break
  fi
  attempt=$((attempt + 1))
  echo "Database is unavailable - sleeping (attempt $attempt/$max_attempts)..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "ERROR: Database connection failed after $max_attempts attempts"
  exit 1
fi

echo "Running makemigrations..."
python3 manage.py makemigrations || echo "No new migrations to make"

echo "Running migrate..."
python3 manage.py migrate

if [ $? -ne 0 ]; then
  echo "ERROR: Migrations failed!"
  exit 1
fi

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Creating admin user..."
python3 manage.py createhorillauser --first_name admin --last_name admin --username admin --password admin --email admin@example.com --phone 1234567890 || echo "Admin user may already exist"

echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:8000 horilla.wsgi:application
