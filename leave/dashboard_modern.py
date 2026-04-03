"""
Modern leave dashboard views — KPI summary + ApexCharts.

Accessible at /leave/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, FloatField, Q, Sum
from django.db.models.functions import Coalesce
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
def modern_leave_dashboard(request):
    """Render the modern leave dashboard page."""
    return render(request, "leave/dashboard_modern.html")


@login_required
def leave_kpi_data(request):
    """Return leave KPI summary data as JSON."""
    from leave.models import AvailableLeave, LeaveAllocationRequest, LeaveRequest

    from_date, to_date = _parse_period(request)
    first_of_month = from_date
    real_today = date.today()  # always current date for point-in-time metrics

    pending_approval = LeaveRequest.objects.filter(status="requested").count()

    approved_this_month = LeaveRequest.objects.filter(
        status="approved",
        start_date__gte=first_of_month,
        start_date__lte=to_date,
    ).count()

    rejected_this_month = LeaveRequest.objects.filter(
        status="rejected",
        start_date__gte=first_of_month,
        start_date__lte=to_date,
    ).count()

    # Always reflects who is on leave right now, independent of the date filter
    on_leave_today = (
        LeaveRequest.objects.filter(
            start_date__lte=real_today,
            end_date__gte=real_today,
            status="approved",
        )
        .values("employee_id")
        .distinct()
        .count()
    )

    # Total leave days approved within the selected period
    total_days_used = LeaveRequest.objects.filter(
        status="approved",
        start_date__gte=first_of_month,
        start_date__lte=to_date,
    ).aggregate(total=Coalesce(Sum("requested_days"), 0.0, output_field=FloatField()))[
        "total"
    ]

    # Pending allocation requests
    pending_allocations = 0
    try:
        pending_allocations = LeaveAllocationRequest.objects.filter(
            status="requested"
        ).count()
    except Exception:
        pass

    # Pending comp leave requests
    pending_comp = 0
    try:
        from leave.models import CompensatoryLeaveRequest

        pending_comp = CompensatoryLeaveRequest.objects.filter(
            status="requested"
        ).count()
    except Exception:
        pass

    return JsonResponse(
        {
            "pending_approval": pending_approval,
            "approved_this_month": approved_this_month,
            "rejected_this_month": rejected_this_month,
            "on_leave_today": on_leave_today,
            "total_days_used": round(float(total_days_used), 1),
            "pending_allocations": pending_allocations,
            "pending_comp": pending_comp,
            "month": to_date.strftime("%B %Y"),
        }
    )


@login_required
def leave_monthly_trend(request):
    """Monthly leave request counts for the last 6 months."""
    from leave.models import LeaveRequest

    _, to_date = _parse_period(request)
    today = to_date
    months = []

    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(
                year=month_start.year + 1, month=1
            ) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(
                days=1
            )

        approved = LeaveRequest.objects.filter(
            status="approved",
            start_date__gte=month_start,
            start_date__lte=month_end,
        ).count()

        rejected = LeaveRequest.objects.filter(
            status="rejected",
            start_date__gte=month_start,
            start_date__lte=month_end,
        ).count()

        pending = LeaveRequest.objects.filter(
            status="requested",
            start_date__gte=month_start,
            start_date__lte=month_end,
        ).count()

        months.append(
            {
                "month": month_start.strftime("%b %Y"),
                "approved": approved,
                "rejected": rejected,
                "pending": pending,
            }
        )

    return JsonResponse({"months": months})


@login_required
def leave_type_distribution(request):
    """Leave days by type for the current month."""
    from leave.models import LeaveRequest

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    types = []

    try:
        data = (
            LeaveRequest.objects.filter(
                status="approved",
                start_date__gte=first_of_month,
                start_date__lte=today,
            )
            .values(
                "leave_type_id__name", "leave_type_id__color", "leave_type_id__payment"
            )
            .annotate(count=Count("id"), total_days=Sum("requested_days"))
            .order_by("-total_days")
        )

        for item in data:
            types.append(
                {
                    "type": item["leave_type_id__name"] or "Unknown",
                    "color": item["leave_type_id__color"] or None,
                    "payment": item["leave_type_id__payment"] or "unpaid",
                    "count": item["count"],
                    "days": round(float(item["total_days"] or 0), 1),
                }
            )
    except Exception:
        pass

    return JsonResponse({"types": types, "month": today.strftime("%B %Y")})


@login_required
def leave_department_breakdown(request):
    """Leave days by department for the current month."""
    from leave.models import LeaveRequest

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    departments = []

    try:
        data = (
            LeaveRequest.objects.filter(
                status="approved",
                start_date__gte=first_of_month,
                start_date__lte=today,
            )
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("id"), total_days=Sum("requested_days"))
            .order_by("-total_days")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "count": item["count"],
                        "days": round(float(item["total_days"] or 0), 1),
                    }
                )
    except Exception:
        pass

    return JsonResponse({"departments": departments, "month": today.strftime("%B %Y")})


@login_required
def leave_utilization_rate(request):
    """Leave utilization: used vs available across all employees."""
    from employee.models import Employee
    from leave.models import AvailableLeave

    utilization = []

    try:
        data = (
            AvailableLeave.objects.filter(employee_id__is_active=True)
            .values("leave_type_id__name")
            .annotate(
                total_available=Sum("available_days"),
                total_carryforward=Sum("carryforward_days"),
                total_allocated=Sum("total_leave_days"),
            )
            .order_by("-total_allocated")
        )

        for item in data:
            allocated = float(item["total_allocated"] or 0)
            available = float(item["total_available"] or 0) + float(
                item["total_carryforward"] or 0
            )
            used = max(0, allocated - available)
            rate = round((used / allocated * 100), 1) if allocated > 0 else 0

            utilization.append(
                {
                    "type": item["leave_type_id__name"] or "Unknown",
                    "allocated": round(allocated, 1),
                    "used": round(used, 1),
                    "remaining": round(available, 1),
                    "rate": rate,
                }
            )
    except Exception:
        pass

    return JsonResponse({"utilization": utilization})


@login_required
def leave_paid_unpaid_split(request):
    """Paid vs unpaid leave days for the current month."""
    from leave.models import LeaveRequest

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date

    paid = 0
    unpaid = 0

    try:
        data = (
            LeaveRequest.objects.filter(
                status="approved",
                start_date__gte=first_of_month,
                start_date__lte=today,
            )
            .values("leave_type_id__payment")
            .annotate(total_days=Sum("requested_days"))
        )

        for item in data:
            days = float(item["total_days"] or 0)
            if item["leave_type_id__payment"] == "paid":
                paid += days
            else:
                unpaid += days
    except Exception:
        pass

    return JsonResponse(
        {
            "paid": round(paid, 1),
            "unpaid": round(unpaid, 1),
            "month": today.strftime("%B %Y"),
        }
    )


@login_required
def leave_top_takers(request):
    """Top 10 employees by leave days taken this month."""
    from leave.models import LeaveRequest

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    takers = []

    try:
        data = (
            LeaveRequest.objects.filter(
                status="approved",
                start_date__gte=first_of_month,
                start_date__lte=today,
            )
            .values(
                "employee_id",
                "employee_id__employee_first_name",
                "employee_id__employee_last_name",
                "employee_id__employee_profile",
            )
            .annotate(total_days=Sum("requested_days"), request_count=Count("id"))
            .order_by("-total_days")[:10]
        )

        for item in data:
            first = item["employee_id__employee_first_name"] or ""
            last = item["employee_id__employee_last_name"] or ""
            name = f"{first} {last}".strip()
            avatar = item["employee_id__employee_profile"]

            takers.append(
                {
                    "id": item["employee_id"],
                    "name": name,
                    "avatar": f"/media/{avatar}" if avatar else None,
                    "days": round(float(item["total_days"] or 0), 1),
                    "requests": item["request_count"],
                }
            )
    except Exception:
        pass

    return JsonResponse(
        {
            "takers": takers,
            "month": today.strftime("%B %Y"),
        }
    )


@login_required
def leave_on_leave_today(request):
    """Employees currently on leave."""
    from leave.models import LeaveRequest

    today = date.today()
    employees = []

    try:
        qs = (
            LeaveRequest.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                status="approved",
            )
            .select_related("employee_id", "leave_type_id")
            .order_by("employee_id__employee_first_name")[:20]
        )

        for lr in qs:
            emp = lr.employee_id
            employees.append(
                {
                    "id": emp.id if emp else None,
                    "name": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "leave_type": lr.leave_type_id.name if lr.leave_type_id else "—",
                    "start": lr.start_date.strftime("%b %d"),
                    "end": (
                        lr.end_date.strftime("%b %d")
                        if lr.end_date
                        else lr.start_date.strftime("%b %d")
                    ),
                    "days": float(lr.requested_days) if lr.requested_days else 1,
                }
            )
    except Exception:
        pass

    return JsonResponse({"employees": employees, "date": today.isoformat()})


@login_required
def leave_upcoming_holidays(request):
    """Upcoming holidays in the next 30 days."""
    from base.models import Holidays

    today = date.today()
    end = today + timedelta(days=30)
    holidays = []

    try:
        qs = Holidays.objects.filter(
            start_date__gte=today,
            start_date__lte=end,
        ).order_by("start_date")[:10]

        for h in qs:
            holidays.append(
                {
                    "name": h.name,
                    "start": h.start_date.strftime("%b %d"),
                    "end": (
                        h.end_date.strftime("%b %d")
                        if h.end_date and h.end_date != h.start_date
                        else None
                    ),
                    "days_away": (h.start_date - today).days,
                }
            )
    except Exception:
        pass

    return JsonResponse({"holidays": holidays})


@login_required
def leave_weekly_pattern(request):
    """Leave requests by day of week for the last 3 months (pattern analysis)."""
    from leave.models import LeaveRequest

    today = date.today()
    three_months_ago = today - timedelta(days=90)
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    counts = [0] * 7

    try:
        leaves = LeaveRequest.objects.filter(
            status="approved",
            start_date__gte=three_months_ago,
            start_date__lte=today,
        )

        for lr in leaves:
            d = lr.start_date
            while d <= (lr.end_date or lr.start_date) and d <= today:
                if d >= three_months_ago:
                    counts[d.weekday()] += 1
                d += timedelta(days=1)
    except Exception:
        pass

    return JsonResponse(
        {
            "days": days,
            "counts": counts,
        }
    )


@login_required
def leave_upcoming(request):
    """Approved leaves starting in the next 7 days."""
    from leave.models import LeaveRequest

    today = date.today()
    end = today + timedelta(days=7)
    upcoming = []

    try:
        qs = (
            LeaveRequest.objects.filter(
                status="approved",
                start_date__gt=today,
                start_date__lte=end,
            )
            .select_related("employee_id", "leave_type_id")
            .order_by("start_date")[:15]
        )

        for lr in qs:
            emp = lr.employee_id
            days_away = (lr.start_date - today).days
            upcoming.append(
                {
                    "id": emp.id if emp else None,
                    "name": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "leave_type": lr.leave_type_id.name if lr.leave_type_id else "—",
                    "start": lr.start_date.strftime("%b %d"),
                    "end": (
                        lr.end_date.strftime("%b %d")
                        if lr.end_date
                        else lr.start_date.strftime("%b %d")
                    ),
                    "days": float(lr.requested_days) if lr.requested_days else 1,
                    "days_away": days_away,
                }
            )
    except Exception:
        pass

    return JsonResponse({"upcoming": upcoming})
