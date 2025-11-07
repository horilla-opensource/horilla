# Docker Deployment Configuration Review & Setup Guide

## Summary of Changes

This document outlines the security improvements and configuration updates made to the Horilla Docker deployment setup.

---

## Critical Security Issues Fixed

### 1. **Hardcoded Credentials** ✅ FIXED
**Issue**: Passwords hardcoded in `docker-compose.yaml` and `init-db.sql`
- **Before**: `DB_PASSWORD=X8UN09WIJDxsz3n` visible in configs
- **After**: All credentials moved to `.env` file and referenced via environment variables
- **Action Required**: Create `.env` file with strong random passwords

### 2. **Exposed PostgreSQL Port** ✅ FIXED
**Issue**: PostgreSQL exposed on port 5434 to host
- **Before**: `ports: - 5434:5432` allowed external connections
- **After**: PostgreSQL only accessible within Docker network (commented out)
- **Benefit**: Database not reachable from outside containers

### 3. **Development Server in Production** ✅ FIXED
**Issue**: Django `runserver` used instead of production WSGI server
- **Before**: `python3 manage.py runserver 0.0.0.0:8000`
- **After**: Gunicorn with 4 workers and proper timeout configuration
- **Benefit**: Concurrent request handling, proper error logging, production-ready

### 4. **Missing Error Handling** ✅ FIXED
**Issue**: Entrypoint script continued on errors
- **Before**: No error exit on failures
- **After**: `set -e` and `set -o pipefail` added at top of script
- **Benefit**: Script exits immediately on any error, preventing silent failures

### 5. **Insecure SQL Injection Risk** ✅ FIXED
**Issue**: Database password embedded in SQL commands
- **Before**: Direct string interpolation in SQL
- **After**: Using environment variables and safer execution patterns
- **Benefit**: Credentials not passed through command-line arguments

### 6. **Missing Docker Network** ✅ FIXED
**Issue**: No explicit internal network configuration
- **After**: Added `horilla-network` bridge network
- **Benefit**: Improved isolation and service discovery

---

## Configuration Changes

### docker-compose.yaml

**Key Changes**:
- Added explicit container names for easier management
- Environment variables now use `.env` file with fallback defaults
- PostgreSQL port no longer exposed (commented out)
- Added explicit network configuration
- Dynamic environment variable interpolation

**Before/After**:
```yaml
# BEFORE: Hardcoded credentials
environment:
  - DB_PASSWORD=X8UN09WIJDxsz3n
  - DATABASE_URL=postgres://horilla_dba:X8UN09WIJDxsz3n@db:5432/horilla

# AFTER: Environment variable references
environment:
  - DB_PASSWORD=${DB_PASSWORD}
  - DATABASE_URL=postgres://${DB_USER:-horilla_dba}:${DB_PASSWORD}@db:5432/${DB_NAME:-horilla}
```

### Dockerfile

**Key Changes**:
- Proper directory permissions set before user switch
- Non-root user for running application
- Directories created before user switch (avoids permission issues)
- Updated ENTRYPOINT to use shell script properly

### entrypoint.sh

**Key Changes**:
- Added `set -e` for strict error handling
- Added `set -o pipefail` for pipeline error detection
- Switched from Django development server to Gunicorn
- Better error handling for database operations
- More robust database verification

**Gunicorn Configuration**:
```bash
gunicorn --bind 0.0.0.0:8000 \
    --workers 4 \                    # Concurrent worker processes
    --worker-class sync \            # Synchronous workers (suitable for Django)
    --timeout 120 \                  # Request timeout in seconds
    --access-logfile - \             # Log to stdout
    --error-logfile - \              # Log errors to stdout
    horilla.config.wsgi:application  # Django WSGI application
```

### init-db.sql

**Key Changes**:
- Removed hardcoded password
- Added conditional user creation
- Better privilege management
- Added schema privileges

---

## Setup Instructions

### 1. Create `.env` File

Copy `.env.dist` to `.env` and configure with strong credentials:

```bash
cp .env.dist .env
```

Edit `.env` and set:
```env
# Set "DEBUG=False" for production
DEBUG=False

# Get a secure secret key from https://djecrety.ir
SECRET_KEY=<generate-new-key-here>

# Production allowed hosts
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Configuration
DB_NAME=horilla
DB_USER=horilla_dba
DB_PASSWORD=<generate-strong-password-here>
DB_INIT_PASSWORD=<generate-strong-postgres-password>
DB_HOST=db
DB_PORT=5432

# Timezone
TIME_ZONE=UTC
```

### 2. Generate Secure Passwords

Use a password generator for `DB_PASSWORD` and `DB_INIT_PASSWORD`:

```bash
# Linux/Mac
openssl rand -base64 32

# Or visit https://djecrety.ir for Django secret keys
```

### 3. Build and Run Containers

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f server

# Check container status
docker-compose ps
```

### 4. Verify Deployment

```bash
# Check application is running
curl http://localhost:8000

# Check database connection
docker-compose exec db psql -U postgres -d horilla -c "\dt"

# View Django migrations
docker-compose exec server python3 manage.py showmigrations
```

### 5. Troubleshooting

```bash
# View all logs
docker-compose logs

# Access Django shell
docker-compose exec server python3 manage.py shell

# Run management commands
docker-compose exec server python3 manage.py collectstatic --noinput

# Access PostgreSQL
docker-compose exec db psql -U postgres -d horilla
```

---

## Production Deployment Checklist

- [ ] **Security**
  - [ ] Set `DEBUG=False` in `.env`
  - [ ] Generate new `SECRET_KEY` from https://djecrety.ir
  - [ ] Use strong passwords (25+ characters with mixed case, numbers, symbols)
  - [ ] Set `ALLOWED_HOSTS` to actual domain(s)
  - [ ] Configure `CSRF_TRUSTED_ORIGINS` for your domain

- [ ] **Database**
  - [ ] Backup initial database
  - [ ] Review database user permissions in `init-db.sql`
  - [ ] Consider using managed database service (AWS RDS, Google Cloud SQL, etc.)

- [ ] **Static Files & Media**
  - [ ] Configure persistent volumes for media uploads
  - [ ] Consider using cloud storage (GCS, S3) for media
  - [ ] Set proper media permissions

- [ ] **Networking**
  - [ ] Configure reverse proxy (Nginx, Apache) in front of Gunicorn
  - [ ] Set up SSL/TLS certificates (Let's Encrypt recommended)
  - [ ] Restrict database network access
  - [ ] Use environment-specific configurations

- [ ] **Monitoring**
  - [ ] Set up logging aggregation
  - [ ] Configure health checks
  - [ ] Set up alerts for service failures
  - [ ] Monitor Gunicorn worker status

- [ ] **Backup & Recovery**
  - [ ] Automate database backups
  - [ ] Test backup restoration
  - [ ] Document recovery procedures
  - [ ] Version control `.env.dist` (not `.env`)

---

## Environment Variable Reference

### Required Variables
```env
DEBUG=False                           # Django debug mode (NEVER True in production)
SECRET_KEY=<secure-random-string>    # Django secret key (generate new one)
ALLOWED_HOSTS=domain.com,www.domain.com
DB_NAME=horilla                      # Database name
DB_USER=horilla_dba                  # Database user
DB_PASSWORD=<strong-password>        # Database password
DB_INIT_PASSWORD=<postgres-password> # Initial postgres user password
DB_HOST=db                           # Docker hostname for database
DB_PORT=5432                         # Database port
```

### Optional Variables
```env
TIME_ZONE=UTC
CSRF_TRUSTED_ORIGINS=https://domain.com
LANGUAGE_CODE=en-us
```

---

## Network Architecture

```
┌─────────────────────────────────────────┐
│         Host Machine (Port 8000)        │
│  ┌────────────────────────────────────┐ │
│  │ horilla-web (Django/Gunicorn)      │ │
│  │ - Exposes: 0.0.0.0:8000            │ │
│  │ - Network: horilla-network (bridge)│ │
│  │ - User: horilla (non-root)         │ │
│  └────────────────────────────────────┘ │
│           ↓ (internal network)           │
│  ┌────────────────────────────────────┐ │
│  │ horilla-db (PostgreSQL)             │ │
│  │ - Port: 5432 (internal only)       │ │
│  │ - Network: horilla-network (bridge)│ │
│  │ - User: postgres                   │ │
│  │ - Volume: horilla-data (persistent)│ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Gunicorn Worker Configuration

The current setup uses:
- **4 workers**: Suitable for 2-4 CPU cores and light-to-medium traffic
- **Sync workers**: Standard Django workers
- **120s timeout**: Allows long-running requests

For production, adjust based on:
- **High traffic**: Increase workers (e.g., `2 * CPU_count + 1`)
- **Heavy tasks**: Use async workers or Celery queue
- **Limited resources**: Reduce workers to 2

Example configuration:
```bash
# For 4 CPU cores
workers = 2 * 4 + 1 = 9

# For memory-constrained environment
workers = 2
```

---

## Common Issues & Solutions

### Issue: Database connection refused
```
Error: could not translate host name "db" to address
```
**Solution**: Ensure containers are on same network
```bash
docker-compose ps                    # Check if db service is running
docker-compose logs db              # Check database logs
docker-compose restart db           # Restart database
```

### Issue: Static files not serving
```
Error: 404 Not Found for /static/
```
**Solution**: Collect static files
```bash
docker-compose exec server python3 manage.py collectstatic --noinput
```

### Issue: Permission denied on media folder
```
Error: Permission denied creating media files
```
**Solution**: Check volume permissions
```bash
docker-compose exec server ls -la /app/media
docker-compose exec server python3 manage.py migrate
```

### Issue: Migrations fail on startup
```
Error: relation "..." does not exist
```
**Solution**: Manually run migrations
```bash
docker-compose down
docker volume rm horilla_horilla-data    # Remove existing data
docker-compose up -d                     # Restart (reinitializes)
```

---

## Security Best Practices

1. **Never commit `.env` file** - Only commit `.env.dist`
2. **Use strong passwords** - Minimum 20 characters, mixed case, numbers, symbols
3. **Rotate credentials regularly** - Update database passwords monthly
4. **Use HTTPS** - Always use SSL/TLS in production
5. **Restrict network access** - Don't expose database ports
6. **Monitor logs** - Regularly check container logs for errors
7. **Update images** - Keep base images updated (`python:3.11-slim-bookworm`, `postgres:16`)
8. **Limit resource usage** - Set memory and CPU limits
9. **Regular backups** - Automated daily database backups
10. **Secrets management** - Use proper secrets management (Docker Secrets, Vault, etc.)

---

## Next Steps

1. Create secure `.env` file with strong credentials
2. Build Docker images: `docker-compose build`
3. Start services: `docker-compose up -d`
4. Verify logs: `docker-compose logs -f`
5. Test application: `curl http://localhost:8000`
6. Monitor production deployment regularly

---

**Last Updated**: November 2024
**Changes Version**: 2.0 (Security Hardening)
