from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hydra_legalization.automation import run_legalization_automation


class Command(BaseCommand):
    help = "Run one bounded legalization reminder/expiry automation cycle."

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="run_date")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000")
        run_date = None
        if options["run_date"]:
            try:
                run_date = date.fromisoformat(options["run_date"])
            except ValueError as error:
                raise CommandError("--date must use YYYY-MM-DD") from error
            if run_date > timezone.localdate():
                raise CommandError("--date cannot be in the future")
        result = run_legalization_automation(
            today=run_date,
            case_limit=limit,
            notification_limit=limit,
        )
        summary = (
            f"Cases: {result.cases_selected}; events: {result.events_created}; "
            f"expired: {result.cases_expired}; notifications: "
            f"{result.notifications_sent}/{result.notifications_selected}; "
            f"failed: {result.notifications_failed}."
        )
        if result.notifications_failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
