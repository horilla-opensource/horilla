import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = max(2, min(multiprocessing.cpu_count() * 2 + 1, 8))
worker_class = "gthread"
threads = 4
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeout
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "horilla-hrms"

# Server mechanics
pidfile = "/tmp/gunicorn.pid"
user = None  # Run as current user in container
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
