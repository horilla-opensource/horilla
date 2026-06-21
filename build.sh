#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py check
# Drop-in for `migrate` that also heals legacy databases and tolerates the
# redundant migration history on this branch (see reconcile_legacy_db).
python manage.py reconcile_legacy_db
python manage.py collectstatic --noinput
python manage.py compilemessages