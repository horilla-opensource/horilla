"""
Per-report filter schemas for standard reports.

Each ReportDefinition declares which filter keys apply. The UI and option
builder only expose those keys — so attendance reports don't show leave-type
or candidate-source filters, etc.
"""

from __future__ import annotations

from typing import Any, Optional

from django.apps import apps
from django.utils.translation import gettext as _

from report.registry import ReportDefinition

# Catalog of supported filter controls (id → metadata).
FILTER_CATALOG: dict[str, dict[str, Any]] = {
    "employment_status": {
        "label": _("Employment status"),
        "control": "select",
        "options_key": "employment_statuses",
        "primary": True,
        "empty_label": None,
        "default": "active",
    },
    "department_id": {
        "label": _("Department"),
        "control": "select",
        "options_key": "departments",
        "value_key": "id",
        "label_key": "department",
        "empty_label": _("All departments"),
    },
    "job_position_id": {
        "label": _("Job position"),
        "control": "select",
        "options_key": "job_positions",
        "value_key": "id",
        "label_key": "job_position",
        "empty_label": _("All positions"),
    },
    "job_role_id": {
        "label": _("Job role"),
        "control": "select",
        "options_key": "job_roles",
        "value_key": "id",
        "label_key": "job_role",
        "empty_label": _("All roles"),
    },
    "employee_type_id": {
        "label": _("Employee type"),
        "control": "select",
        "options_key": "employee_types",
        "value_key": "id",
        "label_key": "employee_type",
        "empty_label": _("All types"),
    },
    "work_type_id": {
        "label": _("Work type"),
        "control": "select",
        "options_key": "work_types",
        "value_key": "id",
        "label_key": "work_type",
        "empty_label": _("All work types"),
    },
    "shift_id": {
        "label": _("Shift"),
        "control": "select",
        "options_key": "shifts",
        "value_key": "id",
        "label_key": "employee_shift",
        "empty_label": _("All shifts"),
    },
    "company_id": {
        "label": _("Company"),
        "control": "select",
        "options_key": "companies",
        "value_key": "id",
        "label_key": "company",
        "empty_label": _("Session / all companies"),
    },
    "location": {
        "label": _("Location"),
        "control": "select",
        "options_key": "locations",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All locations"),
    },
    "gender": {
        "label": _("Gender"),
        "control": "select",
        "options_key": "genders",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All genders"),
    },
    "reporting_manager_id": {
        "label": _("Reporting manager"),
        "control": "select",
        "options_key": "managers",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All managers"),
    },
    "leave_type_id": {
        "label": _("Leave type"),
        "control": "select",
        "options_key": "leave_types",
        "value_key": "id",
        "label_key": "name",
        "empty_label": _("All leave types"),
    },
    "leave_status": {
        "label": _("Leave status"),
        "control": "select",
        "options_key": "leave_statuses",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All statuses"),
    },
    "recruitment_id": {
        "label": _("Recruitment"),
        "control": "select",
        "options_key": "recruitments",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All recruitments"),
    },
    "source": {
        "label": _("Source"),
        "control": "select",
        "options_key": "sources",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All sources"),
    },
    "offer_letter_status": {
        "label": _("Offer letter status"),
        "control": "select",
        "options_key": "offer_statuses",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All offer statuses"),
    },
    "payslip_status": {
        "label": _("Payslip status"),
        "control": "select",
        "options_key": "payslip_statuses",
        "value_key": "id",
        "label_key": "label",
        "empty_label": _("All statuses"),
    },
}


# Sensible defaults by domain / model family when a report omits filter_fields.
DOMAIN_DEFAULT_FILTERS: dict[str, tuple[str, ...]] = {
    "workforce": (
        "employment_status",
        "department_id",
        "job_position_id",
        "job_role_id",
        "employee_type_id",
        "work_type_id",
        "shift_id",
        "company_id",
        "location",
        "gender",
        "reporting_manager_id",
    ),
    "time_leave": (
        "employment_status",
        "department_id",
        "job_position_id",
        "work_type_id",
        "shift_id",
        "company_id",
        "gender",
        "leave_type_id",
        "leave_status",
    ),
    "payroll": (
        "employment_status",
        "department_id",
        "job_position_id",
        "employee_type_id",
        "company_id",
        "gender",
        "payslip_status",
    ),
    "talent": (
        "department_id",
        "job_position_id",
        "company_id",
        "gender",
        "recruitment_id",
        "source",
        "offer_letter_status",
    ),
    "compliance": (
        "department_id",
        "company_id",
        "employment_status",
    ),
}


def resolve_filter_fields(definition: ReportDefinition) -> tuple[str, ...]:
    fields = getattr(definition, "filter_fields", None) or ()
    if fields:
        return tuple(fields)
    return DOMAIN_DEFAULT_FILTERS.get(
        definition.domain, ("department_id", "company_id")
    )


def build_filter_schema(
    definition: ReportDefinition, options: Optional[dict] = None
) -> dict[str, Any]:
    """
    Return primary + advanced filter field descriptors for the template,
    with choices already attached (normalized to id/label).
    """
    options = options or {}
    keys = resolve_filter_fields(definition)
    primary = []
    advanced = []
    for key in keys:
        meta = FILTER_CATALOG.get(key)
        if not meta:
            continue
        raw = options.get(meta["options_key"], []) or []
        choices = _normalize_choices(
            raw,
            value_key=meta.get("value_key", "id"),
            label_key=meta.get("label_key", "label"),
        )
        item = {
            "id": key,
            "label": meta["label"],
            "control": meta.get("control", "select"),
            "empty_label": meta.get("empty_label"),
            "default": meta.get("default"),
            "choices": choices,
        }
        if meta.get("primary"):
            primary.append(item)
        else:
            advanced.append(item)
    return {"primary": primary, "advanced": advanced, "keys": list(keys)}


def _normalize_choices(raw: list, value_key: str, label_key: str) -> list[dict]:
    out = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        value = row.get(value_key, row.get("id"))
        label = row.get(label_key, row.get("label", value))
        if value is None:
            continue
        out.append({"id": value, "label": label})
    return out


def build_filter_options(definition: ReportDefinition) -> dict[str, list]:
    """Load dropdown option lists only for filters this report uses."""
    from django.core.cache import cache

    cache_key = f"report:filter_options:{definition.slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    keys = set(resolve_filter_fields(definition))
    needed = {FILTER_CATALOG[k]["options_key"] for k in keys if k in FILTER_CATALOG}
    options: dict[str, list] = {}

    # Always include period presets for the primary bar
    options["period_presets"] = [
        {"id": "all_time", "label": str(_("All time"))},
        {"id": "this_month", "label": str(_("This month"))},
        {"id": "last_month", "label": str(_("Last month"))},
        {"id": "last_30", "label": str(_("Last 30 days"))},
        {"id": "last_90", "label": str(_("Last 90 days"))},
        {"id": "quarter", "label": str(_("Quarter to date"))},
        {"id": "ytd", "label": str(_("Year to date"))},
        {"id": "last_year", "label": str(_("Last year"))},
        {"id": "custom", "label": str(_("Custom range"))},
    ]

    if "employment_statuses" in needed:
        options["employment_statuses"] = [
            {"id": "active", "label": str(_("Active"))},
            {"id": "inactive", "label": str(_("Inactive"))},
            {"id": "all", "label": str(_("All"))},
        ]

    if "genders" in needed:
        options["genders"] = [
            {"id": "male", "label": str(_("Male"))},
            {"id": "female", "label": str(_("Female"))},
            {"id": "other", "label": str(_("Other"))},
        ]

    if "departments" in needed:
        options["departments"] = _safe_values("base.Department", ("id", "department"))

    if "job_positions" in needed:
        options["job_positions"] = _safe_values(
            "base.JobPosition", ("id", "job_position")
        )

    if "job_roles" in needed:
        options["job_roles"] = _safe_values("base.JobRole", ("id", "job_role"))

    if "employee_types" in needed:
        options["employee_types"] = _safe_values(
            "base.EmployeeType", ("id", "employee_type")
        )

    if "work_types" in needed:
        options["work_types"] = _safe_values("base.WorkType", ("id", "work_type"))

    if "shifts" in needed:
        options["shifts"] = _safe_values("base.EmployeeShift", ("id", "employee_shift"))

    if "companies" in needed:
        options["companies"] = _safe_values("base.Company", ("id", "company"))

    if "locations" in needed and apps.is_installed("employee"):
        options["locations"] = _employee_locations()

    if "managers" in needed and apps.is_installed("employee"):
        options["managers"] = _managers()

    if "leave_types" in needed and apps.is_installed("leave"):
        options["leave_types"] = _safe_values("leave.LeaveType", ("id", "name"))

    if "leave_statuses" in needed:
        options["leave_statuses"] = [
            {"id": "requested", "label": str(_("Requested"))},
            {"id": "approved", "label": str(_("Approved"))},
            {"id": "rejected", "label": str(_("Rejected"))},
            {"id": "cancelled", "label": str(_("Cancelled"))},
        ]

    if "recruitments" in needed and apps.is_installed("recruitment"):
        options["recruitments"] = _recruitments()

    if "sources" in needed:
        options["sources"] = [
            {"id": "application", "label": str(_("Application"))},
            {"id": "software", "label": str(_("Software"))},
            {"id": "referral", "label": str(_("Referral"))},
            {"id": "other", "label": str(_("Other"))},
        ]

    if "offer_statuses" in needed:
        options["offer_statuses"] = [
            {"id": "not_sent", "label": str(_("Not sent"))},
            {"id": "sent", "label": str(_("Sent"))},
            {"id": "accepted", "label": str(_("Accepted"))},
            {"id": "rejected", "label": str(_("Rejected"))},
            {"id": "joined", "label": str(_("Joined"))},
        ]

    if "payslip_statuses" in needed:
        options["payslip_statuses"] = [
            {"id": "draft", "label": str(_("Draft"))},
            {"id": "review_ongoing", "label": str(_("Review ongoing"))},
            {"id": "confirmed", "label": str(_("Confirmed"))},
            {"id": "paid", "label": str(_("Paid"))},
        ]

    cache.set(cache_key, options, 60)
    return options


def _safe_values(model_path: str, fields: tuple[str, ...], limit: int = 300) -> list:
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
        return list(model.objects.all().values(*fields)[:limit])
    except Exception:
        return []


def _employee_locations() -> list:
    try:
        from employee.models import EmployeeWorkInformation

        return [
            {"id": loc, "label": loc}
            for loc in (
                EmployeeWorkInformation.objects.exclude(location__isnull=True)
                .exclude(location="")
                .values_list("location", flat=True)
                .distinct()
                .order_by("location")[:100]
            )
        ]
    except Exception:
        return []


def _managers() -> list:
    try:
        from employee.models import Employee, EmployeeWorkInformation

        managers = Employee.objects.filter(
            is_active=True,
            id__in=EmployeeWorkInformation.objects.exclude(
                reporting_manager_id__isnull=True
            ).values_list("reporting_manager_id", flat=True),
        ).order_by("employee_first_name")[:200]
        return [
            {
                "id": m.id,
                "label": m.get_full_name() if hasattr(m, "get_full_name") else str(m),
            }
            for m in managers
        ]
    except Exception:
        return []


def _recruitments() -> list:
    try:
        from recruitment.models import Recruitment

        return [
            {"id": r.id, "label": r.title or str(r)}
            for r in Recruitment.objects.all().order_by("-id")[:100]
        ]
    except Exception:
        return []
