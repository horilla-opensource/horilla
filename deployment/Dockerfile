# Use an official Python runtime as a parent image
# We choose python:3.11-slim-bookworm for a supported and smaller image size
FROM python:3.11-slim-bookworm

# Set environment variables for the application
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install necessary system dependencies, including those required for PostgreSQL client (psycopg2)
# and git for cloning (though we assume the code is already checked out)
# and the virtual environment tools (which are generally not needed in a container)
# We focus on the build dependencies for psycopg2 and other tools.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better Docker caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app/

# Copy deployment files
COPY deployment/entrypoint.sh /app/deployment/
COPY deployment/init-db.sh /app/deployment/

# Make scripts executable and create directories
RUN chmod +x /app/deployment/entrypoint.sh && \
    chmod +x /app/deployment/init-db.sh && \
    mkdir -p /app/staticfiles /app/media

# Create a non-root user for running the application
RUN adduser --disabled-password --gecos "" horilla && \
    chown -R horilla:horilla /app

# Switch to the non-root user for running the application
USER horilla

# Expose the port the app runs on
EXPOSE 8000

# Use entrypoint script for initialization and running the app
CMD ["/app/deployment/entrypoint.sh"]