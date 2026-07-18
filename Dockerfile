FROM python:3.11-slim-bookworm AS builder

ARG REQUIREMENTS_FILE=requirements.txt

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libcairo2-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.phase0-windows-py311.lock requirements.staging.lock ./
RUN pip install --prefix=/install -r "${REQUIREMENTS_FILE}"


FROM python:3.11-slim-bookworm AS runtime

ENV PATH=/home/hydra/.local/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 libgdk-pixbuf-2.0-0 libpango-1.0-0 libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 hydra \
    && useradd --uid 10001 --gid hydra --create-home --shell /usr/sbin/nologin hydra

WORKDIR /app

COPY --from=builder /install /usr/local
COPY deployment/django_auth_migrations/0013_user_is_new_employee.py \
    /usr/local/lib/python3.11/site-packages/django/contrib/auth/migrations/0013_user_is_new_employee.py
COPY --chown=hydra:hydra . .

RUN python scripts/verify-migration-manifest.py \
    && chmod 0555 /app/entrypoint.sh \
    && install -d -o hydra -g hydra -m 0750 \
        /app/staticfiles /var/lib/hydra/media /var/lib/hydra/private \
        /var/lib/hydra/quarantine /var/lib/hydra/outbox

USER hydra

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready/', timeout=3).read()"

ENTRYPOINT ["/app/entrypoint.sh"]
