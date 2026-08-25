"""
Helpers for Phase 2 personalization — favorites, presets, recent runs.
"""

from __future__ import annotations

from typing import Optional

from django.urls import reverse

from report.models import (
    ReportFavorite,
    ReportFilterPreset,
    ReportRunLog,
    ReportSavedView,
)
from report.registry import get_report

# Opt-in Suggested Reports pack for dashboard Phase 4 handshake.
# Do NOT auto-favorite these — UI must require explicit user opt-in.
# Excluded until further hardening: absenteeism-rate, leave-utilization,
# payslip-register, diversity-snapshot (DEI pack), named-OT variants.
SUGGESTED_REPORT_SLUGS: tuple[str, ...] = (
    "workforce-composition",
    "tenure-longevity",
    "span-of-control",
    "turnover-attrition",
    "joiners-leavers",
    "headcount-bridge",
    "exit-analysis",
    "attendance-summary",
    "unscheduled-absence",
    "leave-liability",  # catalog: Open Leave Balance (Days)
    "ot-concentration",  # department / KPI defaults; names gated
    "recruitment-funnel",
    "time-to-hire",
    "offer-acceptance",
    "pipeline-aging",
    "quality-of-hire",
    "document-expiry",
    "document-expiry-aging",
)

# Priority order for the home "Pin recommended" action (subset of Suggested).
# Cap still 6 favorites total — this only fills empty pin slots on click.
DASHBOARD_PIN_PRIORITY_SLUGS: tuple[str, ...] = (
    "turnover-attrition",
    "time-to-hire",
    "document-expiry",
    "span-of-control",
    "ot-concentration",
    "leave-liability",
)

MAX_DASHBOARD_REPORT_PINS = 6


def session_company_id(request) -> Optional[int]:
    selected = request.session.get("selected_company") if request else None
    if not selected or selected == "all":
        return None
    try:
        return int(selected)
    except (TypeError, ValueError):
        return None


def filters_dict_from_request(request) -> dict:
    """Capture query params used by standard reports (for presets / run logs)."""
    keys = (
        "period_preset",
        "compare_preset",
        "from_date",
        "to_date",
        "employment_status",
        "department_id",
        "job_position_id",
        "work_type_id",
        "shift_id",
        "company_id",
        "gender",
        "employee_type_id",
        "reporting_manager_id",
        "leave_type_id",
        "recruitment_id",
        "source",
        "candidate_status",
        "job_position",
        "stage_id",
        "payroll_status",
        "batch",
        "contract_status",
        "format",
    )
    out = {}
    for key in keys:
        val = request.GET.get(key)
        if val not in (None, ""):
            out[key] = val
    # Also persist any other simple filter_* / id fields from GET
    for key, val in request.GET.items():
        if key in out or key in ("csrfmiddlewaretoken",):
            continue
        if val in (None, ""):
            continue
        if key.endswith("_id") or key in (
            "period_preset",
            "from_date",
            "to_date",
            "gender",
            "source",
            "employment_status",
        ):
            out[key] = val
    return out


def log_report_run(request, slug: str, action: str, filters: Optional[dict] = None):
    """Best-effort write; never raise into the report response path."""
    try:
        ReportRunLog.objects.create(
            report_slug=slug,
            action=action,
            filters=filters or filters_dict_from_request(request),
            user=request.user if request.user.is_authenticated else None,
            company_id_id=session_company_id(request),
        )
    except Exception:
        pass


def favorite_slugs_for_user(request) -> set[str]:
    company_id = session_company_id(request)
    qs = ReportFavorite.objects.filter(user=request.user, is_active=True)
    if company_id is not None:
        qs = qs.filter(company_id_id=company_id)
    else:
        qs = qs.filter(company_id__isnull=True)
    return set(qs.values_list("report_slug", flat=True))


def is_favorited(request, slug: str) -> bool:
    company_id = session_company_id(request)
    qs = ReportFavorite.objects.filter(
        user=request.user, report_slug=slug, is_active=True
    )
    if company_id is not None:
        qs = qs.filter(company_id_id=company_id)
    else:
        qs = qs.filter(company_id__isnull=True)
    return qs.exists()


def catalog_cards_for_slugs(
    slugs: list[str], user, company_id: Optional[int] = None
) -> list[dict]:
    """Build catalog card dicts preserving slug order; skip unavailable/denied."""
    from report.access import user_can_view_report

    cards = []
    seen = set()
    for slug in slugs:
        if slug in seen:
            continue
        seen.add(slug)
        definition = get_report(slug)
        if not definition or not user_can_view_report(
            user, definition, company_id=company_id
        ):
            continue
        cards.append(
            {
                "slug": definition.slug,
                "name": str(definition.name),
                "description": str(definition.description),
                "url": reverse("standard-report-detail", args=[definition.slug]),
                "domain": definition.domain,
            }
        )
    return cards


def recent_run_slugs(request, limit: int = 8) -> list[str]:
    qs = (
        ReportRunLog.objects.filter(user=request.user, is_active=True)
        .order_by("-created_at")
        .values_list("report_slug", flat=True)
    )
    ordered: list[str] = []
    for slug in qs[: limit * 4]:
        if slug not in ordered:
            ordered.append(slug)
        if len(ordered) >= limit:
            break
    return ordered


def saved_views_for_user(request) -> list[ReportSavedView]:
    company_id = session_company_id(request)
    qs = ReportSavedView.objects.filter(owner=request.user, is_active=True)
    if company_id is not None:
        qs = qs.filter(company_id_id=company_id)
    else:
        qs = qs.filter(company_id__isnull=True)
    return list(qs.order_by("name"))


def presets_for_report(request, slug: str) -> list[dict]:
    company_id = session_company_id(request)
    qs = ReportFilterPreset.objects.filter(
        user=request.user, report_slug=slug, is_active=True
    )
    if company_id is not None:
        qs = qs.filter(company_id_id=company_id)
    else:
        qs = qs.filter(company_id__isnull=True)
    return [
        {"id": p.id, "name": p.name, "filters": p.filters or {}}
        for p in qs.order_by("name")
    ]
