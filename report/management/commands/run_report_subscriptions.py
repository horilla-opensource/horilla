from django.core.management.base import BaseCommand

from report.delivery import run_due_subscriptions


class Command(BaseCommand):
    help = (
        "Process due standard-report email subscriptions "
        "(or force one with --force-id)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-id",
            type=int,
            default=None,
            help="Force-run a single ReportSubscription primary key.",
        )

    def handle(self, *args, **options):
        force_id = options.get("force_id")
        results = run_due_subscriptions(force_id=force_id)
        if not results:
            self.stdout.write(self.style.WARNING("No subscriptions processed."))
            return
        for result in results:
            line = f"{result.status}: {result.detail or ''}".strip()
            if result.ok:
                self.stdout.write(self.style.SUCCESS(line))
            elif result.status in ("skipped", "inactive"):
                self.stdout.write(line)
            else:
                self.stdout.write(self.style.ERROR(line))
