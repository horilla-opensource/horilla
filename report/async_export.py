"""Background export delivery for heavy standard-report downloads (Phase 8)."""

from __future__ import annotations

import logging
import threading

from django.core.mail import EmailMessage
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def queue_export_email(
    *,
    user_id: int,
    to_email: str,
    slug: str,
    fmt: str,
    filters_dict: dict,
    meta: dict,
    filename: str = "",
) -> None:
    """Spawn a daemon thread that builds the export and emails it."""

    def _run():
        try:
            import report.metrics  # noqa: F401
            from base.backends import ConfiguredEmailBackend
            from report.engine import filters_from_dict
            from report.export import export_csv, export_pdf, export_xlsx
            from report.registry import get_report, run_report

            definition = get_report(slug)
            if not definition:
                logger.warning("Async export: unknown report %s", slug)
                return

            filters = filters_from_dict(filters_dict)
            filters.extra["row_limit"] = 5000
            payload = run_report(slug, filters)
            safe = slug.replace("/", "-")
            fmt_local = (fmt or "xlsx").lower()
            if fmt_local == "csv":
                filename_local = filename or f"{safe}.csv"
                response = export_csv(payload, filename=filename_local, meta=meta)
                content_type = "text/csv"
            elif fmt_local == "pdf":
                filename_local = filename or f"{safe}.pdf"
                response = export_pdf(payload, filename=filename_local, meta=meta)
                content_type = "application/pdf"
            else:
                fmt_local = "xlsx"
                filename_local = filename or f"{safe}.xlsx"
                response = export_xlsx(payload, filename=filename_local, meta=meta)
                content_type = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            backend = ConfiguredEmailBackend()
            from_email = (
                getattr(backend, "dynamic_from_email_with_display_name", None) or ""
            )
            if not from_email:
                logger.warning(
                    "Async export for %s skipped — email server not configured", slug
                )
                return

            subject = _("Horilla report ready: %(name)s") % {
                "name": str(definition.name)
            }
            body = _(
                "Your requested export is attached.\n\nReport: %(name)s\nFormat: %(fmt)s"
            ) % {"name": str(definition.name), "fmt": fmt_local}
            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[to_email],
                connection=backend,
            )
            msg.attach(filename_local, response.content, content_type)
            sent = msg.send(fail_silently=False)
            logger.info(
                "Async export emailed user_id=%s slug=%s fmt=%s sent=%s",
                user_id,
                slug,
                fmt_local,
                sent,
            )
        except Exception:
            logger.exception(
                "Async export failed for slug=%s user_id=%s", slug, user_id
            )

    thread = threading.Thread(target=_run, name=f"report-export-{slug}", daemon=True)
    thread.start()
