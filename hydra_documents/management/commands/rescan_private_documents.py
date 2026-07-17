from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hydra_documents.audit import AccessContext, log_access
from hydra_documents.models import DocumentAccessLog, PrivateDocument
from hydra_documents.scanning import ScannerError, scan_file


SYSTEM_CONTEXT = AccessContext(ip_address=None, user_agent_sha256="")


class Command(BaseCommand):
    help = "Scan legacy private documents; unscanned files remain download-blocked."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        queryset = PrivateDocument.objects.filter(
            scanned_at__isnull=True,
            deleted_at__isnull=True,
        ).exclude(file="").order_by("pk")
        if options["limit"] > 0:
            queryset = queryset[: options["limit"]]

        clean = infected = errors = 0
        for document in queryset.iterator():
            try:
                with document.file.open("rb") as source:
                    result = scan_file(source)
            except (ScannerError, OSError):
                errors += 1
                log_access(
                    actor=None,
                    context=SYSTEM_CONTEXT,
                    document=document,
                    document_uuid=document.uuid,
                    action=DocumentAccessLog.Action.SCAN,
                    outcome=DocumentAccessLog.Outcome.ERROR,
                    reason="legacy_scan_failed",
                )
                continue

            now = timezone.now()
            if result.clean:
                PrivateDocument.objects.filter(pk=document.pk).update(
                    scanner=result.scanner,
                    scanned_at=now,
                )
                clean += 1
                outcome = DocumentAccessLog.Outcome.ALLOWED
                reason = "legacy_scan_clean"
            else:
                file_name = document.file.name
                PrivateDocument.objects.filter(pk=document.pk).update(
                    scanner=result.scanner,
                    scanned_at=now,
                    deleted_at=now,
                    deletion_reason="Threat detected during legacy rescan",
                )
                try:
                    document.file.storage.delete(file_name)
                except OSError:
                    pass
                else:
                    PrivateDocument.objects.filter(pk=document.pk).update(
                        file="", file_purged_at=timezone.now()
                    )
                infected += 1
                outcome = DocumentAccessLog.Outcome.DENIED
                reason = "legacy_threat_detected"
            log_access(
                actor=None,
                context=SYSTEM_CONTEXT,
                document=document,
                document_uuid=document.uuid,
                action=DocumentAccessLog.Action.SCAN,
                outcome=outcome,
                reason=reason,
            )

        summary = f"Clean: {clean}; threats: {infected}; errors: {errors}."
        if errors:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
