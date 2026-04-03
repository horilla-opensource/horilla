"""
Modern attendance dashboard views — KPI summary + ApexCharts.

Accessible at /attendance/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render


def _parse_period(request):
    """Parse from_date and to_date from GET params. Defaults to current month."""
    today = date.today()
    from_str = request.GET.get("from_date")
    to_str = request.GET.get("to_date")
    try:
        from_date = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    except (ValueError, TypeError):
        from_date = today.replace(day=1)
    try:
        to_date = date.fromisoformat(to_str) if to_str else today
    except (ValueError, TypeError):
        to_date = today
    return from_date, to_date


@login_required
def modern_attendance_dashboard(request):
    """Render the modern attendance dashboard page."""
    return render(request, "attendance/dashboard_modern.html")


@login_required
def attendance_kpi_data(request):
    """Return attendance KPI summary data as JSON."""
    from attendance.models import Attendance, AttendanceLateComeEarlyOut
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    total_employees = Employee.objects.filter(is_active=True).count()

    present_today = (
        Attendance.objects.filter(
            attendance_date=today,
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    attendance_rate = (
        round((present_today / total_employees * 100), 1) if total_employees > 0 else 0
    )

    late_come = (
        AttendanceLateComeEarlyOut.objects.filter(
            type="late_come",
            attendance_id__attendance_date=today,
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    early_out = (
        AttendanceLateComeEarlyOut.objects.filter(
            type="early_out",
            attendance_id__attendance_date=today,
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    on_time = max(0, present_today - late_come)

    # Pending validation
    pending_validation = Attendance.objects.filter(
        attendance_validated=False,
    ).count()

    # Pending overtime approval
    pending_overtime = 0
    try:
        pending_overtime = Attendance.objects.filter(
            attendance_overtime_approve=False,
            attendance_validated=True,
            overtime_second__gt=0,
        ).count()
    except Exception:
        pass

    return JsonResponse(
        {
            "total_employees": total_employees,
            "present_today": present_today,
            "attendance_rate": attendance_rate,
            "on_time": on_time,
            "late_come": late_come,
            "early_out": early_out,
            "pending_validation": pending_validation,
            "pending_overtime": pending_overtime,
            "date": today.isoformat(),
        }
    )


@login_required
def attendance_weekly_trend(request):
    """Daily attendance count for the selected period (up to 31 days)."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    today = date.today()
    days = []

    d = from_date
    while d <= to_date:
        count = (
            Attendance.objects.filter(
                attendance_date=d,
            )
            .values("employee_id")
            .distinct()
            .count()
        )
        days.append(
            {
                "day": d.strftime("%a"),
                "date": d.isoformat(),
                "count": count,
                "is_today": d == today,
            }
        )
        d += timedelta(days=1)
        if len(days) >= 31:
            break

    return JsonResponse({"days": days, "week_start": from_date.isoformat()})


@login_required
def attendance_department_breakdown(request):
    """Attendance broken down by department for the selected date (to_date)."""
    from attendance.models import Attendance
    from employee.models import Employee

    _, today = _parse_period(request)
    departments = []

    try:
        dept_data = (
            Attendance.objects.filter(attendance_date=today)
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(present=Count("employee_id", distinct=True))
            .order_by("-present")
        )

        for item in dept_data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                total_in_dept = Employee.objects.filter(
                    is_active=True,
                    employee_work_info__department_id__department=dept,
                ).count()
                departments.append(
                    {
                        "department": dept,
                        "present": item["present"],
                        "total": total_in_dept,
                        "rate": (
                            round((item["present"] / total_in_dept * 100), 1)
                            if total_in_dept > 0
                            else 0
                        ),
                    }
                )
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def attendance_late_early_data(request):
    """Late come and early out breakdown by department for the selected date (to_date)."""
    from attendance.models import AttendanceLateComeEarlyOut

    _, today = _parse_period(request)
    late_data = []
    early_data = []

    try:
        late = (
            AttendanceLateComeEarlyOut.objects.filter(
                type="late_come",
                attendance_id__attendance_date=today,
            )
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("employee_id", distinct=True))
            .order_by("-count")
        )
        for item in late:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                late_data.append({"department": dept, "count": item["count"]})

        early = (
            AttendanceLateComeEarlyOut.objects.filter(
                type="early_out",
                attendance_id__attendance_date=today,
            )
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("employee_id", distinct=True))
            .order_by("-count")
        )
        for item in early:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                early_data.append({"department": dept, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"late_come": late_data, "early_out": early_data})


@login_required
def attendance_overtime_summary(request):
    """Overtime summary by department for the current month."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    departments = []

    try:
        data = (
            Attendance.objects.filter(
                attendance_date__gte=first_of_month,
                attendance_date__lte=today,
                attendance_validated=True,
                overtime_second__gt=0,
            )
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(
                total_ot=Sum("overtime_second"),
                total_approved=Sum("approved_overtime_second"),
                count=Count("employee_id", distinct=True),
            )
            .order_by("-total_ot")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "total_hours": round((item["total_ot"] or 0) / 3600, 1),
                        "approved_hours": round(
                            (item["total_approved"] or 0) / 3600, 1
                        ),
                        "employees": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse(
        {
            "departments": departments,
            "month": today.strftime("%B %Y"),
        }
    )


@login_required
def attendance_hours_distribution(request):
    """Worked hours vs pending hours by department."""
    from attendance.models import AttendanceOverTime
    from base.models import Department

    departments = []

    try:
        dept_list = list(Department.objects.values_list("department", flat=True))

        for dept in dept_list:
            records = AttendanceOverTime.objects.filter(
                employee_id__employee_work_info__department_id__department=dept,
                employee_id__is_active=True,
            )
            if not records.exists():
                continue

            worked = sum(r.hour_account_second or 0 for r in records)
            pending = sum(r.hour_pending_second or 0 for r in records)

            departments.append(
                {
                    "department": dept,
                    "worked_hours": round(worked / 3600, 1),
                    "pending_hours": round(pending / 3600, 1),
                }
            )

        departments.sort(key=lambda x: x["worked_hours"], reverse=True)
    except Exception:
        pass

    return JsonResponse({"departments": departments[:10]})


@login_required
def attendance_shift_distribution(request):
    """Employee distribution by shift type."""
    from employee.models import Employee

    shifts = []

    try:
        data = (
            Employee.objects.filter(is_active=True)
            .exclude(employee_work_info__shift_id__isnull=True)
            .values("employee_work_info__shift_id__employee_shift")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            shift = item["employee_work_info__shift_id__employee_shift"]
            if shift:
                shifts.append({"shift": shift, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"shifts": shifts})


@login_required
def attendance_absenteeism_trend(request):
    """Monthly absenteeism rate for the last 6 months."""
    from attendance.models import Attendance
    from employee.models import Employee

    _, to_date = _parse_period(request)
    today = to_date
    months = []

    try:
        total_employees = Employee.objects.filter(is_active=True).count()

        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(
                    year=month_start.year + 1, month=1
                ) - timedelta(days=1)
            else:
                month_end = month_start.replace(
                    month=month_start.month + 1
                ) - timedelta(days=1)

            # Count working days (Mon-Fri) in the month
            working_days = 0
            d = month_start
            while d <= min(month_end, today):
                if d.weekday() < 5:
                    working_days += 1
                d += timedelta(days=1)

            if working_days == 0 or total_employees == 0:
                months.append({"month": month_start.strftime("%b %Y"), "rate": 0})
                continue

            # Count unique employee-days with attendance
            present_days = (
                Attendance.objects.filter(
                    attendance_date__gte=month_start,
                    attendance_date__lte=min(month_end, today),
                )
                .values("employee_id", "attendance_date")
                .distinct()
                .count()
            )

            expected_days = total_employees * working_days
            absent_days = max(0, expected_days - present_days)
            absenteeism_rate = round((absent_days / expected_days * 100), 1)

            months.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "rate": absenteeism_rate,
                    "absent_days": absent_days,
                    "expected_days": expected_days,
                }
            )
    except Exception:
        months = [{"month": f"M{i+1}", "rate": 0} for i in range(6)]

    return JsonResponse({"months": months})


@login_required
def attendance_work_type_distribution(request):
    """Employee distribution by work type (remote, on-site, hybrid, etc.)."""
    from employee.models import Employee

    work_types = []

    try:
        data = (
            Employee.objects.filter(is_active=True)
            .exclude(employee_work_info__work_type_id__isnull=True)
            .values("employee_work_info__work_type_id__work_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            wt = item["employee_work_info__work_type_id__work_type"]
            if wt:
                work_types.append({"work_type": wt, "count": item["count"]})

        # Count employees with no work type assigned
        no_wt = Employee.objects.filter(
            is_active=True,
            employee_work_info__work_type_id__isnull=True,
        ).count()
        if no_wt > 0:
            work_types.append({"work_type": "Not Assigned", "count": no_wt})
    except Exception:
        pass

    return JsonResponse({"work_types": work_types})


@login_required
def attendance_avg_working_hours(request):
    """Average working hours per department for the current month."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    departments = []

    try:
        data = (
            Attendance.objects.filter(
                attendance_date__gte=first_of_month,
                attendance_date__lte=today,
                at_work_second__gt=0,
            )
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(
                total_seconds=Sum("at_work_second"),
                att_count=Count("id"),
                emp_count=Count("employee_id", distinct=True),
            )
            .order_by("-total_seconds")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if not dept:
                continue
            total_hrs = (item["total_seconds"] or 0) / 3600
            avg_per_day = (
                round(total_hrs / item["att_count"], 1) if item["att_count"] > 0 else 0
            )
            departments.append(
                {
                    "department": dept,
                    "avg_hours_per_day": avg_per_day,
                    "total_hours": round(total_hrs, 1),
                    "employees": item["emp_count"],
                }
            )

        departments.sort(key=lambda x: x["avg_hours_per_day"], reverse=True)
    except Exception:
        pass

    return JsonResponse(
        {
            "departments": departments[:10],
            "month": today.strftime("%B %Y"),
        }
    )


@login_required
def attendance_top_absentees(request):
    """Top 10 employees with most absences in the current month."""
    from attendance.models import Attendance
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    absentees = []

    try:
        # Count working days so far this month
        working_days = 0
        d = first_of_month
        while d <= today:
            if d.weekday() < 5:
                working_days += 1
            d += timedelta(days=1)

        if working_days == 0:
            return JsonResponse({"absentees": []})

        employees = Employee.objects.filter(is_active=True)

        for emp in employees:
            present_days = (
                Attendance.objects.filter(
                    employee_id=emp,
                    attendance_date__gte=first_of_month,
                    attendance_date__lte=today,
                )
                .values("attendance_date")
                .distinct()
                .count()
            )

            absent_days = max(0, working_days - present_days)
            if absent_days > 0:
                absentees.append(
                    {
                        "id": emp.id,
                        "name": emp.get_full_name(),
                        "avatar": (
                            emp.employee_profile.url if emp.employee_profile else None
                        ),
                        "absent_days": absent_days,
                        "present_days": present_days,
                        "total_days": working_days,
                        "rate": round((absent_days / working_days * 100), 1),
                    }
                )

        absentees.sort(key=lambda x: x["absent_days"], reverse=True)
    except Exception:
        pass

    return JsonResponse(
        {
            "absentees": absentees[:10],
            "month": today.strftime("%B %Y"),
        }
    )


@login_required
def attendance_clockin_distribution(request):
    """Distribution of clock-in times for today."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    buckets = {}
    try:
        qs = Attendance.objects.filter(
            attendance_date=to_date, attendance_clock_in__isnull=False
        )
        for att in qs:
            hour = att.attendance_clock_in.hour
            label = f"{hour:02d}:00"
            buckets[label] = buckets.get(label, 0) + 1
    except Exception:
        pass
    sorted_buckets = sorted(buckets.items())
    return JsonResponse(
        {
            "hours": [b[0] for b in sorted_buckets],
            "counts": [b[1] for b in sorted_buckets],
        }
    )


@login_required
def attendance_calendar_heatmap(request):
    """Daily attendance count for the selected month."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    days = []
    try:
        from employee.models import Employee

        total = Employee.objects.filter(is_active=True).count()
        d = from_date
        while d <= to_date:
            count = (
                Attendance.objects.filter(attendance_date=d)
                .values("employee_id")
                .distinct()
                .count()
            )
            rate = round((count / total * 100), 1) if total > 0 else 0
            days.append(
                {
                    "date": d.isoformat(),
                    "day": d.strftime("%a"),
                    "dom": d.day,
                    "count": count,
                    "rate": rate,
                }
            )
            d += timedelta(days=1)
    except Exception:
        pass
    return JsonResponse({"days": days, "month": from_date.strftime("%B %Y")})
