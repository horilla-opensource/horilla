# Production Dockerfile (multi-stage) for Horilla v2.0
# Builds Python wheels in a builder image, then installs them into a slim runtime.

FROM python:3.11-slim-bookworm AS builder

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
    PYTHONUNBUFFERED=1

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
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy project source
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Entrypoint runs migrations, collectstatic, admin creation, and gunicorn
CMD ["sh", "./entrypoint.sh"]
