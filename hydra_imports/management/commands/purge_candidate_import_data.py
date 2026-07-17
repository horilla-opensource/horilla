from django.core.management.base import BaseCommand, CommandError

from hydra_imports.services import purge_expired_candidate_import_data


class Command(BaseCommand):
    help = "Redact expired candidate-import source data while retaining audit evidence."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= 1000:
            raise CommandError("limit must be between 1 and 1000")
        purged = purge_expired_candidate_import_data(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"candidate imports redacted: {purged}"))
