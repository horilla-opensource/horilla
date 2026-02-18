#!/bin/bash
set -e

# entrypoint.sh for horilla web service
# Strict mode: exit on error, undefined variables, pipe failures
set -o pipefail

echo "Waiting for PostgreSQL to start..."

# Get the connection variables from environment with defaults
export DB_HOST=${DB_HOST:-db}
export DB_PORT=${DB_PORT:-5432}
export DB_NAME=${DB_NAME:-horilla}
export DB_USER=${DB_USER:-horilla_dba}
export DB_PASSWORD=${DB_PASSWORD}
export PGPASSWORD=${DB_INIT_PASSWORD:-postgres}  # Use DB_INIT_PASSWORD for postgres user

# Set DATABASE_URL explicitly to avoid env variable expansion issues
export DATABASE_URL="postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "postgres"; do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is up - setting up database..."

# Database initialization (can be skipped if init-db.sql handles it)
echo "Verifying database setup..."

# Check if database exists, if not create it
if ! PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Creating database $DB_NAME..."
    PGPASSWORD=$PGPASSWORD createdb -h "$DB_HOST" -U postgres "$DB_NAME" || echo "Database creation returned status (may already exist)"
fi

# Note: User and privileges are typically created via init-db.sql during first run
# This is a fallback in case they're not created
{
    PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1
} || {
    echo "Creating user $DB_USER..."
    PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
}

# Ensure the user has all privileges on the database
PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;" 2>/dev/null || true
PGPASSWORD=$PGPASSWORD psql -h "$DB_HOST" -U postgres -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;" 2>/dev/null || true

# Run Django migrations
echo "Running migrations..."
python3 manage.py makemigrations
python3 manage.py migrate

# Compile translations
echo "Compiling translations..."
python3 manage.py compilemessages

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Start the Django application with gunicorn (production-ready)
echo "Starting Horilla server with gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    horilla.wsgi:application