"""
Modern Project dashboard views — KPI summary + ApexCharts.

Accessible at /project/dashboard/
"""

from collections import Counter
from datetime import date, timedelta

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from horilla.decorators import login_required
from project.cbv.cbv_decorators import is_projectmanager_or_member_or_perms

PIPELINE_STAGES = (
    ("new", _("New")),
    ("in_progress", _("In Progress")),
    ("on_hold", _("On Hold")),
    ("completed", _("Completed")),
)

TASK_STATUS_LABELS = {
    "to_do": _("To Do"),
    "in_progress": _("In Progress"),
    "completed": _("Completed"),
    "expired": _("Expired"),
}


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


def _month_bounds(today, months_ago):
    """First/last day of the month `months_ago` months before `today`."""
    year = today.year
    month = today.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    first = date(year, month, 1)
    if first.month == 12:
        last = date(first.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(first.year, first.month + 1, 1) - timedelta(days=1)
    return first, last


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_dashboard_view(request):
    return render(request, "project/dashboard.html")


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_kpi_data(request):
    """Total/Active/Completed/Overdue counts, each with a small trend delta."""
    from project.models import Project

    today = date.today()
    this_month_start, this_month_end = _month_bounds(today, 0)
    last_month_start, last_month_end = _month_bounds(today, 1)

    active_qs = Project.objects.filter(is_active=True)
    total = active_qs.count()
    active = active_qs.filter(status="in_progress").count()
    completed = active_qs.filter(status="completed").count()
    overdue = (
        active_qs.filter(end_date__lt=today)
        .exclude(status__in=["completed", "cancelled", "expired"])
        .count()
    )

    total_new_this_month = active_qs.filter(
        created_at__date__gte=this_month_start, created_at__date__lte=this_month_end
    ).count()
    active_started_this_month = active_qs.filter(
        status="in_progress",
        start_date__gte=this_month_start,
        start_date__lte=this_month_end,
    ).count()
    completed_this_month = active_qs.filter(
        status="completed",
        end_date__gte=this_month_start,
        end_date__lte=this_month_end,
    ).count()
    completed_last_month = active_qs.filter(
        status="completed",
        end_date__gte=last_month_start,
        end_date__lte=last_month_end,
    ).count()
    completed_change_pct = 0
    if completed_last_month > 0:
        completed_change_pct = round(
            ((completed_this_month - completed_last_month) / completed_last_month)
            * 100,
            1,
        )
    overdue_new_this_month = (
        active_qs.filter(
            end_date__gte=this_month_start,
            end_date__lte=min(this_month_end, today),
        )
        .exclude(status__in=["completed", "cancelled", "expired"])
        .count()
    )

    return JsonResponse(
        {
            "total_projects": total,
            "active_projects": active,
            "completed_projects": completed,
            "overdue_projects": overdue,
            "total_new_this_month": total_new_this_month,
            "active_started_this_month": active_started_this_month,
            "completed_this_month": completed_this_month,
            "completed_change_pct": completed_change_pct,
            "overdue_new_this_month": overdue_new_this_month,
        }
    )


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_status_pipeline(request):
    """Live New -> In Progress -> On Hold -> Completed stage tracker.

    Reflects the current state of every active project (not scoped to a
    date period, unlike the trend chart) so the pipeline always shows
    where things stand right now.
    """
    from project.models import Project

    qs = Project.objects.filter(is_active=True)
    # HorillaCompanyManager's get_queryset() applies .distinct() whenever the
    # company OR-filter is active; chaining .values("status").annotate(Count())
    # on top of that collapses to one row per Project instead of one row per
    # status (Django groups by the queryset's already-selected columns, not
    # just "status"), so every status count comes back as 1. Counting in
    # Python over a plain column pull sidesteps that entirely -- but only if
    # "pk" is pulled alongside the field: pk uniqueness is what actually
    # forces SELECT DISTINCT to keep every row. (Pulling "status" alone
    # happens to work today only because Project has Meta.ordering, which
    # Django folds into the DISTINCT column list to satisfy ORDER BY --
    # remove that ordering and this would silently start undercounting.)
    counts = Counter(status for _pk, status in qs.values_list("pk", "status"))
    stages = [
        {"status": key, "label": str(label), "count": counts.get(key, 0)}
        for key, label in PIPELINE_STAGES
    ]
    return JsonResponse({"stages": stages, "total": qs.count()})


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_task_status(request):
    """Task status breakdown across every active task."""
    from project.models import Task

    qs = Task.objects.filter(is_active=True)
    # See project_status_pipeline for why this counts in Python (rather than
    # via .values("status").annotate(Count())) and pulls "pk" alongside
    # "status" rather than relying on Task's incidental Meta.ordering.
    counts = Counter(status for _pk, status in qs.values_list("pk", "status"))
    labels, counts_list, keys = [], [], []
    for key, label in TASK_STATUS_LABELS.items():
        count = counts.get(key, 0)
        if count:
            labels.append(str(label))
            counts_list.append(count)
            keys.append(key)
    return JsonResponse(
        {"labels": labels, "counts": counts_list, "keys": keys, "total": qs.count()}
    )


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_monthly_trend(request):
    """Projects started vs. completed vs. overdue, over the trailing 6 months."""
    from project.models import Project

    _, to_date = _parse_period(request)
    today = to_date
    months, started, completed, overdue = [], [], [], []
    for i in range(5, -1, -1):
        first, last = _month_bounds(today, i)
        months.append(first.strftime("%b %Y"))
        started.append(
            Project.objects.filter(start_date__gte=first, start_date__lte=last).count()
        )
        completed.append(
            Project.objects.filter(
                status="completed", end_date__gte=first, end_date__lte=last
            ).count()
        )
        overdue.append(
            Project.objects.filter(end_date__gte=first, end_date__lte=last)
            .exclude(status__in=["completed", "cancelled", "expired"])
            .count()
        )
    return JsonResponse(
        {
            "months": months,
            "started": started,
            "completed": completed,
            "overdue": overdue,
        }
    )


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_top_active(request):
    """Top in-progress projects by task count, for pairing with Task Status."""
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


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_top_contributors(request):
    """Top employees by tasks completed this period."""
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    contributors = []
    try:
        data = (
            Employee.objects.filter(
                tasks__status="completed",
                tasks__end_date__gte=from_date,
                tasks__end_date__lte=to_date,
            )
            .annotate(completed_count=Count("tasks", distinct=True))
            .filter(completed_count__gt=0)
            .order_by("-completed_count")[:10]
        )
        for emp in data:
            contributors.append(
                {
                    "id": emp.id,
                    "name": emp.get_full_name(),
                    "avatar": emp.get_avatar(),
                    "completed_count": emp.completed_count,
                }
            )
    except Exception:
        pass
    return JsonResponse(
        {"contributors": contributors, "month": to_date.strftime("%B %Y")}
    )


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_task_deadlines(request):
    """Tasks due within the next 14 days, plus tasks already overdue."""
    from project.models import Task

    today = date.today()
    open_tasks = Task.objects.filter(is_active=True).exclude(status__in=["completed"])

    upcoming = open_tasks.filter(
        end_date__gte=today, end_date__lte=today + timedelta(days=14)
    ).order_by("end_date")[:8]
    overdue = open_tasks.filter(end_date__lt=today).order_by("end_date")[:8]

    def _serialize(task, days_left):
        return {
            "id": task.id,
            "title": task.title,
            "project": task.project.title if task.project_id else "—",
            "project_id": task.project_id,
            "end_date": str(task.end_date) if task.end_date else "—",
            "days_left": days_left,
        }

    upcoming_data = [_serialize(t, (t.end_date - today).days) for t in upcoming]
    overdue_data = [_serialize(t, (t.end_date - today).days) for t in overdue]

    return JsonResponse({"upcoming": upcoming_data, "overdue": overdue_data})
