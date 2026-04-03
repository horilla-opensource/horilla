"""
Modern onboarding dashboard views — KPI summary + ApexCharts.

Accessible at /onboarding/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
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
def modern_onboarding_dashboard(request):
    """Render the modern onboarding dashboard page."""
    return render(request, "onboarding/dashboard_modern.html")


@login_required
def onboarding_kpi_data(request):
    """Return onboarding KPI summary data as JSON."""
    from onboarding.models import CandidateStage, CandidateTask
    from recruitment.models import Candidate, Recruitment

    total_candidates = Candidate.objects.filter(start_onboard=True).count()
    active_recruitments = Recruitment.objects.filter(
        closed=False, is_active=True
    ).count()

    # Task stats
    total_tasks = CandidateTask.objects.all().count()
    completed_tasks = CandidateTask.objects.filter(status="done").count()
    stuck_tasks = CandidateTask.objects.filter(status="stuck").count()
    task_completion = (
        round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    )

    # Candidates who completed onboarding (on final stage)
    completed_onboarding = CandidateStage.objects.filter(
        onboarding_stage_id__is_final_stage=True,
    ).count()

    # Candidates in progress (not on final stage)
    in_progress = total_candidates - completed_onboarding

    return JsonResponse(
        {
            "total_candidates": total_candidates,
            "active_recruitments": active_recruitments,
            "completed_onboarding": completed_onboarding,
            "in_progress": in_progress,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "stuck_tasks": stuck_tasks,
            "task_completion": task_completion,
        }
    )


@login_required
def onboarding_stage_distribution(request):
    """Candidates by onboarding stage."""
    from onboarding.models import CandidateStage, OnboardingStage

    stages = []

    try:
        stage_qs = OnboardingStage.objects.all().order_by("sequence")
        for stage in stage_qs:
            count = CandidateStage.objects.filter(onboarding_stage_id=stage).count()
            if count > 0:
                stages.append(
                    {
                        "stage": stage.stage_title,
                        "count": count,
                        "is_final": stage.is_final_stage,
                        "recruitment": (
                            stage.recruitment_id.title if stage.recruitment_id else "—"
                        ),
                    }
                )
    except Exception:
        pass

    return JsonResponse({"stages": stages})


@login_required
def onboarding_task_status(request):
    """Task status breakdown."""
    from onboarding.models import CandidateTask

    statuses = []
    task_choices = [
        ("todo", "Todo"),
        ("scheduled", "Scheduled"),
        ("ongoing", "Ongoing"),
        ("stuck", "Stuck"),
        ("done", "Done"),
    ]

    for status, label in task_choices:
        count = CandidateTask.objects.filter(status=status).count()
        statuses.append({"status": status, "label": label, "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def onboarding_by_recruitment(request):
    """Candidates onboarding per recruitment."""
    from recruitment.models import Candidate, Recruitment

    recruitments = []

    try:
        data = (
            Candidate.objects.filter(start_onboard=True)
            .values("recruitment_id__title")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            title = item["recruitment_id__title"]
            if title:
                recruitments.append({"recruitment": title, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"recruitments": recruitments})


@login_required
def onboarding_by_job_position(request):
    """Candidates onboarding per job position."""
    from recruitment.models import Candidate

    positions = []

    try:
        data = (
            Candidate.objects.filter(start_onboard=True)
            .values("job_position_id__job_position")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            pos = item["job_position_id__job_position"]
            if pos:
                positions.append({"position": pos, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"positions": positions})


@login_required
def onboarding_candidates_list(request):
    """Current onboarding candidates with progress."""
    from onboarding.models import CandidateStage, CandidateTask
    from recruitment.models import Candidate

    candidates = []

    try:
        qs = (
            Candidate.objects.filter(start_onboard=True)
            .select_related("recruitment_id", "job_position_id", "onboarding_stage")
            .order_by("-id")[:15]
        )

        for c in qs:
            stage_name = "—"
            try:
                cs = c.onboarding_stage
                stage_name = (
                    cs.onboarding_stage_id.stage_title
                    if cs and cs.onboarding_stage_id
                    else "—"
                )
            except Exception:
                pass

            # Task progress
            total = CandidateTask.objects.filter(candidate_id=c).count()
            done = CandidateTask.objects.filter(candidate_id=c, status="done").count()
            progress = round((done / total * 100)) if total > 0 else 0

            candidates.append(
                {
                    "id": c.id,
                    "name": c.name or "—",
                    "profile": c.profile.url if c.profile else None,
                    "recruitment": c.recruitment_id.title if c.recruitment_id else "—",
                    "position": (
                        c.job_position_id.job_position if c.job_position_id else "—"
                    ),
                    "stage": stage_name,
                    "progress": progress,
                    "tasks_done": done,
                    "tasks_total": total,
                }
            )
    except Exception:
        pass

    return JsonResponse({"candidates": candidates})


@login_required
def onboarding_task_managers(request):
    """Task assignment by manager (logged-in user's tasks)."""
    from onboarding.models import CandidateTask, OnboardingTask

    tasks = []

    try:
        user_emp = getattr(request.user, "employee_get", None)
        if user_emp:
            task_qs = OnboardingTask.objects.filter(
                employee_id=user_emp,
            ).order_by("stage_id__sequence")

            for task in task_qs[:10]:
                total = CandidateTask.objects.filter(onboarding_task_id=task).count()
                done = CandidateTask.objects.filter(
                    onboarding_task_id=task, status="done"
                ).count()
                stuck = CandidateTask.objects.filter(
                    onboarding_task_id=task, status="stuck"
                ).count()

                tasks.append(
                    {
                        "title": task.task_title,
                        "stage": task.stage_id.stage_title if task.stage_id else "—",
                        "total": total,
                        "done": done,
                        "stuck": stuck,
                        "progress": round((done / total * 100)) if total > 0 else 0,
                    }
                )
    except Exception:
        pass

    return JsonResponse({"tasks": tasks})


@login_required
def onboarding_completion_trend(request):
    """Monthly onboarding completions for the last 6 months."""
    from onboarding.models import CandidateStage

    _, to_date = _parse_period(request)
    today = to_date
    months = []
    try:
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
            count = CandidateStage.objects.filter(
                onboarding_end_date__gte=month_start,
                onboarding_end_date__lte=month_end,
            ).count()
            months.append({"month": month_start.strftime("%b %Y"), "count": count})
    except Exception:
        pass
    return JsonResponse({"months": months})


@login_required
def onboarding_portal_status(request):
    """Portal access status for onboarding candidates."""
    from onboarding.models import OnboardingPortal

    portals = []
    try:
        qs = OnboardingPortal.objects.select_related("candidate_id").order_by("-count")[
            :15
        ]
        for p in qs:
            cand = p.candidate_id
            portals.append(
                {
                    "id": cand.id if cand else None,
                    "name": cand.name if cand else "—",
                    "used": p.used,
                    "visits": p.count,
                }
            )
    except Exception:
        pass
    return JsonResponse({"portals": portals})
