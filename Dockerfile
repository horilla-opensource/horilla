# syntax=docker/dockerfile:1

# -------- Base image with dependencies layer --------
FROM python:3.11-slim AS base

# System deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Install build deps for common Python packages (incl. cairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -------- Builder for wheels --------
FROM base AS builder
COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# -------- Final runtime image --------
FROM python:3.11-slim AS runtime

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Install runtime deps for libraries like psycopg2, cairo, etc. (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libjpeg62-turbo \
    zlib1g \
    libxml2 \
    libxslt1.1 \
    libffi8 \
    libfreetype6 \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*

# Copy project
COPY . .

# Ensure static dirs exist and are owned by app
RUN mkdir -p /app/staticfiles /app/static_root && chown -R app:app /app

# Gunicorn config
ENV PORT=8000 \
    GUNICORN_CMD_ARGS="--config deploy/gunicorn.conf.py"

# Entrypoint
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app
EXPOSE 8000

CMD ["/entrypoint.sh"]
