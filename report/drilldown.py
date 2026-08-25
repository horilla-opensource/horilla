"""
Drill-down helpers for standard reports (Phase 4b).

Returns tabular row payloads with optional record links. Applies
filtersubordinates when the user lacks the report's global permission.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext as _


def safe_reverse(name: str, *args, **kwargs) -> str:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return ""


def employee_link(employee_id: Optional[int]) -> str:
    if not employee_id:
        return ""
    return safe_reverse("employee-view-individual", employee_id)


def candidate_link(candidate_id: Optional[int]) -> str:
    if not candidate_id:
        return ""
    url = safe_reverse("candidate-view-individual", candidate_id)
    if url:
        return url
    try:
        return reverse("candidate-view-individual", kwargs={"cand_id": candidate_id})
    except NoReverseMatch:
        return safe_reverse("candidate-detail", pk=candidate_id)


def payslip_link(payslip_id: Optional[int]) -> str:
    if not payslip_id:
        return ""
    return safe_reverse("payslip-pdf", payslip_id)


def apply_subordinate_scope(request, qs, *, perm: str, field: str = "id"):
    """
    If the user lacks `perm`, restrict queryset to subordinates (+ self).
    `field` is the Employee FK path relative to the queryset model
    (use \"id\" for Employee queryset, \"employee_id\" for related models).
    """
    if request is None or not getattr(request, "user", None):
        return qs
    user = request.user
    if user.is_superuser or (perm and user.has_perm(perm)):
        return qs
    from base.methods import filtersubordinates, filtersubordinatesemployeemodel

    if field in ("", "id", None):
        return filtersubordinatesemployeemodel(request, qs, perm=perm)
    return filtersubordinates(request, qs, perm=perm, field=field)


def drilldown_payload(
    *,
    title: str,
    dimension: str,
    value: str,
    columns: list[dict],
    rows: list[dict],
    truncated: bool = False,
) -> dict[str, Any]:
    return {
        "title": title,
        "dimension": dimension,
        "value": value,
        "columns": columns,
        "rows": rows,
        "count": len(rows),
        "truncated": truncated,
        "message": (
            _("Showing first %(n)s rows.") % {"n": len(rows)} if truncated else ""
        ),
    }


def empty_drilldown(title: str, dimension: str, value: str, message: str = "") -> dict:
    return drilldown_payload(
        title=title,
        dimension=dimension,
        value=value,
        columns=[],
        rows=[],
        truncated=False,
    ) | {"message": message or _("No matching records.")}


def build_drilldown_url(slug: str, params: dict) -> str:
    base = safe_reverse("standard-report-drilldown", slug)
    if not base:
        return ""
    qs = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return f"{base}?{qs}" if qs else base
