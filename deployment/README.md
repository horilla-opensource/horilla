# Horilla Docker Deployment

A simplified, production-ready Docker deployment configuration for Horilla HR Management System.

## Quick Start

1. **Copy environment template**:
   ```bash
   cp .env.dist .env
   ```

2. **Configure environment variables** in `.env`:
   ```env
   # Security
   SECRET_KEY=<generate-secure-key>
   DEBUG=False
   ALLOWED_HOSTS=your-domain.com

   # Database
   DB_PASSWORD=<strong-password>
   DB_INIT_PASSWORD=<postgres-password>
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**:
   ```bash
   curl http://localhost:8000
   ```

## Architecture

- **Web Server**: Django + Gunicorn (4 workers)
- **Database**: PostgreSQL 16 with automatic initialization
- **Security**: Non-root user, internal networking, environment-based config

## Configuration Files

- `docker-compose.yaml` - Service orchestration
- `Dockerfile` - Web application container
- `entrypoint.sh` - Application startup script
- `init-db.sh` - Database initialization
- `.env` - Environment configuration (create from .env.dist)

## Production Deployment

### Environment Variables

**Required**:
```env
SECRET_KEY=<django-secret-key>       # Generate at https://djecrety.ir
DEBUG=False                          # Never True in production
ALLOWED_HOSTS=domain.com             # Your actual domain
DB_PASSWORD=<strong-password>        # Database password (20+ chars)
DB_INIT_PASSWORD=<postgres-password> # PostgreSQL admin password
```

**Optional**:
```env
TIME_ZONE=UTC
CSRF_TRUSTED_ORIGINS=https://domain.com
DB_NAME=horilla
DB_USER=horilla_dba
DB_HOST=db
DB_PORT=5432
```

### Security Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Use strong passwords (20+ characters)
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Enable HTTPS with reverse proxy
- [ ] Never commit `.env` file

### Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f server

# Run Django commands
docker-compose exec server python manage.py migrate
docker-compose exec server python manage.py createsuperuser
docker-compose exec server python manage.py collectstatic

# Database access
docker-compose exec db psql -U postgres -d horilla

# Stop services
docker-compose down

# Remove data (reset)
docker-compose down -v
```

## Troubleshooting

### Common Issues

**Database connection failed**:
```bash
docker-compose logs db
docker-compose restart db
```

**Static files missing**:
```bash
docker-compose exec server python manage.py collectstatic --noinput
```

**Permission errors**:
```bash
docker-compose exec server ls -la /app/
```

### Logs

- Application: `docker-compose logs server`
- Database: `docker-compose logs db`
- All services: `docker-compose logs`

## Development vs Production

**Development**:
- Set `DEBUG=True`
- Use weak passwords for testing
- Expose database port for external access

**Production**:
- Set `DEBUG=False`
- Use strong passwords
- Hide database behind internal network
- Add reverse proxy (Nginx/Apache)
- Enable SSL/TLS
- Set up monitoring and backups

## Support

For issues with Horilla itself, visit: https://github.com/horilla-opensource/horilla

For deployment issues, check:
1. Container logs: `docker-compose logs`
2. Environment configuration in `.env`
3. Network connectivity between containers