#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py check

if [ "$RECONCILE_DB" = "1" ]; then
    # One-time: reconcile a legacy DB (built before migrations were tracked)
    # with the committed migrations. Set RECONCILE_DB=1 for a single deploy,
    # then remove the env var.
    python manage.py reconcile_legacy_db
else
    python manage.py migrate
fi

python manage.py collectstatic --noinput
python manage.py compilemessages