#!/bin/bash

echo "Waiting for database to be ready..."
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py createhorillauser --first_name admin --last_name admin --username admin --password Cleaff@2025# --email pranay.rajput@cleaff.com --phone 1234567890
gunicorn --bind 0.0.0.0:8008 horilla.wsgi:application
