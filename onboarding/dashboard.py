"""
Modern onboarding dashboard views — KPI summary + ApexCharts.

Accessible at /onboarding/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from horilla.methods import handle_no_permission


def _has_onboarding_permission(request):
    """Return True if the user may access the onboarding dashboard."""
    user = request.user
    if user.is_superuser or user.has_perm("onboarding.view_onboardingstage"):
        return True
    try:
        employee = user.employee_get
        return (
            employee.onboardingstage_set.all().exists()
            or employee.onboarding_task.all().exists()
        )
    except Exception:
        return False


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


def _onboarding_candidates_in_period(request):
    """Return Candidate queryset (start_onboard=True) filtered to the requested period."""
    from recruitment.models import Candidate

    from_date, to_date = _parse_period(request)
    return Candidate.objects.filter(
        start_onboard=True,
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )


@login_required
def onboarding_dashboard_view(request):
    """Render the modern onboarding dashboard page."""
    if not _has_onboarding_permission(request):
        return handle_no_permission(request)
    return render(request, "onboarding/dashboard.html")


@login_required
def onboarding_kpi_data(request):
    """Return onboarding KPI summary data as JSON."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateStage, CandidateTask
    from recruitment.models import Recruitment

    from_date, to_date = _parse_period(request)
    period_candidates = _onboarding_candidates_in_period(request)
    total_candidates = period_candidates.count()
    active_recruitments = Recruitment.objects.filter(
        closed=False, is_active=True
    ).count()

    # Task stats — restrict to tasks belonging to candidates in the selected period
    period_tasks = CandidateTask.objects.filter(candidate_id__in=period_candidates)
    total_tasks = period_tasks.count()
    completed_tasks = period_tasks.filter(status="done").count()
    stuck_tasks = period_tasks.filter(status="stuck").count()
    task_completion = (
        round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    )

    # Candidates who completed onboarding (reached the final stage) during the
    # selected period, scoped by onboarding_end_date -- the date the final
    # stage was actually reached -- not by candidate_id__in=period_candidates
    # (creation date), since a candidate can be created in one period and
    # only finish onboarding in a later one.
    completed_onboarding = CandidateStage.objects.filter(
        onboarding_stage_id__is_final_stage=True,
        onboarding_end_date__gte=from_date,
        onboarding_end_date__lte=to_date,
    ).count()

    # Of this period's own new onboarding candidates, how many are still
    # in progress (not yet on the final stage) -- kept separate from
    # `completed_onboarding` above so this always stays <= total_candidates.
    completed_of_period_starters = CandidateStage.objects.filter(
        onboarding_stage_id__is_final_stage=True,
        candidate_id__in=period_candidates,
    ).count()
    in_progress = total_candidates - completed_of_period_starters

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
            # Echoed back so the "Onboarding" card's click-through can
            # filter to the exact same period the count above was
            # computed from, instead of showing all-time candidates.
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
def onboarding_stage_distribution(request):
    """Candidates grouped by onboarding stage name -- one tile per stage.

    OnboardingStage rows are per-recruitment (every recruitment seeds its
    own stage set -- see recruitment_expansion.py), so grouping by the
    stage *row*, as this endpoint used to, renders one duplicate tile per
    recruitment that happens to share a stage name (e.g. "Initial"
    appearing once per recruitment instead of once, total). Grouping by
    stage_title instead collapses that back to one tile per distinct step
    (same fix as offboarding_pipeline in offboarding/dashboard.py).

    This also sidesteps a second, sneakier bug: a plain
    .values_list("onboarding_stage_id__stage_title", flat=True) is NOT
    safe here either. HorillaCompanyManager.get_queryset() forces
    .distinct() under company scoping, which Django compiles as a real SQL
    `SELECT DISTINCT title`, silently deduplicating by VALUE rather than
    by row the moment two different CandidateStage rows share a title --
    undercounting exactly the case this fix is meant to aggregate
    correctly. Pulling `pk` alongside every field defeats that, since pk
    uniqueness keeps each row distinct regardless of which other columns
    repeat.
    """
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateStage

    period_candidates = _onboarding_candidates_in_period(request)
    rows = CandidateStage.objects.filter(
        candidate_id__in=period_candidates
    ).values_list(
        "pk",
        "onboarding_stage_id",
        "onboarding_stage_id__stage_title",
        "onboarding_stage_id__sequence",
        "onboarding_stage_id__is_final_stage",
        "onboarding_stage_id__recruitment_id__title",
    )

    groups = {}
    for _pk, stage_id, title, sequence, is_final, recruitment_title in rows:
        sequence = sequence if sequence is not None else 0
        group = groups.setdefault(
            title,
            {
                "id": stage_id,
                "stage": title,
                "count": 0,
                "is_final": False,
                "sequence": sequence,
                "recruitments": set(),
            },
        )
        group["count"] += 1
        group["is_final"] = group["is_final"] or bool(is_final)
        group["sequence"] = min(group["sequence"], sequence)
        if recruitment_title:
            group["recruitments"].add(recruitment_title)

    stages = [
        {
            "id": group["id"],
            "stage": group["stage"],
            "count": group["count"],
            "is_final": group["is_final"],
            "recruitment": (
                next(iter(group["recruitments"]))
                if len(group["recruitments"]) == 1
                else (
                    f"{len(group['recruitments'])} recruitments"
                    if group["recruitments"]
                    else "—"
                )
            ),
        }
        for group in sorted(groups.values(), key=lambda g: g["sequence"])
    ]

    return JsonResponse({"stages": stages})


@login_required
def onboarding_task_status(request):
    """Task status breakdown."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateTask

    period_candidates = _onboarding_candidates_in_period(request)
    period_tasks = CandidateTask.objects.filter(candidate_id__in=period_candidates)

    statuses = []
    task_choices = [
        ("todo", _("Todo")),
        ("scheduled", _("Scheduled")),
        ("ongoing", _("Ongoing")),
        ("stuck", _("Stuck")),
        ("done", _("Done")),
    ]

    for status, label in task_choices:
        count = period_tasks.filter(status=status).count()
        statuses.append({"status": status, "label": label, "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def onboarding_by_recruitment(request):
    """Candidates onboarding per recruitment."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    recruitments = []

    try:
        data = (
            _onboarding_candidates_in_period(request)
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
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    positions = []

    try:
        data = (
            _onboarding_candidates_in_period(request)
            .values("job_position_id", "job_position_id__job_position")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            pos = item["job_position_id__job_position"]
            pos_id = item["job_position_id"]
            if pos:
                positions.append(
                    {"position": pos, "position_id": pos_id, "count": item["count"]}
                )
    except Exception:
        pass

    return JsonResponse({"positions": positions})


@login_required
def onboarding_candidates_list(request):
    """Current onboarding candidates with progress."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateTask

    candidates = []

    try:
        qs = (
            _onboarding_candidates_in_period(request)
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
    """Task assignment by manager (logged-in user's tasks), scoped to the selected period."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateTask, OnboardingTask

    tasks = []

    try:
        user_emp = getattr(request.user, "employee_get", None)
        if user_emp:
            period_candidates = _onboarding_candidates_in_period(request)
            task_qs = OnboardingTask.objects.filter(
                employee_id=user_emp,
            ).order_by("stage_id__sequence")

            for task in task_qs[:10]:
                ct_base = CandidateTask.objects.filter(
                    onboarding_task_id=task,
                    candidate_id__in=period_candidates,
                )
                total = ct_base.count()
                if total == 0:
                    continue
                done = ct_base.filter(status="done").count()
                stuck = ct_base.filter(status="stuck").count()

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
    """Monthly onboarding completions within the selected period."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import CandidateStage

    from_date, to_date = _parse_period(request)
    months = []
    try:
        cursor = from_date.replace(day=1)
        end_marker = to_date.replace(day=1)
        while cursor <= end_marker:
            if cursor.month == 12:
                next_month = cursor.replace(year=cursor.year + 1, month=1)
            else:
                next_month = cursor.replace(month=cursor.month + 1)
            month_end = next_month - timedelta(days=1)
            count = CandidateStage.objects.filter(
                onboarding_end_date__gte=cursor,
                onboarding_end_date__lte=month_end,
            ).count()
            months.append({"month": cursor.strftime("%b %Y"), "count": count})
            cursor = next_month
    except Exception:
        pass
    return JsonResponse({"months": months})


@login_required
def onboarding_portal_status(request):
    """Portal access status for onboarding candidates within the selected period."""
    if not _has_onboarding_permission(request):
        return JsonResponse({"no_permission": True})
    from onboarding.models import OnboardingPortal

    portals = []
    try:
        period_candidates = _onboarding_candidates_in_period(request)
        qs = (
            OnboardingPortal.objects.filter(candidate_id__in=period_candidates)
            .select_related("candidate_id")
            .order_by("-count")[:15]
        )
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
