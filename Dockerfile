# Builder stage for docker image to build python reqs
FROM python:3.12.9-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .

RUN pip wheel --wheel-dir=/wheels --no-cache-dir -r requirements.txt


# Main Docker Image
FROM python:3.12.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /app /app

RUN pip install --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Create a local user and group to run the app
RUN groupadd -g 1007 -r app && \
    useradd -u 1006 -d /app -M -r -g app app && \
    mkdir /app/staticfiles && \
    chown -R app:app /usr/local/lib/python3.12/site-packages

COPY . .

RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["./entrypoint.sh"]
