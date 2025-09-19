#!/bin/sh
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! python3 -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready!"

echo "Creating migrations..."
python3 manage.py makemigrations

echo "Applying database migrations..."
python3 manage.py migrate --noinput

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Compiling translations..."
python3 manage.py compilemessages || true

# Create superuser if requested and doesn't exist
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Checking for superuser..."
    python3 manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username=os.environ.get('SUPERUSER_USERNAME', 'admin'),
        email=os.environ.get('SUPERUSER_EMAIL', 'admin@example.com'),
        password=os.environ.get('SUPERUSER_PASSWORD', 'admin')
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
" || true
fi

# Start the application
if [ "$DEBUG" = "true" ]; then
    echo "Starting Django development server..."
    exec python3 manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn..."
    exec gunicorn -c ./deploy/gunicorn.conf.py horilla.wsgi:application
fi
