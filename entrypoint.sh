#!/bin/sh
set -eu

umask 077

case "${HYDRA_PROCESS_ROLE:-web}" in
    release)
        python manage.py check --deploy
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput
        python manage.py hydra_readiness
        ;;
    web)
        python manage.py check --deploy
        python manage.py migrate --check
        python manage.py hydra_readiness
        exec gunicorn \
            --bind "0.0.0.0:${PORT:-8000}" \
            --workers "${GUNICORN_WORKERS:-3}" \
            --threads "${GUNICORN_THREADS:-2}" \
            --timeout "${GUNICORN_TIMEOUT:-60}" \
            --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
            --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
            --max-requests "${GUNICORN_MAX_REQUESTS:-4000}" \
            --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-400}" \
            --forwarded-allow-ips "${GUNICORN_FORWARDED_ALLOW_IPS:-127.0.0.1}" \
            --access-logfile - \
            --access-logformat '{"timestamp":"%(t)s","request_id":"%({x-request-id}o)s","method":"%(m)s","path":"%(U)s","status":%(s)s,"duration_seconds":%(L)s,"bytes":%(B)s}' \
            --error-logfile - \
            hydra.wsgi:application
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
