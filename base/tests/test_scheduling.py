"""
Scheduled jobs must be registered, not started at import.

The bug this guards: every ``<app>/scheduler.py`` used to build its own
BackgroundScheduler and call ``.start()`` at import time via AppConfig.ready().
gunicorn runs up to 8 workers with preload_app=False, so each worker started its
own copy of every job -- payroll generation and database backups ran up to 8
times per interval.
"""

from django.core.management import call_command
from django.test import SimpleTestCase
from django.utils.module_loading import module_has_submodule

from horilla.scheduling import (
    ScheduledJob,
    clear_registry,
    get_registered_jobs,
    register_job,
)

# Reconfigured at runtime rather than statically registered, so they still own a
# live scheduler. See the ponytail: comments in those modules.
RUNTIME_CONFIGURED = {"horilla_backup", "pg_backup"}


class RegistryTests(SimpleTestCase):
    def setUp(self):
        self._saved = get_registered_jobs()
        clear_registry()

    def tearDown(self):
        clear_registry()
        for job in self._saved:
            register_job(job.func, job.trigger, job_id=job.job_id, **job.kwargs)

    def test_register_job_records_trigger_and_kwargs(self):
        def dummy():
            pass

        register_job(dummy, "interval", hours=4)
        jobs = get_registered_jobs()

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].trigger, "interval")
        self.assertEqual(jobs[0].kwargs, {"hours": 4})

    def test_job_id_defaults_to_module_qualified_name(self):
        def dummy():
            pass

        register_job(dummy, "interval", hours=1)
        # Stable across restarts, so the jobstore replaces rather than
        # accumulating a duplicate row on every boot.
        self.assertEqual(get_registered_jobs()[0].job_id, f"{dummy.__module__}.dummy")

    def test_same_callable_may_register_under_distinct_ids(self):
        def dummy():
            pass

        register_job(dummy, "interval", minutes=30)
        register_job(dummy, "cron", job_id="dummy_daily", hour=0)

        self.assertEqual(len(get_registered_jobs()), 2)

    def test_clashing_job_id_raises_rather_than_silently_overwriting(self):
        def one():
            pass

        def two():
            pass

        register_job(one, "interval", job_id="shared", hours=1)
        with self.assertRaises(ValueError):
            register_job(two, "interval", job_id="shared", hours=1)


class NoSchedulerStartsAtImportTests(SimpleTestCase):
    """
    Importing an app's scheduler module must not start a scheduler.

    Asserted structurally rather than by importing and inspecting threads: a
    started scheduler is a side effect that would already have happened by the
    time this test runs.
    """

    def test_app_schedulers_do_not_call_start_at_import(self):
        from django.apps import apps

        offenders = []
        for config in apps.get_app_configs():
            if config.label in RUNTIME_CONFIGURED:
                continue
            if not module_has_submodule(config.module, "scheduler"):
                continue
            path = f"{config.path}/scheduler.py"
            with open(path) as handle:
                source = handle.read()
            for lineno, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if ".start()" in stripped and "scheduler" in stripped:
                    offenders.append(f"{path}:{lineno}")

        self.assertEqual(
            offenders,
            [],
            "Scheduler started at import time -- this runs once per gunicorn "
            "worker. Register the job with horilla.scheduling.register_job "
            "instead; run_scheduler owns execution.",
        )

    def test_every_registered_job_is_discoverable(self):
        jobs = get_registered_jobs()
        self.assertTrue(jobs, "No jobs registered -- scheduler modules not imported?")
        for job in jobs:
            self.assertIsInstance(job, ScheduledJob)
            self.assertTrue(callable(job.func))
            self.assertTrue(job.job_id)

    def test_run_scheduler_list_does_not_start_anything(self):
        # --list must be safe to run anywhere, including a deploy shell.
        call_command("run_scheduler", "--list")
