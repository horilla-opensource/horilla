FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf-xlib-2.0-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        pkg-config \
        curl \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

# Copy application
COPY . .

# Set permissions
RUN mkdir -p staticfiles media \
    && chown -R appuser:appuser /app

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "horilla.wsgi:application", "--config", "docker/gunicorn.conf.py"]
