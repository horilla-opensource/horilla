"""Privacy / culture gates for named employee outputs in reports."""

from __future__ import annotations

from report.engine import ReportFilters


def allow_named_ot_rows(filters: ReportFilters) -> bool:
    """
    Named OT employee rows require ``?include_names=1`` and a stricter perm.

    Viewers with only ``attendance.view_attendance`` see department aggregates.
    """
    request = getattr(filters, "request", None)
    if request is None:
        return False
    flag = (request.GET.get("include_names") or "").lower()
    if flag not in ("1", "true", "yes"):
        return False
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    return bool(user.is_superuser or user.has_perm("attendance.change_attendance"))
