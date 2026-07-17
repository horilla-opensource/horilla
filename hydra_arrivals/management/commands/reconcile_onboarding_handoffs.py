from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from hydra_arrivals.onboarding import reconcile_open_onboarding_handoffs


class Command(BaseCommand):
    help = "Reconcile open arrival-to-onboarding handoffs in a bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        try:
            result = reconcile_open_onboarding_handoffs(
                batch_size=options["batch_size"]
            )
        except ValidationError as error:
            raise CommandError(error.messages[0]) from error
        self.stdout.write(
            self.style.SUCCESS(
                "Onboarding handoffs reconciled: "
                f"selected={result.handoffs_selected}, "
                f"updated={result.handoffs_updated}, "
                f"completed={result.handoffs_completed}."
            )
        )
