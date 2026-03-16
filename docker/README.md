# Horilla HRMS — Docker Deployment Guide

A complete, step-by-step guide to running Horilla HR using Docker. Covers development setup, production deployment, customization, troubleshooting, and maintenance.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (Development)](#2-quick-start-development)
3. [Architecture Overview](#3-architecture-overview)
4. [Configuration Reference](#4-configuration-reference)
5. [Development Workflow](#5-development-workflow)
6. [Production Deployment](#6-production-deployment)
7. [Database Management](#7-database-management)
8. [Static & Media Files](#8-static--media-files)
9. [Scaling & Performance](#9-scaling--performance)
10. [Backup & Restore](#10-backup--restore)
11. [Monitoring & Health Checks](#11-monitoring--health-checks)
12. [Troubleshooting](#12-troubleshooting)
13. [Security Checklist](#13-security-checklist)
14. [File Reference](#14-file-reference)

---

## 1. Prerequisites

### Required Software

| Software | Minimum Version | Check Command |
|----------|----------------|---------------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ (V2) | `docker compose version` |
| Git | 2.30+ | `git --version` |

### System Requirements

| Environment | CPU | RAM | Disk |
|-------------|-----|-----|------|
| Development | 2 cores | 4 GB | 10 GB |
| Production (small, <50 employees) | 2 cores | 4 GB | 20 GB |
| Production (medium, 50–500 employees) | 4 cores | 8 GB | 50 GB |
| Production (large, 500+ employees) | 8 cores | 16 GB | 100 GB+ |

### Port Requirements

| Service | Port | Required For |
|---------|------|-------------|
| Web App | 8000 | Development access |
| Nginx | 80 | Production HTTP |
| PostgreSQL | 5432 | Internal only (not exposed to host by default) |
| Redis | 6379 | Internal only (not exposed to host by default) |

---

## 2. Quick Start (Development)

Get Horilla running in under 5 minutes:

```bash
# 1. Clone the repository
git clone -b dev/v2.0 https://github.com/horilla-opensource/horilla.git
cd horilla

# 2. Start all services
docker compose up -d

# 3. Wait for services to be healthy (~30–60 seconds on first run)
docker compose ps

# 4. Open in your browser
open http://localhost:8000
```

On first launch, Horilla will:
1. Wait for PostgreSQL to be ready
2. Run database migrations automatically
3. Collect static files
4. Start the Gunicorn application server

You'll see the **Database Initialization** page where you can create your first admin user and company.

### Stopping & Starting

```bash
# Stop all services (preserves data)
docker compose down

# Stop and remove ALL data (fresh start)
docker compose down -v

# Restart only the web service (after code changes)
docker compose restart web

# View logs
docker compose logs -f web
```

---

## 3. Architecture Overview

```
                              ┌─────────────────────────────┐
                              │         Browser             │
                              └─────────┬───────────────────┘
                                        │ :8000 (dev) / :80 (prod)
                   ┌────────────────────┼────────────────────┐
                   │  Docker Network    │                    │
                   │                    ▼                    │
                   │  ┌──────────────────────────────────┐  │
                   │  │  Nginx (production profile only)  │  │
                   │  │  - Static files (/static/)       │  │
                   │  │  - Media files (/media/)         │  │
                   │  │  - Proxy pass to web:8000        │  │
                   │  └──────────────┬───────────────────┘  │
                   │                 │                       │
                   │                 ▼                       │
                   │  ┌──────────────────────────────────┐  │
                   │  │  Web (Django + Gunicorn)          │  │
                   │  │  - 2–8 workers (adaptive)        │  │
                   │  │  - 4 threads per worker           │  │
                   │  │  - Health check: /health/         │  │
                   │  └───────┬──────────────┬──────────┘  │
                   │          │              │              │
                   │          ▼              ▼              │
                   │  ┌──────────────┐ ┌──────────────┐    │
                   │  │  PostgreSQL  │ │    Redis     │    │
                   │  │  16-alpine   │ │   7-alpine   │    │
                   │  │  Port: 5432  │ │  Port: 6379  │    │
                   │  └──────────────┘ └──────────────┘    │
                   │          │              │              │
                   │          ▼              ▼              │
                   │  [postgres_data]  [redis_data]         │
                   │  [staticfiles]    [media]              │
                   └────────────────────────────────────────┘
```

### Services

| Service | Image | Purpose |
|---------|-------|---------|
| **web** | Custom (Dockerfile) | Django application with Gunicorn WSGI server |
| **db** | `postgres:16-alpine` | Primary database for all application data |
| **redis** | `redis:7-alpine` | Caching, session storage, background job queues |
| **nginx** | `nginx:alpine` | Reverse proxy, static file serving (production only) |

### Volumes

| Volume | Mounted At | Purpose |
|--------|-----------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Persistent database storage |
| `redis_data` | `/data` | Redis AOF persistence |
| `staticfiles` | `/app/staticfiles` | Collected Django static files |
| `media` | `/app/media` | User-uploaded files (photos, documents, attachments) |

---

## 4. Configuration Reference

### Environment Variables (docker-compose.yml)

#### Django Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `1` | Set to `0` for production |
| `SECRET_KEY` | `dev-secret-key...` | **Change for production** — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames. Add your domain for production |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Full URLs for CSRF validation. Must include protocol |
| `DATABASE_URL` | `postgres://...@db:5432/...` | PostgreSQL connection string. `db` is the Docker service name |
| `REDIS_URL` | `redis://:...@redis:6379/0` | Redis connection string |

#### PostgreSQL Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `horilla_db` | Database name |
| `POSTGRES_USER` | `horilla_user` | Database user |
| `POSTGRES_PASSWORD` | `horilla_pass` | Database password — **change for production** |

#### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TIME_ZONE` | `Asia/Kolkata` | Server timezone (set in `.env`) |
| `LANGUAGE_CODE` | `en-us` | Default language |
| `GUNICORN_WORKERS` | Auto (2–8) | Override worker count |
| `GUNICORN_LOG_LEVEL` | `info` | Logging verbosity: debug, info, warning, error |
| `GUNICORN_RELOAD` | `false` | Set to `true` for auto-reload during development |

### Using a .env File (Optional)

For cleaner configuration, create a `.env` file from the template:

```bash
cp .env.dist .env
# Edit .env with your values
```

Then reference it in `docker-compose.yml`:

```yaml
services:
  web:
    env_file:
      - .env
```

Docker Compose automatically reads `.env` for variable substitution in the compose file itself (e.g., `${POSTGRES_PASSWORD}`).

---

## 5. Development Workflow

### Live Code Reloading

The development setup mounts your local code into the container (`. :/app`), so code changes are reflected immediately. To enable Gunicorn auto-reload:

```bash
# Option 1: Set environment variable
docker compose exec web env GUNICORN_RELOAD=true gunicorn horilla.wsgi:application --config docker/gunicorn.conf.py

# Option 2: Use Django's development server instead
docker compose exec web python manage.py runserver 0.0.0.0:8000
```

### Running Management Commands

```bash
# Run any Django management command
docker compose exec web python manage.py <command>

# Examples:
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell
docker compose exec web python manage.py compilemessages
docker compose exec web python manage.py collectstatic --noinput
```

### Installing New Python Packages

```bash
# 1. Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# 2. Rebuild the web image
docker compose build web

# 3. Restart
docker compose up -d
```

### Running Tests

```bash
docker compose exec web python manage.py test
```

### Accessing the Database Directly

```bash
# PostgreSQL shell
docker compose exec db psql -U horilla_user -d horilla_db

# Redis CLI
docker compose exec redis redis-cli -a horilla_pass
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f db

# Last 100 lines
docker compose logs --tail=100 web
```

---

## 6. Production Deployment

### Step 1: Update Environment Variables

Edit `docker-compose.yml` with production values:

```yaml
environment:
  - DEBUG=0
  - SECRET_KEY=your-unique-50-char-random-string-here
  - ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
  - CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Generate a secure secret key:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 2: Update Database Password

Change `horilla_pass` in all three places:
- `web` service `DATABASE_URL`
- `db` service `POSTGRES_PASSWORD`
- `redis` service `command` and `REDIS_URL`

### Step 3: Enable Nginx

Start with the production profile:

```bash
docker compose --profile production up -d
```

This starts the Nginx service which:
- Serves static files directly (with 1-year cache)
- Serves media files directly
- Proxies all other requests to Django
- Adds security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- Enables gzip compression
- Hides server version information

### Step 4: Set Up SSL/TLS

For HTTPS, add a `443` listener to `docker/nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # ... rest of config
}
```

Mount certificates in `docker-compose.yml`:

```yaml
nginx:
  volumes:
    - ./ssl/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
    - ./ssl/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
```

**Alternative:** Use [Caddy](https://caddyserver.com/) or [Traefik](https://traefik.io/) for automatic Let's Encrypt SSL.

### Step 5: Create Admin User

```bash
docker compose exec web python manage.py createsuperuser
```

### Step 6: Verify Deployment

```bash
# Check all services are healthy
docker compose ps

# Test health endpoint
curl http://localhost:8000/health/

# Check logs for errors
docker compose logs --tail=50 web
```

---

## 7. Database Management

### Running Migrations

Migrations run automatically on container start via `entrypoint.sh`. To run manually:

```bash
docker compose exec web python manage.py migrate
```

### Creating Migrations (Development Only)

```bash
# After model changes
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

> **Important:** Never run `makemigrations` in production. Migration files should be created during development, committed to version control, and applied in production via `migrate` only.

### Database Shell

```bash
docker compose exec db psql -U horilla_user -d horilla_db
```

### Loading Demo Data

From the Horilla login page, click "Load Demo Data" to populate the system with sample employees, departments, and other test data.

---

## 8. Static & Media Files

### Static Files

Collected automatically during container startup via `collectstatic`. In production, Nginx serves them directly from the `staticfiles` volume.

```bash
# Force re-collect
docker compose exec web python manage.py collectstatic --noinput --clear
```

### Media Files

User uploads (employee photos, documents, attachments) are stored in the `media` volume.

```bash
# List media files
docker compose exec web ls -la /app/media/

# Copy media to/from host
docker cp $(docker compose ps -q web):/app/media ./media-backup
```

### Using Cloud Storage (S3/GCP)

Horilla supports AWS S3 and Google Cloud Storage. Add to your environment:

**AWS S3:**
```
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1
DEFAULT_FILE_STORAGE=horilla.horilla_backends.PrivateMediaStorage
```

**Google Cloud Storage:**
```
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
GS_BUCKET_NAME=your-bucket
DEFAULT_FILE_STORAGE=horilla.horilla_backends_gcp.PrivateMediaStorage
```

---

## 9. Scaling & Performance

### Gunicorn Tuning

The default configuration auto-scales workers based on CPU count:

| Setting | Default | Description |
|---------|---------|-------------|
| Workers | `max(2, min(CPU*2+1, 8))` | Process count |
| Worker class | `gthread` | Threaded workers |
| Threads | `4` | Threads per worker |
| Max requests | `1000` | Restart worker after N requests (prevents memory leaks) |
| Timeout | `120s` | Request timeout |

Override via environment variables:

```yaml
environment:
  - GUNICORN_WORKERS=4
  - GUNICORN_LOG_LEVEL=warning
```

### PostgreSQL Tuning

For production workloads, add PostgreSQL configuration:

```yaml
db:
  image: postgres:16-alpine
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=768MB
    -c work_mem=16MB
    -c maintenance_work_mem=128MB
    -c max_connections=100
```

### Redis Memory Limit

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --requirepass horilla_pass --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

## 10. Backup & Restore

### Database Backup

```bash
# Create backup
docker compose exec db pg_dump -U horilla_user horilla_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec db pg_dump -U horilla_user -F c horilla_db > backup_$(date +%Y%m%d).dump
```

### Database Restore

```bash
# From SQL file
cat backup.sql | docker compose exec -T db psql -U horilla_user -d horilla_db

# From compressed dump
docker compose exec -T db pg_restore -U horilla_user -d horilla_db --clean < backup.dump
```

### Media Backup

```bash
# Backup media volume
docker run --rm -v horilla-hr-ai_media:/data -v $(pwd):/backup alpine tar czf /backup/media_backup.tar.gz -C /data .

# Restore media volume
docker run --rm -v horilla-hr-ai_media:/data -v $(pwd):/backup alpine tar xzf /backup/media_backup.tar.gz -C /data
```

### Automated Backups

Horilla includes a built-in backup system accessible from **Settings > Backup**. It supports:
- Scheduled local backups
- Google Drive backups with OAuth
- Database + media file backup

---

## 11. Monitoring & Health Checks

### Built-in Health Check

The Dockerfile includes a health check that pings `/health/` every 30 seconds:

```bash
# Check container health status
docker compose ps

# Manual health check
curl -f http://localhost:8000/health/
# Returns: {"status": "ok"}
```

### Service Health Checks

All services have health checks configured:

| Service | Health Check | Interval |
|---------|-------------|----------|
| web | `curl /health/` | 30s |
| db | `pg_isready` | 5s |
| redis | `redis-cli ping` | 5s |

### Resource Monitoring

```bash
# Live resource usage
docker stats

# Disk usage by volumes
docker system df -v
```

---

## 12. Troubleshooting

### Common Issues

#### Container won't start — "PostgreSQL not available"

The web container waits up to 30 seconds for PostgreSQL. If it times out:

```bash
# Check if db container is running
docker compose ps db

# Check db logs
docker compose logs db

# Restart db and web
docker compose restart db
docker compose restart web
```

#### "Permission denied" errors

The container runs as `appuser` (UID 1000). If volumes have wrong permissions:

```bash
docker compose exec web chown -R appuser:appuser /app/staticfiles /app/media
```

#### Static files not loading (404)

```bash
# Re-collect static files
docker compose exec web python manage.py collectstatic --noinput --clear

# Verify files exist
docker compose exec web ls /app/staticfiles/
```

#### Database migration errors

```bash
# Check migration status
docker compose exec web python manage.py showmigrations

# Run specific app migration
docker compose exec web python manage.py migrate <app_name>

# Reset a specific app's migrations (DESTRUCTIVE — development only)
docker compose exec web python manage.py migrate <app_name> zero
```

#### Out of disk space

```bash
# Clean unused Docker resources
docker system prune -a --volumes

# Check volume sizes
docker system df -v
```

#### Slow performance

1. Check worker count: `docker compose exec web ps aux | grep gunicorn`
2. Check database connections: `docker compose exec db psql -U horilla_user -c "SELECT count(*) FROM pg_stat_activity;"`
3. Check Redis memory: `docker compose exec redis redis-cli -a horilla_pass INFO memory`

### Resetting Everything

```bash
# Stop containers and remove ALL data (database, uploads, cache)
docker compose down -v

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

---

## 13. Security Checklist

Before going to production, verify the following:

- [ ] `DEBUG=0` is set
- [ ] `SECRET_KEY` is a unique, random 50+ character string
- [ ] `ALLOWED_HOSTS` lists only your actual domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS` uses `https://` URLs
- [ ] Database password is strong and unique (not `horilla_pass`)
- [ ] Redis password is strong and unique
- [ ] SSL/TLS is configured (HTTPS)
- [ ] Database and Redis ports are NOT exposed to the host
- [ ] Nginx is enabled (`--profile production`)
- [ ] Regular backups are configured
- [ ] Container images are kept up to date

---

## 14. File Reference

```
docker/
├── entrypoint.sh        # Container startup script
│                          - Waits for PostgreSQL (30s timeout)
│                          - Runs migrations
│                          - Collects static files
│                          - Starts Gunicorn via exec "$@"
│
├── gunicorn.conf.py     # Gunicorn WSGI server configuration
│                          - Adaptive worker count (2–8 based on CPU)
│                          - gthread worker class with 4 threads
│                          - 120s timeout, 1000 max requests
│                          - Access/error logging to stdout
│
├── nginx.conf           # Nginx reverse proxy configuration
│                          - Static files with 1-year cache
│                          - Gzip compression
│                          - Security headers
│                          - Proxy to Django with proper headers
│
└── README.md            # This file

Dockerfile               # Multi-stage build
                           - Builder: compiles C extensions
                           - Production: minimal runtime image
                           - Non-root user (appuser, UID 1000)
                           - Health check on /health/

docker-compose.yml        # Service orchestration
                           - web: Django + Gunicorn
                           - db: PostgreSQL 16
                           - redis: Redis 7
                           - nginx: Production reverse proxy

.dockerignore             # Files excluded from Docker build context
```
