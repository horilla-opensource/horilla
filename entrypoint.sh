#!/bin/bash

set -e

echo "Waiting for database to be ready..."
# Wait for database to be ready (healthcheck should handle this, but add extra wait)
until python3 -c "import psycopg2; psycopg2.connect('postgres://postgres:postgres@db:5432/horilla')" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready. Running migrations..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

echo "Compiling translation files..."
python3 manage.py compilemessages || echo "Warning: Some translation files may not have compiled"

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Creating default admin user..."
python3 manage.py createhorillauser --first_name admin --last_name admin --username admin --password admin --email admin@example.com --phone 1234567890 || echo "Admin user may already exist, skipping..."

echo "Starting server..."
gunicorn --bind 0.0.0.0:8000 horilla.wsgi:application
