"""
Modern helpdesk dashboard views — KPI summary + ApexCharts.

Accessible at /helpdesk/dashboard/modern/ alongside the existing pipeline view.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q
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
def modern_helpdesk_dashboard(request):
    """Render the modern helpdesk dashboard page."""
    return render(request, "helpdesk/dashboard_modern.html")


@login_required
def helpdesk_kpi_data(request):
    """Return helpdesk KPI summary data as JSON."""
    from helpdesk.models import ClaimRequest, Ticket

    total_tickets = Ticket.objects.filter(is_active=True).count()
    new_tickets = Ticket.objects.filter(is_active=True, status="new").count()
    in_progress = Ticket.objects.filter(is_active=True, status="in_progress").count()
    on_hold = Ticket.objects.filter(is_active=True, status="on_hold").count()
    resolved = Ticket.objects.filter(is_active=True, status="resolved").count()
    canceled = Ticket.objects.filter(is_active=True, status="canceled").count()

    # Open tickets (new + in_progress + on_hold)
    open_tickets = new_tickets + in_progress + on_hold

    # Resolution rate
    resolution_rate = (
        round((resolved / total_tickets * 100), 1) if total_tickets > 0 else 0
    )

    # Overdue tickets (past deadline, not resolved/canceled)
    today = date.today()
    overdue = Ticket.objects.filter(
        is_active=True,
        deadline__lt=today,
        status__in=["new", "in_progress", "on_hold"],
    ).count()

    # Pending claims
    pending_claims = ClaimRequest.objects.filter(
        is_approved=False,
        is_rejected=False,
    ).count()

    # Avg resolution time (days between created_date and resolved_date)
    avg_resolution = None
    try:
        resolved_tickets = Ticket.objects.filter(
            is_active=True,
            status="resolved",
            resolved_date__isnull=False,
        )
        if resolved_tickets.exists():
            total_days = 0
            count = 0
            for t in resolved_tickets:
                if t.resolved_date and t.created_date:
                    delta = (t.resolved_date - t.created_date).days
                    if delta >= 0:
                        total_days += delta
                        count += 1
            avg_resolution = round(total_days / count, 1) if count > 0 else None
    except Exception:
        pass

    return JsonResponse(
        {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "new_tickets": new_tickets,
            "in_progress": in_progress,
            "on_hold": on_hold,
            "resolved": resolved,
            "canceled": canceled,
            "resolution_rate": resolution_rate,
            "overdue": overdue,
            "pending_claims": pending_claims,
            "avg_resolution_days": avg_resolution,
        }
    )


@login_required
def helpdesk_status_distribution(request):
    """Ticket count by status."""
    from helpdesk.models import Ticket

    statuses = []
    status_choices = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("resolved", "Resolved"),
        ("canceled", "Canceled"),
    ]

    for status, label in status_choices:
        count = Ticket.objects.filter(is_active=True, status=status).count()
        statuses.append({"status": status, "label": label, "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def helpdesk_priority_distribution(request):
    """Ticket count by priority."""
    from helpdesk.models import Ticket

    priorities = []
    priority_choices = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    for priority, label in priority_choices:
        count = Ticket.objects.filter(is_active=True, priority=priority).count()
        priorities.append({"priority": priority, "label": label, "count": count})

    return JsonResponse({"priorities": priorities})


@login_required
def helpdesk_type_distribution(request):
    """Ticket count by type."""
    from helpdesk.models import Ticket

    types = []

    try:
        data = (
            Ticket.objects.filter(is_active=True)
            .values("ticket_type__title", "ticket_type__type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            title = item["ticket_type__title"]
            if title:
                types.append(
                    {
                        "type": title,
                        "category": item["ticket_type__type"] or "",
                        "count": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"types": types})


@login_required
def helpdesk_monthly_trend(request):
    """Ticket creation trend for the last 6 months."""
    from helpdesk.models import Ticket

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

        created = Ticket.objects.filter(
            is_active=True,
            created_date__gte=month_start,
            created_date__lte=month_end,
        ).count()

        resolved_count = Ticket.objects.filter(
            is_active=True,
            status="resolved",
            resolved_date__gte=month_start,
            resolved_date__lte=month_end,
        ).count()

        months.append(
            {
                "month": month_start.strftime("%b %Y"),
                "created": created,
                "resolved": resolved_count,
            }
        )

    return JsonResponse({"months": months})


@login_required
def helpdesk_department_breakdown(request):
    """Tickets by department (via employee owner)."""
    from helpdesk.models import Ticket

    departments = []

    try:
        data = (
            Ticket.objects.filter(is_active=True)
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                departments.append({"department": dept, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def helpdesk_overdue_tickets(request):
    """Tickets past their deadline."""
    from helpdesk.models import Ticket

    today = date.today()
    tickets = []

    try:
        qs = (
            Ticket.objects.filter(
                is_active=True,
                deadline__lt=today,
                status__in=["new", "in_progress", "on_hold"],
            )
            .select_related("employee_id", "ticket_type")
            .order_by("deadline")[:15]
        )

        for t in qs:
            emp = t.employee_id
            days_overdue = (today - t.deadline).days if t.deadline else 0
            tickets.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "ticket_id": (
                        f"{t.ticket_type.prefix}-{t.id}" if t.ticket_type else str(t.id)
                    ),
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "priority": t.priority,
                    "status": t.status,
                    "days_overdue": days_overdue,
                    "deadline": t.deadline.strftime("%b %d") if t.deadline else "—",
                }
            )
    except Exception:
        pass

    return JsonResponse({"tickets": tickets})


@login_required
def helpdesk_recent_tickets(request):
    """Most recently created tickets."""
    from helpdesk.models import Ticket

    tickets = []

    try:
        qs = (
            Ticket.objects.filter(is_active=True)
            .select_related("employee_id", "ticket_type")
            .order_by("-created_date", "-id")[:10]
        )

        for t in qs:
            emp = t.employee_id
            tickets.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "ticket_id": (
                        f"{t.ticket_type.prefix}-{t.id}" if t.ticket_type else str(t.id)
                    ),
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "priority": t.priority,
                    "status": t.status,
                    "type": t.ticket_type.title if t.ticket_type else "—",
                    "date": t.created_date.strftime("%b %d") if t.created_date else "—",
                }
            )
    except Exception:
        pass

    return JsonResponse({"tickets": tickets})


@login_required
def helpdesk_sla_compliance(request):
    """SLA compliance rate — tickets resolved within deadline."""
    from helpdesk.models import Ticket

    resolved_on_time = 0
    resolved_late = 0
    open_overdue = 0
    today = date.today()

    try:
        resolved_with_deadline = Ticket.objects.filter(
            is_active=True,
            status="resolved",
            deadline__isnull=False,
            resolved_date__isnull=False,
        )

        for t in resolved_with_deadline:
            if t.resolved_date <= t.deadline:
                resolved_on_time += 1
            else:
                resolved_late += 1

        open_overdue = Ticket.objects.filter(
            is_active=True,
            deadline__lt=today,
            status__in=["new", "in_progress", "on_hold"],
        ).count()
    except Exception:
        pass

    total_with_deadline = resolved_on_time + resolved_late
    compliance_rate = (
        round((resolved_on_time / total_with_deadline * 100), 1)
        if total_with_deadline > 0
        else 0
    )

    return JsonResponse(
        {
            "compliance_rate": compliance_rate,
            "resolved_on_time": resolved_on_time,
            "resolved_late": resolved_late,
            "open_overdue": open_overdue,
            "total_with_deadline": total_with_deadline,
        }
    )


@login_required
def helpdesk_assignee_workload(request):
    """Open ticket count per assignee."""
    from helpdesk.models import Ticket

    assignees = []

    try:
        open_tickets = Ticket.objects.filter(
            is_active=True,
            status__in=["new", "in_progress", "on_hold"],
        )

        workload = {}
        for t in open_tickets:
            for emp in t.assigned_to.all():
                if emp.id not in workload:
                    workload[emp.id] = {
                        "id": emp.id,
                        "name": emp.get_full_name(),
                        "avatar": (
                            emp.employee_profile.url if emp.employee_profile else None
                        ),
                        "count": 0,
                        "high": 0,
                    }
                workload[emp.id]["count"] += 1
                if t.priority == "high":
                    workload[emp.id]["high"] += 1

        assignees = sorted(workload.values(), key=lambda x: x["count"], reverse=True)[
            :10
        ]
    except Exception:
        pass

    return JsonResponse({"assignees": assignees})
