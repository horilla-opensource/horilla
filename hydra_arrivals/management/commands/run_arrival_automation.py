from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hydra_arrivals.automation import run_arrival_automation


class Command(BaseCommand):
    help = "Run one bounded arrival reminder/overdue automation cycle."

    def add_arguments(self, parser):
        parser.add_argument("--at", dest="run_at")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000")
        run_at = None
        if options["run_at"]:
            try:
                run_at = datetime.fromisoformat(options["run_at"])
            except ValueError as error:
                raise CommandError("--at must use ISO 8601 date/time") from error
            if timezone.is_naive(run_at):
                run_at = timezone.make_aware(run_at)
            if run_at > timezone.now():
                raise CommandError("--at cannot be in the future")
        result = run_arrival_automation(
            now=run_at,
            plan_limit=limit,
            notification_limit=limit,
        )
        summary = (
            f"Plans: {result.plans_selected}; events: {result.events_created}; "
            f"notifications: {result.notifications_sent}/"
            f"{result.notifications_selected}; failed: "
            f"{result.notifications_failed}."
        )
        if result.notifications_failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
