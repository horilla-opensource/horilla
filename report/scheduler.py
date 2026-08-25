"""
APScheduler bootstrap for standard report subscriptions.

Copy pattern from payroll/scheduler.py — BackgroundScheduler with argv guards.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_SKIP_ARGV = (
    "makemigrations",
    "migrate",
    "compilemessages",
    "flush",
    "shell",
    "test",
    "collectstatic",
)


def run_report_subscriptions():
    """Hourly poll entrypoint used by APScheduler."""
    from report.delivery import run_due_subscriptions

    results = run_due_subscriptions()
    sent = sum(1 for r in results if r.ok)
    skipped = sum(1 for r in results if r.status in ("skipped", "inactive"))
    failed = sum(
        1 for r in results if not r.ok and r.status not in ("skipped", "inactive")
    )
    if results:
        logger.info(
            "Report subscriptions poll: %s sent, %s skipped, %s failed/denied",
            sent,
            skipped,
            failed,
        )


def _should_start_scheduler() -> bool:
    return not any(cmd in sys.argv for cmd in _SKIP_ARGV)


if _should_start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_report_subscriptions,
            "interval",
            hours=1,
            id="report_subscriptions",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info("Report subscription scheduler started (hourly)")
    except Exception:
        logger.exception("Could not start report subscription scheduler")
