# Build stage - for compiling dependencies
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
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
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
# gunicorn and psycopg2-binary are pinned in requirements.txt -- do not repeat
# them here, an unpinned CLI copy silently overrides the pin.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Production stage - minimal runtime image
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
        libcairo2 \
        libpango-1.0-0 \
        libgdk-pixbuf-xlib-2.0-0 \
        libxml2 \
        libxslt1.1 \
        libffi8 \
        curl \
        netcat-openbsd \
        gettext \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user FIRST
RUN useradd --create-home --uid 1000 appuser

# Copy virtual environment from builder stage WITH correct ownership
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Compile gettext catalogs (.po -> .mo): nothing in the repo or the runtime
# compiles them, so without this every non-English locale silently renders
# English. Plain msgfmt, so no Django settings/DB are needed at build time.
RUN find . -name '*.po' -execdir sh -c 'msgfmt "$1" -o "${1%.po}.mo"' _ {} \;

# Copy entrypoint script
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Both COPYs above already set --chown, so only the new dirs need ownership;
# a recursive chown over /app would duplicate a whole layer for no gain.
RUN mkdir -p staticfiles media \
    && chown appuser:appuser staticfiles media

USER appuser

# Build metadata. VERSION should match horilla/__version__.py and the release
# tag; the publish workflow passes all three and fails if they disagree.
ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="Horilla HR" \
      org.opencontainers.image.description="Free and open source HR software" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/horilla/horilla-hr" \
      org.opencontainers.image.url="https://www.horilla.com" \
      org.opencontainers.image.documentation="https://docs.horilla.com" \
      org.opencontainers.image.vendor="Horilla" \
      org.opencontainers.image.licenses="LGPL-2.1"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "horilla.wsgi:application", "--config", "docker/gunicorn.conf.py"]
