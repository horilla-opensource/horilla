## Horilla v2.0 Docker Guide

This guide explains how to run Horilla with Docker in development and production (Nginx + Gunicorn).

### Prerequisites
- Docker 24+ and Docker Compose v2
- 2 CPU / 2 GB RAM minimum recommended

### Project layout (Docker-related)
- `Dockerfile`: Production multi-stage image (Python 3.11, slim)
- `Dockerfile.dev`: Development image with compilers and auto-reload
- `docker-compose.yaml`: Production stack (web + db + nginx)
- `docker-compose.dev.yaml`: Development stack (web + db) with live reload
- `deploy/nginx/nginx.conf`: Nginx reverse proxy config (serves `/static/` and `/media/`)
- `deploy/gunicorn.conf.py`: Gunicorn config for production
- `entrypoint.sh`: App lifecycle (migrate, collectstatic, start Gunicorn)
- `.dockerignore`: Reduces build context

## Development

### Start
```bash
# Build and run (autoreload)
docker compose -f docker-compose.dev.yaml up --build
# Open the app
open http://localhost:8000
```

### Useful dev commands
```bash
# Shell into the web container
docker compose -f docker-compose.dev.yaml exec web bash

# Run migrations
docker compose -f docker-compose.dev.yaml exec web python manage.py migrate

# Create admin user (example)
docker compose -f docker-compose.dev.yaml exec web \
  python manage.py createhorillauser \
  --first_name admin --last_name admin \
  --username admin --password admin \
  --email admin@example.com --phone 1234567890
```

## Production (Nginx + Gunicorn)

### Start
```bash
# Build and start in the background
docker compose up --build -d
# Open the app (served by Nginx)
open http://localhost
```

### Services
- `web`: Django app via Gunicorn on port 8000 (internal)
- `db`: PostgreSQL 16 (internal only)
- `nginx`: Reverse proxy on port 80; serves static and media directly

### Volumes
- `staticfiles`: `collectstatic` output served at `/static/`
- `media`: user uploads served at `/media/`
- `horilla-data`: Postgres data

### Environment variables
- `DATABASE_URL`: e.g. `postgres://postgres:postgres@db:5432/horilla`
- `DEBUG`: should be `false` in production
- `ALLOWED_HOSTS`: e.g. `["yourdomain.com"]`
- `CSRF_TRUSTED_ORIGINS`: e.g. `["https://yourdomain.com"]`
- `TIME_ZONE`: e.g. `Asia/Kolkata`
- `SECRET_KEY`: set a strong value (read from `.env` by Django)

Django reads `.env` from the project root via `django-environ`. Create one if needed.

### Common operations
```bash
# View logs
docker compose logs -f web

# Run management commands
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput

# Create admin user
docker compose exec web \
  python manage.py createhorillauser \
  --first_name admin --last_name admin \
  --username admin --password 'CHANGE_ME' \
  --email admin@example.com --phone 1234567890

# Stop the stack
docker compose down
```

### TLS (HTTPS)
- Terminate TLS at Nginx. Provide your certs and update `deploy/nginx/nginx.conf` to listen on 443 and reference your certificate and key.
- Then publish `443:443` in the `nginx` service and set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` accordingly.

### Database backup/restore
```bash
# Backup (inside db container)
docker compose exec db pg_dump -U postgres -d horilla > horilla_backup.sql

# Restore
cat horilla_backup.sql | docker compose exec -T db psql -U postgres -d horilla
```

## Troubleshooting
- Static files not loading: ensure `collectstatic` ran successfully; check `staticfiles` volume is mounted to Nginx.
- 502 from Nginx: check `web` logs and Gunicorn is listening on 0.0.0.0:8000.
- CSRF/host errors: set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for your domain.
- DB connection errors: confirm `DATABASE_URL` and that `db` service is healthy.
- Permissions on `media`: ensure Docker user can write; by default, containers run as root in this setup.

## Upgrades
```bash
# Rebuild images after changes to requirements or Dockerfiles
docker compose build --no-cache
# Apply migrations
docker compose exec web python manage.py migrate
# Reload Nginx (if config changed)
docker compose exec nginx nginx -s reload
```

## Notes
- Production images are based on Python 3.11 slim and use a multi-stage build for smaller, reliable artifacts.
- The database is not exposed to the host in production compose; connect from `web` or via `docker compose exec db psql`.
- For multi-host deployments, consider externalizing Postgres and object storage (e.g., S3) via `django-storages`.
