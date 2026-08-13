"""Time, attendance, and leave metrics."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils.translation import gettext as _

from report.engine import ReportFilters, apply_org_filters, iter_months


def attendance_summary(filters: ReportFilters) -> dict:
    from attendance.models import Attendance, AttendanceLateComeEarlyOut
    from employee.models import Employee

    active = apply_org_filters(
        Employee.objects.all(), filters, prefix="employee_work_info", employee_prefix=""
    )
    headcount = active.count()

    att_qs = Attendance.objects.filter(
        attendance_date__gte=filters.from_date,
        attendance_date__lte=filters.to_date,
    )
    att_qs = apply_org_filters(
        att_qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )

    present_days = att_qs.values("employee_id", "attendance_date").distinct().count()
    unique_present = att_qs.values("employee_id").distinct().count()

    late = AttendanceLateComeEarlyOut.objects.filter(
        type="late_come",
        attendance_id__attendance_date__gte=filters.from_date,
        attendance_id__attendance_date__lte=filters.to_date,
    )
    late = apply_org_filters(
        late,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )
    late_count = late.count()

    early = AttendanceLateComeEarlyOut.objects.filter(
        type="early_out",
        attendance_id__attendance_date__gte=filters.from_date,
        attendance_id__attendance_date__lte=filters.to_date,
    )
    early = apply_org_filters(
        early,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )

    ot_seconds = att_qs.aggregate(total=Sum("overtime_second"))["total"] or 0
    worked_seconds = att_qs.aggregate(total=Sum("at_work_second"))["total"] or 0
    ot_hours = round(ot_seconds / 3600, 1)
    avg_hours = round(worked_seconds / 3600 / present_days, 2) if present_days else 0

    by_dept = list(
        att_qs.filter(employee_id__employee_work_info__department_id__isnull=False)
        .values("employee_id__employee_work_info__department_id__department")
        .annotate(
            records=Count("id"),
            employees=Count("employee_id", distinct=True),
            ot=Sum("overtime_second"),
        )
        .order_by("-records")[:15]
    )

    return {
        "title": _("Attendance Summary"),
        "kpis": [
            {"label": _("Active headcount"), "value": headcount, "hint": ""},
            {
                "label": _("Present employee-days"),
                "value": present_days,
                "hint": _("Unique employee × day"),
            },
            {"label": _("Late comes"), "value": late_count, "hint": _("In period")},
            {
                "label": _("OT hours"),
                "value": ot_hours,
                "hint": _("Sum of overtime"),
            },
        ],
        "charts": [
            {
                "id": "dept_attendance",
                "type": "bar",
                "title": _("Attendance Records by Department"),
                "categories": [
                    r["employee_id__employee_work_info__department_id__department"]
                    for r in by_dept
                ],
                "series": [
                    {"name": _("Records"), "data": [r["records"] for r in by_dept]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "department", "label": _("Department")},
                {"key": "employees", "label": _("Employees")},
                {"key": "records", "label": _("Records")},
                {"key": "ot_hours", "label": _("OT Hours")},
            ],
            "rows": [
                {
                    "department": r[
                        "employee_id__employee_work_info__department_id__department"
                    ],
                    "employees": r["employees"],
                    "records": r["records"],
                    "ot_hours": round((r["ot"] or 0) / 3600, 1),
                }
                for r in by_dept
            ],
        },
        "meta": {
            "unique_present": unique_present,
            "early_out": early.count(),
            "avg_hours_per_present_day": avg_hours,
        },
        "explorer_url_name": "attendance-report",
    }


def absenteeism_rate(filters: ReportFilters) -> dict:
    from attendance.models import Attendance
    from employee.models import Employee

    total_employees = apply_org_filters(
        Employee.objects.all(), filters, prefix="employee_work_info", employee_prefix=""
    ).count()

    months = []
    for month_start, month_end, label in iter_months(filters.to_date, 6):
        end = min(month_end, filters.to_date)
        working_days = 0
        d = month_start
        while d <= end:
            if d.weekday() < 5:
                working_days += 1
            d += timedelta(days=1)

        if working_days == 0 or total_employees == 0:
            months.append(
                {
                    "month": label,
                    "rate": 0,
                    "absent_days": 0,
                    "expected_days": 0,
                }
            )
            continue

        present_qs = Attendance.objects.filter(
            attendance_date__gte=month_start,
            attendance_date__lte=end,
        )
        present_qs = apply_org_filters(
            present_qs,
            filters,
            prefix="employee_id__employee_work_info",
            employee_prefix="employee_id",
        )
        present_days = (
            present_qs.values("employee_id", "attendance_date").distinct().count()
        )
        expected = total_employees * working_days
        absent = max(0, expected - present_days)
        months.append(
            {
                "month": label,
                "rate": round(absent / expected * 100, 1),
                "absent_days": absent,
                "expected_days": expected,
            }
        )

    latest = months[-1]["rate"] if months else 0
    avg_rate = round(sum(m["rate"] for m in months) / len(months), 1) if months else 0

    return {
        "title": _("Absenteeism Rate"),
        "kpis": [
            {
                "label": _("Latest month rate"),
                "value": f"{latest}%",
                "hint": _("Absent / expected working days"),
            },
            {
                "label": _("6-month avg"),
                "value": f"{avg_rate}%",
                "hint": _("Average absenteeism"),
            },
            {
                "label": _("Active headcount"),
                "value": total_employees,
                "hint": _("Denominator base"),
            },
            {
                "label": _("Absent days (latest)"),
                "value": months[-1]["absent_days"] if months else 0,
                "hint": _("Estimated"),
            },
        ],
        "charts": [
            {
                "id": "absenteeism",
                "type": "line",
                "title": _("Absenteeism Trend"),
                "categories": [m["month"] for m in months],
                "series": [{"name": _("Rate %"), "data": [m["rate"] for m in months]}],
            }
        ],
        "table": {
            "columns": [
                {"key": "month", "label": _("Month")},
                {"key": "rate", "label": _("Rate %")},
                {"key": "absent_days", "label": _("Absent Days")},
                {"key": "expected_days", "label": _("Expected Days")},
            ],
            "rows": months,
        },
        "explorer_url_name": "attendance-report",
    }


def overtime_analysis(filters: ReportFilters) -> dict:
    from attendance.models import Attendance

    att_qs = Attendance.objects.filter(
        attendance_date__gte=filters.from_date,
        attendance_date__lte=filters.to_date,
        overtime_second__gt=0,
    )
    att_qs = apply_org_filters(
        att_qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )

    total_ot = att_qs.aggregate(total=Sum("overtime_second"))["total"] or 0
    approved = (
        att_qs.filter(attendance_overtime_approve=True).aggregate(
            total=Sum("approved_overtime_second")
        )["total"]
        or 0
    )

    by_dept = list(
        att_qs.filter(employee_id__employee_work_info__department_id__isnull=False)
        .values("employee_id__employee_work_info__department_id__department")
        .annotate(
            total_seconds=Sum("overtime_second"),
            approved_seconds=Sum("approved_overtime_second"),
            employees=Count("employee_id", distinct=True),
        )
        .order_by("-total_seconds")[:20]
    )

    by_emp = list(
        att_qs.values(
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__employee_work_info__department_id__department",
        )
        .annotate(total_seconds=Sum("overtime_second"))
        .order_by("-total_seconds")[:25]
    )

    return {
        "title": _("Overtime Analysis"),
        "kpis": [
            {
                "label": _("Total OT hours"),
                "value": round(total_ot / 3600, 1),
                "hint": _("In period"),
            },
            {
                "label": _("Approved OT hours"),
                "value": round(approved / 3600, 1),
                "hint": _("Approved overtime"),
            },
            {
                "label": _("Employees with OT"),
                "value": att_qs.values("employee_id").distinct().count(),
                "hint": "",
            },
            {
                "label": _("Departments"),
                "value": len(by_dept),
                "hint": _("With OT"),
            },
        ],
        "charts": [
            {
                "id": "ot_dept",
                "type": "bar",
                "title": _("OT Hours by Department"),
                "categories": [
                    r["employee_id__employee_work_info__department_id__department"]
                    for r in by_dept[:12]
                ],
                "series": [
                    {
                        "name": _("OT Hours"),
                        "data": [
                            round((r["total_seconds"] or 0) / 3600, 1)
                            for r in by_dept[:12]
                        ],
                    }
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "employee", "label": _("Employee")},
                {"key": "department", "label": _("Department")},
                {"key": "ot_hours", "label": _("OT Hours")},
            ],
            "rows": [
                {
                    "employee": f"{r['employee_id__employee_first_name']} {r['employee_id__employee_last_name'] or ''}".strip(),
                    "department": r[
                        "employee_id__employee_work_info__department_id__department"
                    ]
                    or "",
                    "ot_hours": round((r["total_seconds"] or 0) / 3600, 1),
                }
                for r in by_emp
            ],
        },
        "explorer_url_name": "attendance-report",
    }


def leave_utilization(filters: ReportFilters) -> dict:
    from leave.models import AvailableLeave, LeaveRequest

    allocations = AvailableLeave.objects.filter(employee_id__is_active=True)
    allocations = apply_org_filters(
        allocations,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )
    if filters.leave_type_id:
        allocations = allocations.filter(leave_type_id=filters.leave_type_id)
    allocation_rows = list(
        allocations.values("leave_type_id", "leave_type_id__name")
        .annotate(
            total_available=Sum("available_days"),
            total_carryforward=Sum("carryforward_days"),
            total_allocated=Sum("total_leave_days"),
        )
        .order_by("-total_allocated")
    )

    leave_qs = LeaveRequest.objects.filter(
        status="approved",
        start_date__lte=filters.to_date,
        end_date__gte=filters.from_date,
    )
    leave_qs = apply_org_filters(
        leave_qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )
    if filters.leave_type_id:
        leave_qs = leave_qs.filter(leave_type_id=filters.leave_type_id)
    if filters.leave_status:
        leave_qs = leave_qs.filter(status=filters.leave_status)
    used_by_type = {
        row["leave_type_id"]: float(row["total"] or 0)
        for row in leave_qs.values("leave_type_id").annotate(
            total=Sum("requested_days")
        )
    }

    utilization = []
    for item in allocation_rows:
        lt_id = item["leave_type_id"]
        allocated = float(item["total_allocated"] or 0)
        available = float(item["total_available"] or 0) + float(
            item["total_carryforward"] or 0
        )
        used = used_by_type.get(lt_id, 0.0)
        rate = round((used / allocated * 100), 1) if allocated > 0 else 0
        utilization.append(
            {
                "type": item["leave_type_id__name"] or _("Unknown"),
                "allocated": round(allocated, 1),
                "used": round(used, 1),
                "remaining": round(available, 1),
                "rate": rate,
            }
        )

    total_used = sum(u["used"] for u in utilization)
    total_alloc = sum(u["allocated"] for u in utilization)
    overall = round(total_used / total_alloc * 100, 1) if total_alloc else 0

    return {
        "title": _("Leave Utilization"),
        "kpis": [
            {
                "label": _("Overall utilization"),
                "value": f"{overall}%",
                "hint": _("Used / allocated"),
            },
            {
                "label": _("Days used"),
                "value": round(total_used, 1),
                "hint": _("Period"),
            },
            {
                "label": _("Days allocated"),
                "value": round(total_alloc, 1),
                "hint": _("Current balances"),
            },
            {"label": _("Leave types"), "value": len(utilization), "hint": ""},
        ],
        "charts": [
            {
                "id": "leave_util",
                "type": "bar",
                "title": _("Utilization by Leave Type"),
                "categories": [u["type"] for u in utilization],
                "series": [
                    {"name": _("Used"), "data": [u["used"] for u in utilization]},
                    {
                        "name": _("Allocated"),
                        "data": [u["allocated"] for u in utilization],
                    },
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "type", "label": _("Leave Type")},
                {"key": "allocated", "label": _("Allocated")},
                {"key": "used", "label": _("Used")},
                {"key": "remaining", "label": _("Remaining")},
                {"key": "rate", "label": _("Rate %")},
            ],
            "rows": utilization,
        },
        "explorer_url_name": "leave-report",
    }


def leave_liability(filters: ReportFilters) -> dict:
    from leave.models import AvailableLeave

    qs = AvailableLeave.objects.filter(employee_id__is_active=True)
    qs = apply_org_filters(
        qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )
    if filters.leave_type_id:
        qs = qs.filter(leave_type_id=filters.leave_type_id)

    by_type = []
    aggregated = (
        qs.values("leave_type_id", "leave_type_id__name")
        .annotate(
            avail=Sum("available_days"),
            carry=Sum("carryforward_days"),
            employees=Count("employee_id", distinct=True),
        )
        .order_by("-avail")
    )
    for row in aggregated:
        remaining = float(row["avail"] or 0) + float(row["carry"] or 0)
        by_type.append(
            {
                "type": row["leave_type_id__name"] or _("Unknown"),
                "remaining": round(remaining, 1),
                "employees": row["employees"],
            }
        )
    by_type.sort(key=lambda x: -x["remaining"])

    by_dept = list(
        qs.filter(employee_id__employee_work_info__department_id__isnull=False)
        .values("employee_id__employee_work_info__department_id__department")
        .annotate(
            avail=Sum("available_days"),
            carry=Sum("carryforward_days"),
        )
        .order_by("-avail")
    )
    dept_rows = [
        {
            "department": r[
                "employee_id__employee_work_info__department_id__department"
            ],
            "remaining": round(float(r["avail"] or 0) + float(r["carry"] or 0), 1),
        }
        for r in by_dept
    ]

    total_liability = sum(r["remaining"] for r in by_type)

    return {
        "title": _("Leave Liability"),
        "kpis": [
            {
                "label": _("Open balance (days)"),
                "value": round(total_liability, 1),
                "hint": _("Available + carry forward"),
            },
            {"label": _("Leave types"), "value": len(by_type), "hint": ""},
            {
                "label": _("Departments"),
                "value": len(dept_rows),
                "hint": _("With balances"),
            },
            {
                "label": _("Employees with leave"),
                "value": qs.values("employee_id").distinct().count(),
                "hint": "",
            },
        ],
        "charts": [
            {
                "id": "liability_type",
                "type": "donut",
                "title": _("Liability by Leave Type"),
                "categories": [r["type"] for r in by_type],
                "series": [
                    {"name": _("Days"), "data": [r["remaining"] for r in by_type]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "type", "label": _("Leave Type")},
                {"key": "remaining", "label": _("Open Days")},
                {"key": "employees", "label": _("Employees")},
            ],
            "rows": by_type
            + [
                {
                    "type": _("Dept: %(d)s") % {"d": r["department"]},
                    "remaining": r["remaining"],
                    "employees": "",
                }
                for r in dept_rows
            ],
        },
        "explorer_url_name": "leave-report",
    }
