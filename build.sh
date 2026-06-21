#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py compilemessages