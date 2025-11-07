#!/bin/bash
# Initialize database script
# This script is executed by PostgreSQL's entrypoint when the container starts

set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is ready - running initialization..."

# Create the horilla_dba user with password if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO
    \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'horilla_dba') THEN
            CREATE USER horilla_dba WITH LOGIN PASSWORD '${DB_PASSWORD}';
            GRANT ALL PRIVILEGES ON DATABASE horilla TO horilla_dba;
            ALTER DATABASE horilla OWNER TO horilla_dba;
            GRANT USAGE ON SCHEMA public TO horilla_dba;
            GRANT CREATE ON SCHEMA public TO horilla_dba;
        END IF;
    END
    \$\$;
EOSQL

echo "Database initialization completed"
