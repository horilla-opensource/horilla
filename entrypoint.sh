#!/bin/bash

echo "Waiting for database to be ready..."
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
gunicorn horilla.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -
