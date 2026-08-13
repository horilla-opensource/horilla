"""Compliance / audit standard reports (Phase 2 starter pack)."""

from __future__ import annotations

from django.apps import apps
from django.db.models import Count
from django.utils.translation import gettext as _

from report.engine import ReportFilters, empty_report


def audit_activity(filters: ReportFilters) -> dict:
    """Recent audit log activity summary when horilla_audit / auditlog is available."""
    try:
        from auditlog.models import LogEntry
    except Exception:
        return empty_report(
            _("Audit Activity"),
            filters,
            _("Audit log is not available in this installation."),
        )

    qs = LogEntry.objects.filter(
        timestamp__date__gte=filters.from_date,
        timestamp__date__lte=filters.to_date,
    )
    total = qs.count()
    by_action = list(qs.values("action").annotate(count=Count("id")).order_by("-count"))
    action_labels = {0: _("Create"), 1: _("Update"), 2: _("Delete"), 3: _("Access")}
    by_model = list(
        qs.values("content_type__app_label", "content_type__model")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )

    return {
        "title": _("Audit Activity"),
        "kpis": [
            {"label": _("Log entries"), "value": total, "hint": _("In period")},
            {
                "label": _("Models touched"),
                "value": len(by_model),
                "hint": _("Top 20 shown"),
            },
            {
                "label": _("Action types"),
                "value": len(by_action),
                "hint": "",
            },
            {
                "label": _("Deletes"),
                "value": next((r["count"] for r in by_action if r["action"] == 2), 0),
                "hint": _("Action=delete"),
            },
        ],
        "charts": [
            {
                "id": "audit_actions",
                "type": "donut",
                "title": _("Actions"),
                "categories": [
                    action_labels.get(r["action"], str(r["action"])) for r in by_action
                ],
                "series": [
                    {"name": _("Count"), "data": [r["count"] for r in by_action]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "app", "label": _("App")},
                {"key": "model", "label": _("Model")},
                {"key": "count", "label": _("Events")},
            ],
            "rows": [
                {
                    "app": r["content_type__app_label"],
                    "model": r["content_type__model"],
                    "count": r["count"],
                }
                for r in by_model
            ],
        },
    }


def document_expiry(filters: ReportFilters) -> dict:
    """Expiring employee / asset documents when models exist."""
    rows = []
    kpis_docs = 0

    if apps.is_installed("employee"):
        try:
            from employee.models import DisciplinaryAction  # may not be docs

            pass
        except Exception:
            pass
        # Employee documents often live as DocumentRequest / EmployeeDocument
        for model_name in ("Document", "EmployeeDocument", "DocumentRequest"):
            try:
                Model = apps.get_model("employee", model_name)
            except LookupError:
                continue
            date_fields = [
                f.name
                for f in Model._meta.fields
                if f.name in ("expiry_date", "expire_date", "end_date", "valid_until")
            ]
            if not date_fields:
                continue
            field = date_fields[0]
            qs = Model.objects.filter(
                **{
                    f"{field}__gte": filters.from_date,
                    f"{field}__lte": filters.to_date,
                }
            )
            kpis_docs += qs.count()
            for obj in qs[:100]:
                rows.append(
                    {
                        "source": f"employee.{model_name}",
                        "title": str(obj),
                        "expiry": str(getattr(obj, field, "")),
                    }
                )

    if apps.is_installed("asset"):
        try:
            from asset.models import Asset

            if hasattr(Asset, "expiry_date"):
                qs = Asset.objects.filter(
                    expiry_date__gte=filters.from_date,
                    expiry_date__lte=filters.to_date,
                )
                kpis_docs += qs.count()
                for obj in qs[:100]:
                    rows.append(
                        {
                            "source": "asset.Asset",
                            "title": str(obj),
                            "expiry": str(obj.expiry_date),
                        }
                    )
        except Exception:
            pass

    if not rows and not kpis_docs:
        return empty_report(
            _("Document Expiry"),
            filters,
            _("No expiring documents found for the selected period."),
        )

    return {
        "title": _("Document Expiry"),
        "kpis": [
            {
                "label": _("Expiring items"),
                "value": kpis_docs or len(rows),
                "hint": _("In period"),
            },
            {"label": _("Listed"), "value": len(rows), "hint": _("Capped at 200")},
        ],
        "charts": [],
        "table": {
            "columns": [
                {"key": "source", "label": _("Source")},
                {"key": "title", "label": _("Item")},
                {"key": "expiry", "label": _("Expiry")},
            ],
            "rows": rows,
        },
    }
