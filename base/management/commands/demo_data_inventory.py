"""Print SIDEBAR UI models with zero demo rows. Gap register after seed."""

from django.core.management.base import BaseCommand, CommandError

from base.demo_data.inventory import count_sidebar_models, zero_row_models


class Command(BaseCommand):
    help = (
        "List SIDEBAR (plus Base request/holiday/mail/tag) models and their "
        "row counts after demo seed. Use --fail-on-empty as the gap register."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-empty",
            action="store_true",
            help="Exit non-zero if any inventory model has zero rows.",
        )

    def handle(self, *args, **options):
        for label, n in count_sidebar_models():
            line = f"{n:6d}  {label}"
            if n == 0:
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)

        empty = zero_row_models()
        if not empty:
            self.stdout.write(self.style.SUCCESS("No empty SIDEBAR UI models."))
            return
        self.stdout.write(
            self.style.WARNING(f"{len(empty)} empty model(s): {', '.join(empty)}")
        )
        if options["fail_on_empty"]:
            raise CommandError(f"Empty UI models: {', '.join(empty)}")
