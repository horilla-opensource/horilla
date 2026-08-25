"""
Modern attendance dashboard views — KPI summary + ApexCharts.

Accessible at /attendance/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from base.decorators import manager_can_enter


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


def _latest_attendance_date(reference_date=None):
    """Return the latest attendance_date that actually has records.

    Falls back to the given reference_date (or today) if no attendance exists at all,
    so callers can still execute their queries with a safe default.
    """
    from attendance.models import Attendance

    ref = reference_date or date.today()
    latest = (
        Attendance.objects.filter(attendance_date__lte=ref)
        .order_by("-attendance_date")
        .values_list("attendance_date", flat=True)
        .first()
    )
    return latest or ref


@login_required
@manager_can_enter("attendance.view_attendance")
def attendance_dashboard_view(request):
    """Render the modern attendance dashboard page."""
    return render(request, "attendance/dashboard.html")


@login_required
def attendance_kpi_data(request):
    """Return attendance KPI summary data as JSON."""
    from attendance.models import Attendance, AttendanceLateComeEarlyOut
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    first_of_month = from_date
    total_employees = Employee.objects.filter(is_active=True).count()

    # "Present Today" is a real-time indicator, not scoped to whatever
    # report period is selected above (to_date defaults to end-of-month,
    # a future date) - use the actual current date, like the main HR
    # dashboard's equivalent KPI does. Deliberately NOT routed through
    # _latest_attendance_date(): that fallback would silently substitute an
    # older date with data, so the card's own label ("Present Today") and
    # the date actually being filtered/linked to would disagree - a 0 for
    # today is a more honest result than a non-zero count for some other day.
    today = date.today()

    # This card (and "On Time" below) link through to the "Attendance To
    # Validate" tab, which only ever shows attendance_validated=False rows
    # - so the count needs the same scope, or it'll show a number here that
    # doesn't match a single row on the page it links to.
    present_today = (
        Attendance.objects.filter(
            attendance_date=today,
            attendance_validated=False,
            employee_id__is_active=True,
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
            attendance_id__attendance_validated=False,
            employee_id__is_active=True,
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    early_out = (
        AttendanceLateComeEarlyOut.objects.filter(
            type="early_out",
            attendance_id__attendance_date=today,
            attendance_id__attendance_validated=False,
            employee_id__is_active=True,
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    on_time = max(0, present_today - late_come)

    # Pending validation - scoped the same way as the "Attendance To
    # Validate" tab it links to (employee_id__is_active=True), otherwise
    # this count includes inactive employees' records the destination list
    # never shows.
    pending_validation = Attendance.objects.filter(
        attendance_validated=False,
        employee_id__is_active=True,
    ).count()

    # Pending overtime approval - same reasoning, matches the "OT
    # Attendances" tab's own active-employee scoping.
    pending_overtime = 0
    try:
        pending_overtime = Attendance.objects.filter(
            attendance_overtime_approve=False,
            attendance_validated=True,
            overtime_second__gt=0,
            employee_id__is_active=True,
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
    """Attendance headcount across the selected period.

    Daily bars when span ≤ 14 days; otherwise aggregates by ISO week so the
    chart stays readable for longer ranges (e.g. a quarter).
    """
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    today = date.today()
    span = (to_date - from_date).days

    counts = {
        row["attendance_date"]: row["c"]
        for row in (
            Attendance.objects.filter(
                attendance_date__gte=from_date,
                attendance_date__lte=to_date,
            )
            .values("attendance_date")
            .annotate(c=Count("employee_id", distinct=True))
        )
    }

    period_label = (
        f"{from_date.strftime('%b %d')} – {to_date.strftime('%b %d, %Y')}"
        if from_date.year == to_date.year
        else f"{from_date.strftime('%b %d, %Y')} – {to_date.strftime('%b %d, %Y')}"
    )

    if span <= 14:
        days = []
        d = from_date
        while d <= to_date:
            days.append(
                {
                    "day": d.strftime("%a"),
                    "date": d.isoformat(),
                    "count": counts.get(d, 0),
                    "is_today": d == today,
                }
            )
            d += timedelta(days=1)
        return JsonResponse(
            {
                "days": days,
                "aggregate": "daily",
                "week_start": from_date.isoformat(),
                "period_label": period_label,
            }
        )

    # Weekly aggregation
    days = []
    week_start = from_date - timedelta(days=from_date.weekday())  # Monday
    while week_start <= to_date:
        week_end = week_start + timedelta(days=6)
        bucket_total = 0
        d = max(week_start, from_date)
        last = min(week_end, to_date)
        contains_today = d <= today <= last
        while d <= last:
            bucket_total += counts.get(d, 0)
            d += timedelta(days=1)
        # Use the average daily headcount across the week to keep the y-axis
        # comparable to daily mode.
        bucket_days = (last - max(week_start, from_date)).days + 1
        avg = round(bucket_total / bucket_days) if bucket_days > 0 else 0
        label_start = max(week_start, from_date).strftime("%b %d")
        days.append(
            {
                "day": label_start,
                "date": max(week_start, from_date).isoformat(),
                "count": avg,
                "is_today": contains_today,
            }
        )
        week_start += timedelta(days=7)

    return JsonResponse(
        {
            "days": days,
            "aggregate": "weekly",
            "week_start": from_date.isoformat(),
            "period_label": period_label,
        }
    )


@login_required
def attendance_department_breakdown(request):
    """Attendance broken down by department for the selected date (to_date)."""
    from attendance.models import Attendance
    from employee.models import Employee

    _, to_date = _parse_period(request)
    today = _latest_attendance_date(to_date)
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

    return JsonResponse({"departments": departments, "date": today.isoformat()})


@login_required
def attendance_late_early_data(request):
    """Late come and early out breakdown by department for the selected date (to_date)."""
    from attendance.models import AttendanceLateComeEarlyOut

    _, to_date = _parse_period(request)
    today = _latest_attendance_date(to_date)
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

    return JsonResponse(
        {"late_come": late_data, "early_out": early_data, "date": today.isoformat()}
    )


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
            "from_date": first_of_month.isoformat(),
            "to_date": today.isoformat(),
        }
    )


@login_required
def attendance_hours_distribution(request):
    """Worked hours vs pending hours by department for the selected period."""
    from attendance.models import Attendance, AttendanceOverTime
    from base.models import Department

    from_date, to_date = _parse_period(request)
    departments = []

    try:
        dept_list = list(Department.objects.values_list("department", flat=True))

        for dept in dept_list:
            worked_seconds = (
                Attendance.objects.filter(
                    employee_id__employee_work_info__department_id__department=dept,
                    employee_id__is_active=True,
                    attendance_date__gte=from_date,
                    attendance_date__lte=to_date,
                ).aggregate(total=Sum("at_work_second"))["total"]
                or 0
            )

            pending_seconds = sum(
                max(r.hour_pending_second or 0, 0)
                for r in AttendanceOverTime.objects.filter(
                    employee_id__employee_work_info__department_id__department=dept,
                    employee_id__is_active=True,
                )
            )

            if worked_seconds == 0 and pending_seconds == 0:
                continue

            departments.append(
                {
                    "department": dept,
                    "worked_hours": round(max(worked_seconds, 0) / 3600, 1),
                    "pending_hours": round(pending_seconds / 3600, 1),
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
            .values(
                "employee_work_info__shift_id",
                "employee_work_info__shift_id__employee_shift",
            )
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            shift = item["employee_work_info__shift_id__employee_shift"]
            shift_id = item["employee_work_info__shift_id"]
            if shift:
                shifts.append(
                    {"shift": shift, "shift_id": shift_id, "count": item["count"]}
                )
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

        current_month_start = today.replace(day=1)
        for i in range(5, -1, -1):
            # Step back i full months using year/month arithmetic (no day drift)
            year = current_month_start.year
            month = current_month_start.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

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
            .values(
                "employee_work_info__work_type_id",
                "employee_work_info__work_type_id__work_type",
            )
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            wt = item["employee_work_info__work_type_id__work_type"]
            wt_id = item["employee_work_info__work_type_id"]
            if wt:
                work_types.append(
                    {"work_type": wt, "work_type_id": wt_id, "count": item["count"]}
                )

        # Count employees with no work type assigned
        no_wt = Employee.objects.filter(
            is_active=True,
            employee_work_info__work_type_id__isnull=True,
        ).count()
        if no_wt > 0:
            work_types.append(
                {"work_type": _("Not Assigned"), "work_type_id": None, "count": no_wt}
            )
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
            "from_date": first_of_month.isoformat(),
            "to_date": today.isoformat(),
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
                        "avatar": emp.get_avatar(),
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
    """Distribution of clock-in times for today (or latest day with records)."""
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    target_date = _latest_attendance_date(to_date)
    buckets = {}
    try:
        qs = Attendance.objects.filter(
            attendance_date=target_date, attendance_clock_in__isnull=False
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
            "date": target_date.isoformat(),
        }
    )


@login_required
def attendance_calendar_heatmap(request):
    """Attendance rate per day (or per ISO week for longer ranges).

    For ≤ 31 days the chart shows one bar per day. Beyond that, daily bars
    cram together — so we aggregate to one bar per ISO week and use the
    week's average rate.
    """
    from attendance.models import Attendance

    from_date, to_date = _parse_period(request)
    span = (to_date - from_date).days
    days = []
    aggregate = "daily"
    try:
        from employee.models import Employee

        total = Employee.objects.filter(is_active=True).count()
        counts = {
            row["attendance_date"]: row["c"]
            for row in (
                Attendance.objects.filter(
                    attendance_date__gte=from_date,
                    attendance_date__lte=to_date,
                )
                .values("attendance_date")
                .annotate(c=Count("employee_id", distinct=True))
            )
        }

        if span <= 31:
            d = from_date
            while d <= to_date:
                c = counts.get(d, 0)
                rate = round((c / total * 100), 1) if total > 0 else 0
                days.append(
                    {
                        "date": d.isoformat(),
                        "day": d.strftime("%a"),
                        "dom": d.day,
                        "label": (
                            d.strftime("%b %d")
                            if from_date.month != to_date.month
                            else d.day
                        ),
                        "count": c,
                        "rate": rate,
                    }
                )
                d += timedelta(days=1)
        else:
            aggregate = "weekly"
            week_start = from_date - timedelta(days=from_date.weekday())  # Monday
            while week_start <= to_date:
                week_end = week_start + timedelta(days=6)
                actual_start = max(week_start, from_date)
                actual_end = min(week_end, to_date)
                rates = []
                bucket_total = 0
                d = actual_start
                while d <= actual_end:
                    c = counts.get(d, 0)
                    bucket_total += c
                    if total > 0:
                        rates.append((c / total) * 100)
                    d += timedelta(days=1)
                avg_rate = round(sum(rates) / len(rates), 1) if rates else 0
                bucket_days = (actual_end - actual_start).days + 1
                avg_count = round(bucket_total / bucket_days) if bucket_days > 0 else 0
                days.append(
                    {
                        "date": actual_start.isoformat(),
                        "day": actual_start.strftime("%b %d"),
                        "dom": actual_start.day,
                        "label": actual_start.strftime("%b %d"),
                        "count": avg_count,
                        "rate": avg_rate,
                    }
                )
                week_start += timedelta(days=7)
    except Exception:
        pass

    if from_date.year == to_date.year and from_date.month == to_date.month:
        period_label = from_date.strftime("%B %Y")
    elif from_date.year == to_date.year:
        period_label = (
            f"{from_date.strftime('%b %d')} – {to_date.strftime('%b %d, %Y')}"
        )
    else:
        period_label = (
            f"{from_date.strftime('%b %d, %Y')} – {to_date.strftime('%b %d, %Y')}"
        )

    return JsonResponse(
        {
            "days": days,
            "month": period_label,
            "aggregate": aggregate,
            "period_label": period_label,
        }
    )


@login_required
def attendance_overview(request):
    """Department-wise on-time / late / early counts for the latest day with attendance.

    Same shape as the legacy dashboard_attendance endpoint, but falls back to the most
    recent day that actually has records (so the modern dashboard renders even when
    today has no clock-ins yet).
    """
    from attendance.models import Attendance, AttendanceLateComeEarlyOut
    from base.models import Department

    _from_date, to_date = _parse_period(request)
    target_date = _latest_attendance_date(to_date)

    labels = []
    on_time_series = []
    late_series = []
    early_series = []

    try:
        for dept in Department.objects.all():
            dept_attendance = Attendance.objects.filter(
                attendance_date=target_date,
                employee_id__employee_work_info__department_id=dept,
            )
            present_count = dept_attendance.values("employee_id").distinct().count()
            if not present_count:
                continue

            late_count = (
                AttendanceLateComeEarlyOut.objects.filter(
                    type="late_come",
                    attendance_id__attendance_date=target_date,
                    employee_id__employee_work_info__department_id=dept,
                )
                .values("employee_id")
                .distinct()
                .count()
            )
            early_count = (
                AttendanceLateComeEarlyOut.objects.filter(
                    type="early_out",
                    attendance_id__attendance_date=target_date,
                    employee_id__employee_work_info__department_id=dept,
                )
                .values("employee_id")
                .distinct()
                .count()
            )
            on_time_count = max(0, present_count - late_count)

            labels.append(dept.department)
            on_time_series.append(on_time_count)
            late_series.append(late_count)
            early_series.append(early_count)
    except Exception:
        pass

    data_set = [
        {"label": _("On Time"), "data": on_time_series},
        {"label": _("Late Arrival"), "data": late_series},
        {"label": _("Early Departure"), "data": early_series},
    ]
    return JsonResponse(
        {
            "dataSet": data_set,
            "labels": labels,
            "date": target_date.isoformat(),
        }
    )
