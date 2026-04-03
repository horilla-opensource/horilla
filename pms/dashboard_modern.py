"""
Modern PMS (Performance Management) dashboard views — KPI summary + ApexCharts.

Accessible at /pms/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, FloatField, Q, Sum
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
def modern_pms_dashboard(request):
    """Render the modern PMS dashboard page."""
    return render(request, "pms/dashboard_modern.html")


@login_required
def pms_kpi_data(request):
    """Return PMS KPI summary data as JSON."""
    from pms.models import EmployeeKeyResult, EmployeeObjective, Feedback

    total_objectives = EmployeeObjective.objects.filter(archive=False).count()
    total_key_results = EmployeeKeyResult.objects.all().count()
    total_feedbacks = Feedback.objects.filter(archive=False).count()

    # Average progress
    avg_progress = EmployeeObjective.objects.filter(archive=False).aggregate(
        avg=Coalesce(Avg("progress_percentage"), 0.0, output_field=FloatField())
    )["avg"]

    # At-risk count
    at_risk = EmployeeObjective.objects.filter(archive=False, status="At Risk").count()

    # Closed objectives
    closed = EmployeeObjective.objects.filter(archive=False, status="Closed").count()

    completion_rate = (
        round((closed / total_objectives * 100), 1) if total_objectives > 0 else 0
    )

    # Pending feedback (not started + on track)
    pending_feedback = Feedback.objects.filter(
        archive=False, status__in=["Not Started", "On Track"]
    ).count()

    return JsonResponse(
        {
            "total_objectives": total_objectives,
            "total_key_results": total_key_results,
            "total_feedbacks": total_feedbacks,
            "avg_progress": round(float(avg_progress), 1),
            "at_risk": at_risk,
            "closed": closed,
            "completion_rate": completion_rate,
            "pending_feedback": pending_feedback,
        }
    )


@login_required
def pms_objective_status(request):
    """Objective status distribution."""
    from pms.models import EmployeeObjective

    statuses = []

    for status, label in EmployeeObjective.STATUS_CHOICES:
        count = EmployeeObjective.objects.filter(archive=False, status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def pms_key_result_status(request):
    """Key result status distribution."""
    from pms.models import EmployeeKeyResult

    statuses = []

    for status, label in EmployeeKeyResult.STATUS_CHOICES:
        count = EmployeeKeyResult.objects.filter(status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def pms_feedback_status(request):
    """Feedback status distribution."""
    from pms.models import Feedback

    statuses = []

    for status, label in Feedback.STATUS_CHOICES:
        count = Feedback.objects.filter(archive=False, status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def pms_department_performance(request):
    """Average objective progress by department."""
    from pms.models import EmployeeObjective

    departments = []

    try:
        data = (
            EmployeeObjective.objects.filter(archive=False)
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(
                avg_progress=Avg("progress_percentage"),
                total=Count("id"),
                closed=Count("id", filter=Q(status="Closed")),
                at_risk=Count("id", filter=Q(status="At Risk")),
            )
            .order_by("-avg_progress")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "avg_progress": round(float(item["avg_progress"] or 0), 1),
                        "total": item["total"],
                        "closed": item["closed"],
                        "at_risk": item["at_risk"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def pms_at_risk_objectives(request):
    """Objectives that are at risk or behind."""
    from pms.models import EmployeeObjective

    objectives = []

    try:
        qs = (
            EmployeeObjective.objects.filter(
                archive=False, status__in=["At Risk", "Behind"]
            )
            .select_related("employee_id", "objective_id")
            .order_by("end_date")[:15]
        )

        today = date.today()
        for obj in qs:
            emp = obj.employee_id
            days_left = (obj.end_date - today).days if obj.end_date else None
            objectives.append(
                {
                    "id": obj.id,
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "objective": (
                        obj.objective_id.title
                        if obj.objective_id
                        else obj.objective or "—"
                    ),
                    "status": obj.status,
                    "progress": obj.progress_percentage,
                    "days_left": days_left,
                    "end_date": obj.end_date.strftime("%b %d") if obj.end_date else "—",
                }
            )
    except Exception:
        pass

    return JsonResponse({"objectives": objectives})


@login_required
def pms_top_performers(request):
    """Top performers by objective completion and bonus points."""
    from pms.models import EmployeeBonusPoint, EmployeeObjective

    performers = []

    try:
        # By objective progress
        data = (
            EmployeeObjective.objects.filter(archive=False)
            .values(
                "employee_id",
                "employee_id__employee_first_name",
                "employee_id__employee_last_name",
                "employee_id__employee_profile",
            )
            .annotate(
                avg_progress=Avg("progress_percentage"),
                total_objectives=Count("id"),
                completed=Count("id", filter=Q(status="Closed")),
            )
            .order_by("-avg_progress")[:10]
        )

        for item in data:
            first = item["employee_id__employee_first_name"] or ""
            last = item["employee_id__employee_last_name"] or ""
            avatar = item["employee_id__employee_profile"]

            # Get bonus points
            bonus = 0
            try:
                bonus = EmployeeBonusPoint.objects.filter(
                    employee_id=item["employee_id"]
                ).aggregate(total=Coalesce(Sum("bonus_point"), 0))["total"]
            except Exception:
                pass

            performers.append(
                {
                    "id": item["employee_id"],
                    "name": f"{first} {last}".strip(),
                    "avatar": f"/media/{avatar}" if avatar else None,
                    "avg_progress": round(float(item["avg_progress"] or 0), 1),
                    "objectives": item["total_objectives"],
                    "completed": item["completed"],
                    "bonus_points": bonus,
                }
            )
    except Exception:
        pass

    return JsonResponse({"performers": performers})


@login_required
def pms_kr_progress_overview(request):
    """Key result progress grouped by objective."""
    from pms.models import EmployeeKeyResult, EmployeeObjective

    overview = []

    try:
        objectives = (
            EmployeeObjective.objects.filter(archive=False)
            .select_related("objective_id")
            .order_by("-progress_percentage")[:10]
        )

        for obj in objectives:
            krs = EmployeeKeyResult.objects.filter(employee_objective_id=obj).values(
                "key_result",
                "progress_percentage",
                "status",
                "current_value",
                "target_value",
            )

            kr_list = []
            for kr in krs:
                kr_list.append(
                    {
                        "title": kr["key_result"],
                        "progress": kr["progress_percentage"],
                        "status": kr["status"],
                        "current": kr["current_value"],
                        "target": kr["target_value"],
                    }
                )

            emp = obj.employee_id
            overview.append(
                {
                    "objective": (
                        obj.objective_id.title
                        if obj.objective_id
                        else obj.objective or "—"
                    ),
                    "employee": emp.get_full_name() if emp else "—",
                    "progress": obj.progress_percentage,
                    "status": obj.status,
                    "key_results": kr_list,
                }
            )
    except Exception:
        pass

    return JsonResponse({"overview": overview})


@login_required
def pms_upcoming_meetings(request):
    """Upcoming PMS meetings in the next 14 days."""
    from pms.models import Meetings

    today = date.today()
    end = today + timedelta(days=14)
    meetings = []

    try:
        qs = Meetings.objects.filter(
            date__date__gte=today,
            date__date__lte=end,
        ).order_by("date")[:10]

        for m in qs:
            meetings.append(
                {
                    "id": m.id,
                    "title": m.title,
                    "date": m.date.strftime("%b %d"),
                    "time": m.date.strftime("%I:%M %p"),
                    "days_away": (m.date.date() - today).days,
                    "attendees": m.employee_id.count() + m.manager.count(),
                }
            )
    except Exception:
        pass

    return JsonResponse({"meetings": meetings})


@login_required
def pms_progress_trend(request):
    """Average objective progress over the last 6 months."""
    from pms.models import EmployeeObjective

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
            avg = EmployeeObjective.objects.filter(
                archive=False,
                updated_at__lte=month_end,
            ).aggregate(
                avg=Coalesce(Avg("progress_percentage"), 0.0, output_field=FloatField())
            )[
                "avg"
            ]
            months.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "avg_progress": round(float(avg), 1),
                }
            )
    except Exception:
        pass
    return JsonResponse({"months": months})


@login_required
def pms_feedback_completion(request):
    """Feedback answer completion rate per active feedback cycle."""
    from pms.models import Answer, Feedback, Question

    completions = []
    try:
        feedbacks = Feedback.objects.filter(
            archive=False, status__in=["On Track", "Not Started"]
        )
        for fb in feedbacks[:8]:
            total_questions = Question.objects.filter(
                template_id=fb.question_template_id
            ).count()
            respondents = (
                fb.colleague_id.count()
                + fb.subordinate_id.count()
                + fb.others_id.count()
                + 1
            )
            expected = total_questions * respondents
            actual = Answer.objects.filter(feedback_id=fb).count()
            rate = round((actual / expected * 100), 1) if expected > 0 else 0
            completions.append(
                {
                    "cycle": fb.review_cycle,
                    "employee": (
                        fb.employee_id.get_full_name() if fb.employee_id else "—"
                    ),
                    "expected": expected,
                    "actual": actual,
                    "rate": rate,
                }
            )
    except Exception:
        pass
    return JsonResponse({"completions": completions})
