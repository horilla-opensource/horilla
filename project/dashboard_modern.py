"""
Modern Project dashboard views — KPI summary + ApexCharts.

Accessible at /project/dashboard/
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render


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
def modern_project_dashboard(request):
    return render(request, "project/dashboard_modern.html")


@login_required
def project_kpi_data(request):
    from project.models import Project, Task

    total = Project.objects.count()
    active = Project.objects.filter(status="in_progress").count()
    completed = Project.objects.filter(status="completed").count()
    on_hold = Project.objects.filter(status="on_hold").count()
    overdue = (
        Project.objects.filter(end_date__lt=date.today())
        .exclude(status__in=["completed", "cancelled", "expired"])
        .count()
    )

    total_tasks = Task.objects.count()
    tasks_done = Task.objects.filter(status="completed").count()
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
def project_status_distribution(request):
    from project.models import Project

    qs = Project.objects.values("status").annotate(count=Count("id"))
    labels = []
    counts = []
    label_map = {
        "new": "New",
        "in_progress": "In Progress",
        "completed": "Completed",
        "on_hold": "On Hold",
        "cancelled": "Cancelled",
        "expired": "Expired",
    }
    for row in qs:
        labels.append(label_map.get(row["status"], row["status"]))
        counts.append(row["count"])
    return JsonResponse({"labels": labels, "counts": counts})


@login_required
def project_task_status(request):
    from project.models import Task

    qs = Task.objects.values("status").annotate(count=Count("id"))
    label_map = {
        "to_do": "To Do",
        "in_progress": "In Progress",
        "completed": "Completed",
        "expired": "Expired",
    }
    labels = []
    counts = []
    for row in qs:
        labels.append(label_map.get(row["status"], row["status"]))
        counts.append(row["count"])
    return JsonResponse({"labels": labels, "counts": counts})


@login_required
def project_monthly_trend(request):
    from project.models import Project

    _, to_date = _parse_period(request)
    today = to_date
    months = []
    started = []
    completed = []
    for i in range(5, -1, -1):
        # months ago
        first = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        if first.month == 12:
            last = first.replace(day=31)
        else:
            last = first.replace(month=first.month + 1) - timedelta(days=1)
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
            "title": p.title,
            "end_date": str(p.end_date),
            "status": p.get_status_display(),
            "days_left": (p.end_date - today).days,
        }
        for p in upcoming
    ]
    return JsonResponse({"projects": data})


@login_required
def project_top_active(request):
    from project.models import Project

    projects = (
        Project.objects.filter(status="in_progress")
        .annotate(task_count=Count("task"))
        .order_by("-task_count")[:8]
    )
    data = [
        {
            "title": p.title,
            "task_count": p.task_count,
            "end_date": str(p.end_date) if p.end_date else "—",
        }
        for p in projects
    ]
    return JsonResponse({"projects": data})
