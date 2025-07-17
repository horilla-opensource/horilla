"""
pg_backup.scheduler

This module sets up scheduled PostgreSQL backups using APScheduler and pg_dump.

Backups are only enabled if the configured Django database engine is PostgreSQL.
It supports backing up the default Django database at multiple daily times,
configured via environment variables.

Environment Variables:
----------------------
- BACKUP_CRON_TIMES (str, optional)
    A comma-separated list of times in 24h format ("HH:MM") to run backups.
    Example: "02:00,10:00,18:00"
    Default: "02:00,10:00,18:00"
    If unset or empty, scheduling is disabled and no automated backups will run.

- BACKUP_DIR (str, optional)
    Directory path where PostgreSQL backups will be stored.
    Default: <project_root>/pg_backup/backups

Requirements:
-------------
- The system must have `pg_dump` available in PATH.
- The database user must have permission to perform backups.
- APScheduler and django-environ must be installed and configured.

Logging:
--------
Logs are emitted using the `pg_backup` logger and include backup progress and scheduler setup.
Logging format and handlers can be customized via `LOGGING_CONFIG` in this module.

Usage:
------
This module is automatically executed when imported (e.g., from Django AppConfig's `ready()`).
Backups can also be triggered manually by calling `backup_postgres()`.

"""

import datetime
import logging
import logging.config
import os
import shutil
import subprocess
from pathlib import Path

import environ
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

# === Logging Configuration ===

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "pg_backup": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("pg_backup")

# === Configuration ===

env = environ.Env()

default_backup_dir = Path(settings.BASE_DIR) / "pg_backup" / "backups"
BACKUP_DIR = Path(env("BACKUP_DIR", default=str(default_backup_dir)))
BACKUP_CRON_TIMES = env("BACKUP_CRON_TIMES", default="02:00,10:00,18:00")
DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"

# Load DB settings
db = settings.DATABASES["default"]
DB_ENGINE = db["ENGINE"]

if "postgresql" not in DB_ENGINE:
    logger.warning(
        "Skipping backup scheduler: not a PostgreSQL database (engine: %s)", DB_ENGINE
    )
else:
    DB_NAME = db["NAME"]
    DB_USER = db["USER"]
    DB_PASSWORD = db["PASSWORD"]
    DB_HOST = db.get("HOST", "localhost")
    DB_PORT = str(db.get("PORT", 5432))

    def backup_postgres():
        """
        Method that dump pg data
        """
        timestamp = datetime.datetime.now().strftime(DATE_FORMAT)
        backup_file = BACKUP_DIR / f"{DB_NAME}_backup_{timestamp}.sql"

        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.environ["PGPASSWORD"] = DB_PASSWORD

        command = [
            shutil.which("pg_dump"),
            "-h",
            DB_HOST,
            "-p",
            DB_PORT,
            "-U",
            DB_USER,
            "-F",
            "c",
            "-b",
            "-v",
            "-f",
            str(backup_file),
            DB_NAME,
        ]

        try:
            logger.info("Starting backup: %s", backup_file)
            subprocess.run(command, check=True)
            logger.info("Backup successful: %s", backup_file)
        except subprocess.CalledProcessError as e:
            logger.error("Backup failed: %s", e)
        finally:
            os.environ.pop("PGPASSWORD", None)

    def start():
        """
        Start the scheduler
        """
        if not BACKUP_CRON_TIMES:
            logger.warning("BACKUP_CRON_TIMES not set. Scheduler is disabled.")
            return

        scheduler = BackgroundScheduler()
        times = [t.strip() for t in BACKUP_CRON_TIMES.split(",")]

        for time_str in times:
            try:
                hour, minute = map(int, time_str.split(":"))
                scheduler.add_job(
                    backup_postgres,
                    "cron",
                    hour=hour,
                    minute=minute,
                    id=f"backup_{hour}_{minute}",
                    replace_existing=True,
                )
                logger.info("Backup scheduled at %02d:%02d", hour, minute)
            except ValueError:
                logger.error("Invalid time format in BACKUP_CRON_TIMES: '%s'", time_str)

        scheduler.start()

    # Start the scheduler
    start()
