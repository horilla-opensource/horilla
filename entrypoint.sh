#!/bin/sh
set -eu

umask 077

case "${HYDRA_PROCESS_ROLE:-web}" in
    web)
        python manage.py check --deploy
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput
        python manage.py hydra_readiness
        exec gunicorn \
            --bind "0.0.0.0:${PORT:-8000}" \
            --workers "${GUNICORN_WORKERS:-3}" \
            --threads "${GUNICORN_THREADS:-2}" \
            --timeout "${GUNICORN_TIMEOUT:-60}" \
            --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
            --access-logfile - \
            --error-logfile - \
            horilla.wsgi:application
        ;;
    maintenance)
        python manage.py check --deploy
        python manage.py migrate --check
        exec python manage.py run_hydra_maintenance
        ;;
    *)
        echo "Unsupported HYDRA_PROCESS_ROLE" >&2
        exit 64
        ;;
esac
