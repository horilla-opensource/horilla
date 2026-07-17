from django.core.management.base import BaseCommand, CommandError

from hydra_documents.services import (
    purge_deleted_document_files,
    purge_expired_quarantine,
)


class Command(BaseCommand):
    help = "Purge expired quarantine blobs and retry deleted-document storage cleanup."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1000)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 10000:
            raise CommandError("--limit must be between 1 and 10000")
        quarantined = purge_expired_quarantine(limit=limit)
        deleted = purge_deleted_document_files(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {quarantined} quarantine blob(s) and "
                f"{deleted} deleted-document blob(s)."
            )
        )
