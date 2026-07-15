#!/bin/sh
set -eu

if [ -z "${HYDRA_DB_USER:-}" ] || [ -z "${HYDRA_DB_PASSWORD:-}" ]; then
    echo "HYDRA_DB_USER and HYDRA_DB_PASSWORD are required." >&2
    exit 1
fi

psql --no-psqlrc --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set app_user="$HYDRA_DB_USER" \
    --set app_password="$HYDRA_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec
SELECT format('ALTER ROLE %I NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L', :'app_user', :'app_password') \gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', current_database(), :'app_user') \gexec
SELECT format('ALTER SCHEMA public OWNER TO %I', :'app_user') \gexec
SQL
