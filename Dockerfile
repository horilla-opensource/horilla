# Production Dockerfile (multi-stage) for Horilla v2.0
# Builds Python wheels in builder image, then installs them into a slim runtime.

FROM python:3.11-slim-bookworm AS python-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps required to build certain Python packages and render PDFs/images
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libmagic1 \
    libssl-dev \
    gettext \
    git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage layer caching for deps
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
  && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# ---------------------------- Runtime image ----------------------------
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=horilla.settings

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Runtime libs only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libjpeg62-turbo \
    zlib1g \
    libmagic1 \
    libpq5 \
    gettext \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install built wheels
COPY --from=python-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
  && rm -rf /wheels

# Copy project source
COPY . .

# Create required directories and set permissions
RUN mkdir -p /app/media /app/staticfiles \
  && chown -R appuser:appuser /app

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health/', timeout=10)" || exit 1

# Entrypoint runs migrations, collectstatic, admin creation, and gunicorn
CMD ["sh", "./entrypoint.sh"]
