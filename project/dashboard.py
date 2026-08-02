"""
Modern Project dashboard views — KPI summary + ApexCharts.

Accessible at /project/dashboard/
"""

from datetime import date, timedelta

from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from horilla.decorators import login_required
from project.cbv.cbv_decorators import is_projectmanager_or_member_or_perms


def _parse_period(request):
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
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_dashboard_view(request):
    return render(request, "project/dashboard.html")


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_kpi_data(request):
    from project.models import Project, Task

    from_date, to_date = _parse_period(request)
    period_tasks = Task.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )

    active_qs = Project.objects.filter(is_active=True)
    total = active_qs.count()
    active = active_qs.filter(status="in_progress").count()
    completed = active_qs.filter(status="completed").count()
    on_hold = active_qs.filter(status="on_hold").count()
    overdue = (
        active_qs.filter(end_date__lt=date.today())
        .exclude(status__in=["completed", "cancelled", "expired"])
        .count()
    )

    total_tasks = period_tasks.count()
    tasks_done = period_tasks.filter(status="completed").count()
    task_completion_rate = (
        round(tasks_done / total_tasks * 100, 1) if total_tasks else 0
    )

    return JsonResponse(
        {
            "total_projects": total,
            "active_projects": active,
            "completed_projects": completed,
            "on_hold_projects": on_hold,
            "overdue_projects": overdue,
            "total_tasks": total_tasks,
            "tasks_done": tasks_done,
            "task_completion_rate": task_completion_rate,
        }
    )


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_status_distribution(request):
    """Project status breakdown, for projects created in the picker range."""
    from project.models import Project

    from_date, to_date = _parse_period(request)
    qs = (
        Project.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
        .order_by()
        .values("status")
        .annotate(count=Count("id"))
    )
    labels = []
    counts = []
    keys = []
    label_map = {
        "new": _("New"),
        "in_progress": _("In Progress"),
        "completed": _("Completed"),
        "on_hold": _("On Hold"),
        "cancelled": _("Cancelled"),
        "expired": _("Expired"),
    }
    for row in qs:
        labels.append(label_map.get(row["status"], row["status"]))
        counts.append(row["count"])
        keys.append(row["status"])
    return JsonResponse({"labels": labels, "counts": counts, "keys": keys})


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_task_status(request):
    """Task status breakdown, for tasks created in the picker range."""
    from project.models import Task

    from_date, to_date = _parse_period(request)
    qs = (
        Task.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
        .order_by()
        .values("status")
        .annotate(count=Count("id"))
    )
    label_map = {
        "to_do": _("To Do"),
        "in_progress": _("In Progress"),
        "completed": _("Completed"),
        "expired": _("Expired"),
    }
    labels = []
    counts = []
    keys = []
    for row in qs:
        labels.append(label_map.get(row["status"], row["status"]))
        counts.append(row["count"])
        keys.append(row["status"])
    return JsonResponse({"labels": labels, "counts": counts, "keys": keys})


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_monthly_trend(request):
    from project.models import Project

    _, to_date = _parse_period(request)
    today = to_date
    months = []
    started = []
    completed = []
    for i in range(5, -1, -1):
        # months ago
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        first = date(year, month, 1)
        if first.month == 12:
            last = date(first.year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(first.year, first.month + 1, 1) - timedelta(days=1)
        months.append(first.strftime("%b %Y"))
        started.append(
            Project.objects.filter(start_date__gte=first, start_date__lte=last).count()
        )
        completed.append(
            Project.objects.filter(
                status="completed", end_date__gte=first, end_date__lte=last
            ).count()
        )
    return JsonResponse({"months": months, "started": started, "completed": completed})


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_upcoming_deadlines(request):
    from project.models import Project

    today = date.today()
    upcoming = (
        Project.objects.filter(
            end_date__gte=today,
            end_date__lte=today + timedelta(days=30),
        )
        .exclude(status__in=["completed", "cancelled", "expired"])
        .order_by("end_date")[:10]
    )
    data = [
        {
            "id": p.id,
            "title": p.title,
            "end_date": str(p.end_date),
            "status": p.get_status_display(),
            "days_left": (p.end_date - today).days,
        }
        for p in upcoming
    ]
    return JsonResponse({"projects": data})


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_top_active(request):
    from project.models import Project

    projects = (
        Project.objects.filter(status="in_progress")
        .annotate(task_count=Count("task"))
        .order_by("-task_count")[:8]
    )
    data = [
        {
            "id": p.id,
            "title": p.title,
            "task_count": p.task_count,
            "end_date": str(p.end_date) if p.end_date else "—",
        }
        for p in projects
    ]
    return JsonResponse({"projects": data})
