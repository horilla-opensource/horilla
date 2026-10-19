"""A failing scheduled job is reported with its traceback."""

import logging
import traceback
from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from django.test import SimpleTestCase

from base.management.commands.run_scheduler import log_job_error


def failing_job():
    raise TypeError("'NoneType' object is not iterable")


class TestJobErrorLogging(SimpleTestCase):
    def test_the_error_is_logged_with_its_traceback(self):
        # Built the way APScheduler's executor builds it: `traceback` is a
        # formatted string, the exception keeps its own traceback.
        try:
            failing_job()
        except TypeError as exc:
            event = JobExecutionEvent(
                EVENT_JOB_ERROR,
                "job1",
                "default",
                datetime.now(),
                exception=exc,
                traceback="".join(traceback.format_tb(exc.__traceback__)),
            )

        with self.assertLogs(
            "base.management.commands.run_scheduler", logging.ERROR
        ) as logs:
            log_job_error(event)

        text = logging.Formatter().format(logs.records[0])
        self.assertIn("Scheduled job job1 raised TypeError", text)
        self.assertIn("in failing_job", text)
        self.assertIn("TypeError: 'NoneType' object is not iterable", text)
