import signal
from threading import Event
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError

from hydra_ops.maintenance import (
    acquire_maintenance_lock,
    release_maintenance_lock,
    run_maintenance_cycle,
    start_maintenance_state,
)
from hydra_ops.models import MaintenanceState


class Command(BaseCommand):
    help = "Run the single-owner Hydra maintenance worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--force-document-purge", action="store_true")

    def handle(self, *args, **options):
        if not acquire_maintenance_lock():
            raise CommandError("another Hydra maintenance worker owns the lock")
        stop = Event()
        previous_handlers = {}

        def request_stop(signum, frame):
            stop.set()

        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, request_stop)

        owner_uuid = uuid4()
        try:
            start_maintenance_state(owner_uuid=owner_uuid)
            force_document_purge = options["force_document_purge"]
            while not stop.is_set():
                try:
                    result = run_maintenance_cycle(
                        owner_uuid=owner_uuid,
                        force_document_purge=force_document_purge,
                    )
                except OperationalError as error:
                    raise CommandError("maintenance database connection failed") from error
                self.stdout.write(
                    "maintenance cycle: "
                    f"notifications={result.notifications_sent}/{result.notifications_selected}, "
                    f"legalization={result.legalization_notifications_sent}/"
                    f"{result.legalization_notifications_selected}, "
                    f"legalization_work={result.legalization_work_notifications_sent}/"
                    f"{result.legalization_work_notifications_selected}, "
                    f"tasks={result.task_notifications_sent}/"
                    f"{result.task_notifications_selected}, "
                    f"notification_email={result.notification_emails_sent}/"
                    f"{result.notification_emails_selected}, "
                    f"notification_email_dead={result.notification_emails_dead}, "
                    f"expired={result.legalization_cases_expired}, "
                    f"arrivals={result.arrival_notifications_sent}/"
                    f"{result.arrival_notifications_selected}, "
                    f"onboarding={result.onboarding_handoffs_updated}/"
                    f"{result.onboarding_handoffs_selected}, "
                    f"onboarding_completed={result.onboarding_handoffs_completed}, "
                    f"portal_email={result.portal_emails_sent}/"
                    f"{result.portal_emails_selected}, "
                    f"portal_email_dead={result.portal_emails_dead}, "
                    f"quarantine={result.quarantine_purged}, "
                    f"deleted_files={result.deleted_documents_purged}, "
                    f"candidate_imports={result.candidate_imports_purged}, "
                    f"errors={len(result.errors)}"
                )
                state = MaintenanceState.objects.get(pk="primary")
                if state.consecutive_failures >= settings.HYDRA_MAINTENANCE_MAX_FAILURES:
                    raise CommandError("maintenance failure threshold reached")
                if options["once"]:
                    break
                force_document_purge = False
                stop.wait(settings.HYDRA_MAINTENANCE_INTERVAL_SECONDS)
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            release_maintenance_lock()
