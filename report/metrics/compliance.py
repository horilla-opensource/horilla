"""Compliance / audit standard reports (Phase 2 starter pack)."""

from __future__ import annotations

from django.apps import apps
from django.db.models import Count
from django.utils.translation import gettext as _

from report.engine import ReportFilters, apply_org_filters, empty_report


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
    """Expiring employee documents (horilla_documents) and optional assets."""
    rows = []
    kpis_docs = 0

    if apps.is_installed("horilla_documents"):
        try:
            Document = apps.get_model("horilla_documents", "Document")
            qs = Document.objects.filter(
                expiry_date__gte=filters.from_date,
                expiry_date__lte=filters.to_date,
                expiry_date__isnull=False,
            )
            qs = apply_org_filters(
                qs,
                filters,
                prefix="employee_id__employee_work_info",
                employee_prefix="employee_id",
            )
            kpis_docs += qs.count()
            for obj in qs.select_related("employee_id")[:100]:
                emp = getattr(obj, "employee_id", None)
                rows.append(
                    {
                        "source": "horilla_documents.Document",
                        "title": str(obj),
                        "employee": emp.get_full_name() if emp else "",
                        "expiry": str(obj.expiry_date),
                    }
                )
        except Exception:
            pass

    if apps.is_installed("asset"):
        try:
            from asset.models import Asset

            if hasattr(Asset, "expiry_date"):
                qs = Asset.objects.filter(
                    expiry_date__gte=filters.from_date,
                    expiry_date__lte=filters.to_date,
                    expiry_date__isnull=False,
                )
                kpis_docs += qs.count()
                for obj in qs[:100]:
                    rows.append(
                        {
                            "source": "asset.Asset",
                            "title": str(obj),
                            "employee": "",
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
                {"key": "employee", "label": _("Employee")},
                {"key": "expiry", "label": _("Expiry")},
            ],
            "rows": rows,
        },
    }


def visa_contract_expiry(filters: ReportFilters) -> dict:
    """
    Contracts ending + documents with expiry in/near period.

    Labeled carefully: document rows are not assumed to be visas unless the
    title/request suggests visa/passport/work-permit.
    """
    from datetime import timedelta

    from django.apps import apps

    today = filters.to_date
    horizon_end = max(filters.to_date, today + timedelta(days=90))
    rows = []
    contracts_ending = 0
    visa_like = 0
    other_docs = 0

    try:
        from payroll.models.models import Contract

        qs = Contract.objects.filter(
            contract_end_date__gte=filters.from_date,
            contract_end_date__lte=horizon_end,
            contract_status__in=["active", "expired", "draft"],
        ).select_related("employee_id")
        qs = apply_org_filters(
            qs,
            filters,
            prefix="employee_id__employee_work_info",
            employee_prefix="employee_id",
            apply_employment_status=False,
        )
        contracts_ending = qs.count()
        for c in qs.order_by("contract_end_date")[:100]:
            emp = c.employee_id
            rows.append(
                {
                    "kind": _("Employment contract"),
                    "title": c.contract_name or str(c),
                    "employee": emp.get_full_name() if emp else "",
                    "expiry": (
                        c.contract_end_date.isoformat() if c.contract_end_date else ""
                    ),
                    "status": c.contract_status or "",
                }
            )
    except Exception:
        pass

    # Also surface work_info.contract_end_date when payroll Contract is absent
    try:
        from employee.models import EmployeeWorkInformation

        wi_qs = EmployeeWorkInformation.objects.filter(
            contract_end_date__gte=filters.from_date,
            contract_end_date__lte=horizon_end,
        )
        wi_qs = apply_org_filters(
            wi_qs, filters, prefix="", employee_prefix="employee_id"
        )
        for wi in wi_qs.select_related("employee_id")[:50]:
            emp = wi.employee_id
            rows.append(
                {
                    "kind": _("Work-info contract end"),
                    "title": _("contract_end_date"),
                    "employee": emp.get_full_name() if emp else "",
                    "expiry": wi.contract_end_date.isoformat(),
                    "status": "",
                }
            )
    except Exception:
        pass

    visa_tokens = (
        "visa",
        "passport",
        "work permit",
        "work-permit",
        "i-9",
        "immigration",
    )
    if apps.is_installed("horilla_documents"):
        try:
            Document = apps.get_model("horilla_documents", "Document")
            docs = Document.objects.filter(
                expiry_date__gte=filters.from_date,
                expiry_date__lte=horizon_end,
                expiry_date__isnull=False,
            )
            docs = apply_org_filters(
                docs,
                filters,
                prefix="employee_id__employee_work_info",
                employee_prefix="employee_id",
            )
            for obj in docs.select_related("employee_id", "document_request_id")[:100]:
                emp = getattr(obj, "employee_id", None)
                title = str(getattr(obj, "title", "") or "")
                req = getattr(obj, "document_request_id", None)
                req_title = str(getattr(req, "title", "") or "") if req else ""
                blob = f"{title} {req_title}".lower()
                is_visa_like = any(t in blob for t in visa_tokens)
                if is_visa_like:
                    visa_like += 1
                    kind = _("Document (visa-like title)")
                else:
                    other_docs += 1
                    kind = _("Document (other)")
                rows.append(
                    {
                        "kind": kind,
                        "title": title,
                        "employee": emp.get_full_name() if emp else "",
                        "expiry": str(obj.expiry_date),
                        "status": "",
                    }
                )
        except Exception:
            pass

    if not rows:
        return empty_report(
            _("Contracts & Document Expiry"),
            filters,
            _("No contracts or documents with expiry in the selected window."),
        )

    rows.sort(key=lambda r: r.get("expiry") or "")
    return {
        "title": _("Contracts & Document Expiry"),
        "kpis": [
            {
                "label": _("Contracts ending"),
                "value": contracts_ending,
                "hint": _("Payroll Contract rows in window"),
            },
            {
                "label": _("Visa-like documents"),
                "value": visa_like,
                "hint": _("Title/request contains visa/passport/permit"),
            },
            {
                "label": _("Other expiring documents"),
                "value": other_docs,
                "hint": _("Not classified as visa-like"),
            },
            {"label": _("Rows listed"), "value": len(rows), "hint": _("Capped")},
        ],
        "charts": [
            {
                "id": "expiry_mix",
                "type": "donut",
                "title": _("Expiry mix"),
                "categories": [
                    _("Contracts"),
                    _("Visa-like docs"),
                    _("Other docs"),
                ],
                "series": [
                    {
                        "name": _("Count"),
                        "data": [contracts_ending, visa_like, other_docs],
                    }
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "kind", "label": _("Kind")},
                {"key": "title", "label": _("Item")},
                {"key": "employee", "label": _("Employee")},
                {"key": "expiry", "label": _("Expiry")},
                {"key": "status", "label": _("Status")},
            ],
            "rows": rows[:150],
        },
    }
