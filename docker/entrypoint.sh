#!/bin/bash
set -e

echo "Starting Horilla HR..."

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

# Wait for PostgreSQL to be ready (with timeout)
echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
MAX_TRIES=30
COUNT=0
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_TRIES" ]; then
    echo "ERROR: PostgreSQL not available at ${DB_HOST}:${DB_PORT} after $MAX_TRIES attempts"
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL is ready!"

# Every shipped default (.env.dist, docker-compose.yml's own dev default, and
# historical leaked keys) is a known, public string -- never a real secret.
# If SECRET_KEY is unset or matches one of those, generate a random one and
# persist it in the media volume so it survives container restarts instead of
# invalidating every session/JWT on each `docker compose up`.
SECRET_KEY_FILE="/app/media/.generated_secret_key"
case "${SECRET_KEY:-}" in
  ""|"django-insecure-default-key"|"dev-secret-key-change-in-production"|"django-insecure-j8op9)1q8\$1&0^s&p*_0%d#pr@w9qj@1o=3#@d=a(^@9@zd@%j"|change-me*|django-insecure-*)
    if [ -f "$SECRET_KEY_FILE" ]; then
      SECRET_KEY="$(cat "$SECRET_KEY_FILE")"
      echo "Using previously generated SECRET_KEY from $SECRET_KEY_FILE"
    else
      SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
      mkdir -p "$(dirname "$SECRET_KEY_FILE")"
      printf '%s' "$SECRET_KEY" > "$SECRET_KEY_FILE"
      chmod 600 "$SECRET_KEY_FILE"
      echo "Generated a new random SECRET_KEY and saved it to $SECRET_KEY_FILE"
    fi
    export SECRET_KEY
    ;;
esac

# Run migrations
python manage.py migrate --noinput

# Collect static files.
#
# --clear is deliberate: STATIC_ROOT is a named volume that outlives the image,
# and plain collectstatic leaves anything it considers unmodified in place. With
# CompressedStaticFilesStorage that includes the pre-compressed .gz/.br
# siblings, so after an upgrade WhiteNoise happily served a previous release's
# global.js.gz to every browser (which all send Accept-Encoding: gzip) while
# curl, getting the identity encoding, saw the current file — JS functions
# "not defined" and half-rendered pages that looked fine to any check that
# bypassed static serving. Wiping first keeps what we serve equal to the image.
python manage.py collectstatic --noinput --clear

echo "Starting server..."
exec "$@"
