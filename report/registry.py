"""
Standard report registry — metadata-driven catalog of named reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from django.apps import apps
from django.utils.translation import gettext_lazy as _

from report.engine import ReportFilters

QueryFn = Callable[[ReportFilters], dict]
# filters, params dict (dimension/value/…), optional request for subordinate scope
DrilldownFn = Callable[..., dict]


@dataclass
class ReportDefinition:
    slug: str
    name: str
    domain: str
    description: str
    permission: str
    query_fn: QueryFn
    # Additional permissions that also grant this report, any-of. Lets a
    # report be granted on its own subject-matter permission without
    # revoking access from roles that only hold the primary one -- swapping
    # `permission` outright would silently drop existing users on upgrade.
    alt_permissions: tuple[str, ...] = field(default_factory=tuple)
    explorer_url_name: Optional[str] = None
    export_model: Optional[str] = None
    required_apps: tuple[str, ...] = field(default_factory=tuple)
    chart_hint: str = ""
    # Filter keys from report.filter_schema.FILTER_CATALOG that apply to this report.
    # Empty → fall back to DOMAIN_DEFAULT_FILTERS for the report domain.
    filter_fields: tuple[str, ...] = field(default_factory=tuple)
    drilldown_fn: Optional[DrilldownFn] = None

    def is_available(self) -> bool:
        return all(apps.is_installed(app) for app in self.required_apps)

    def user_has_permission(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.has_perm(self.permission):
            return True
        return any(user.has_perm(perm) for perm in self.alt_permissions)


_REGISTRY: dict[str, ReportDefinition] = {}

DOMAIN_LABELS = {
    "workforce": _("Workforce"),
    "time_leave": _("Time & Leave"),
    "payroll": _("Payroll"),
    "talent": _("Talent"),
    "compliance": _("Compliance"),
}


def register(definition: ReportDefinition) -> ReportDefinition:
    """Register a standard report definition."""
    _REGISTRY[definition.slug] = definition
    return definition


# Retired slugs, mapped to the report that absorbed them. Kept so existing
# bookmarks, saved views and subscriptions keep resolving instead of 404ing
# the moment a report is consolidated away.
RETIRED_SLUGS = {
    # Absorbed into overtime-analysis as a concentration view: same base
    # queryset and chart, only the share KPIs and column differed.
    "ot-concentration": "overtime-analysis",
    # Absorbed into document-expiry-aging, the strictly stronger of the pair
    # -- it buckets by age and can show overdue items, which document-expiry
    # structurally could not (its floor was expiry_date >= from_date).
    "document-expiry": "document-expiry-aging",
}


def resolve_slug(slug: str) -> str:
    "Map a retired slug onto its surviving report."
    return RETIRED_SLUGS.get(slug, slug)


def get_report(slug: str) -> Optional[ReportDefinition]:
    definition = _REGISTRY.get(resolve_slug(slug))
    if definition and definition.is_available():
        return definition
    return None


def list_reports(
    domain: Optional[str] = None, user=None, company_id: Optional[int] = None
) -> list[ReportDefinition]:
    """Return available reports, optionally filtered by domain and user permission."""
    from report.access import user_can_view_report

    items = []
    for definition in _REGISTRY.values():
        if not definition.is_available():
            continue
        if domain and definition.domain != domain:
            continue
        if user is not None and not user_can_view_report(
            user, definition, company_id=company_id
        ):
            continue
        items.append(definition)
    # Stable domain order then name
    domain_order = list(DOMAIN_LABELS.keys())
    items.sort(
        key=lambda d: (
            domain_order.index(d.domain) if d.domain in domain_order else 99,
            str(d.name),
        )
    )
    return items


def reports_by_domain(
    user=None, company_id: Optional[int] = None
) -> dict[str, list[ReportDefinition]]:
    grouped: dict[str, list[ReportDefinition]] = {}
    for definition in list_reports(user=user, company_id=company_id):
        grouped.setdefault(definition.domain, []).append(definition)
    return grouped


def run_report(slug: str, filters: ReportFilters) -> dict:
    """Execute a registered report and attach catalog metadata."""
    from report.compare import (
        COMPARE_NONE,
        apply_compare,
        filters_for_compare,
        normalize_compare_preset,
    )

    definition = get_report(slug)
    if not definition:
        raise KeyError(f"Unknown or unavailable report: {slug}")
    payload = definition.query_fn(filters)
    payload.setdefault("title", str(definition.name))
    payload.setdefault("slug", definition.slug)
    payload.setdefault("domain", definition.domain)
    payload.setdefault(
        "period",
        {
            "from_date": filters.from_date.isoformat(),
            "to_date": filters.to_date.isoformat(),
            "preset": filters.period_preset,
            "label": filters.period_label,
        },
    )
    payload.setdefault("filters", filters.summary_labels())
    payload.setdefault(
        "applied_filters",
        {
            "from_date": filters.from_date.isoformat(),
            "to_date": filters.to_date.isoformat(),
            "period_preset": filters.period_preset,
            "compare_preset": filters.compare_preset,
            "department_id": filters.department_id,
            "job_position_id": filters.job_position_id,
            "employee_type_id": filters.employee_type_id,
            "work_type_id": filters.work_type_id,
            "company_id": filters.company_id,
            "reporting_manager_id": filters.reporting_manager_id,
            "location": filters.location,
            "gender": filters.gender,
            "employment_status": filters.employment_status,
            "leave_type_id": filters.leave_type_id,
            "leave_status": filters.leave_status,
            "recruitment_id": filters.recruitment_id,
            "job_role_id": filters.job_role_id,
            "shift_id": filters.shift_id,
            "source": filters.source,
            "offer_letter_status": filters.offer_letter_status,
            "payslip_status": filters.payslip_status,
        },
    )
    if definition.explorer_url_name:
        payload.setdefault("explorer_url_name", definition.explorer_url_name)

    compare_preset = normalize_compare_preset(filters.compare_preset)
    if compare_preset != COMPARE_NONE:
        prior_filters = filters_for_compare(filters, compare_preset)
        if prior_filters is not None:
            prior_payload = definition.query_fn(prior_filters)
            payload = apply_compare(
                payload, prior_payload, compare_preset, prior_filters
            )
    if definition.drilldown_fn:
        payload.setdefault("drilldown", True)
    return payload


def run_report_kpis(slug: str, filters: ReportFilters) -> dict:
    """KPI-only payload for dashboard pins (Phase 9)."""
    payload = run_report(slug, filters)
    return {
        "slug": slug,
        "title": payload.get("title"),
        "domain": payload.get("domain"),
        "kpis": payload.get("kpis") or [],
        "period": payload.get("period"),
        "filters": payload.get("filters") or [],
    }


def run_drilldown(
    slug: str, filters: ReportFilters, params: dict, request=None
) -> dict:
    definition = get_report(slug)
    if not definition:
        raise KeyError(f"Unknown or unavailable report: {slug}")
    if not definition.drilldown_fn:
        raise ValueError(f"Report {slug} does not support drill-down")
    return definition.drilldown_fn(filters, params, request)
