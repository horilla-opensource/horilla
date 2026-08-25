"""Shared exit-date resolution for workforce turnover metrics."""

from __future__ import annotations

from datetime import date
from typing import Iterator

from django.apps import apps
from django.db.models import Q

from report.engine import ReportFilters, apply_org_filters


def iter_exits(
    filters: ReportFilters,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict]:
    """
    Return exits in the date window as ``{employee_id, exit_date, source}``.

    Priority when multiple sources exist for one employee: archived offboarding
    ``notice_period_ends`` → approved resignation ``planned_to_leave_on`` →
    inactive employee with ``contract_end_date`` (fallback).
    """
    start = from_date or filters.from_date
    end = to_date or filters.to_date
    by_emp: dict[int, dict] = {}

    for row in _offboarding_archived_exits(filters, start, end):
        by_emp[row["employee_id"]] = row

    for row in _resignation_exits(filters, start, end):
        by_emp.setdefault(row["employee_id"], row)

    for row in _inactive_contract_exits(filters, start, end):
        by_emp.setdefault(row["employee_id"], row)

    return sorted(by_emp.values(), key=lambda r: (r["exit_date"], r["employee_id"]))


def exits_in_period(
    filters: ReportFilters,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> int:
    return len(iter_exits(filters, from_date=from_date, to_date=to_date))


def _offboarding_archived_exits(
    filters: ReportFilters, start: date, end: date
) -> Iterator[dict]:
    if not apps.is_installed("offboarding"):
        return
    try:
        OffboardingEmployee = apps.get_model("offboarding", "OffboardingEmployee")
    except LookupError:
        return

    qs = OffboardingEmployee.objects.filter(
        stage_id__type="archived",
        notice_period_ends__gte=start,
        notice_period_ends__lte=end,
        notice_period_ends__isnull=False,
    ).select_related("employee_id", "employee_id__employee_work_info")
    qs = apply_org_filters(
        qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
        apply_employment_status=False,
    )
    for row in qs.iterator():
        emp = row.employee_id
        if not emp or not row.notice_period_ends:
            continue
        yield {
            "employee_id": emp.id,
            "exit_date": row.notice_period_ends,
            "source": "offboarding_archived",
            "employee": emp,
        }


def _resignation_exits(
    filters: ReportFilters, start: date, end: date
) -> Iterator[dict]:
    if not apps.is_installed("offboarding"):
        return
    try:
        ResignationLetter = apps.get_model("offboarding", "ResignationLetter")
    except LookupError:
        return

    qs = ResignationLetter.objects.filter(
        status="approved",
        planned_to_leave_on__gte=start,
        planned_to_leave_on__lte=end,
        planned_to_leave_on__isnull=False,
    ).select_related("employee_id", "employee_id__employee_work_info")
    qs = apply_org_filters(
        qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
        apply_employment_status=False,
    )
    for row in qs.iterator():
        emp = row.employee_id
        if not emp or not row.planned_to_leave_on:
            continue
        yield {
            "employee_id": emp.id,
            "exit_date": row.planned_to_leave_on,
            "source": "resignation_approved",
            "employee": emp,
        }


def _inactive_contract_exits(
    filters: ReportFilters, start: date, end: date
) -> Iterator[dict]:
    from employee.models import Employee

    qs = (
        Employee.objects.filter(is_active=False)
        .filter(
            Q(employee_work_info__contract_end_date__gte=start)
            & Q(employee_work_info__contract_end_date__lte=end)
        )
        .select_related("employee_work_info")
    )
    qs = apply_org_filters(
        qs,
        filters,
        prefix="employee_work_info",
        employee_prefix="",
        apply_employment_status=False,
    )
    for emp in qs.iterator():
        wi = getattr(emp, "employee_work_info", None)
        exit_date = getattr(wi, "contract_end_date", None) if wi else None
        if not exit_date:
            continue
        yield {
            "employee_id": emp.id,
            "exit_date": exit_date,
            "source": "inactive_contract_end",
            "employee": emp,
        }
