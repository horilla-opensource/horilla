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

from horilla.decorators import permission_required


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


def _period_overlap(qs, request, start_field="start_date", end_field="end_date"):
    """Restrict a queryset to rows whose [start, end] overlaps the requested period."""
    from_date, to_date = _parse_period(request)
    return qs.filter(**{f"{start_field}__lte": to_date, f"{end_field}__gte": from_date})


@login_required
@permission_required("pms.view_employeeobjective")
def pms_dashboard_view(request):
    """Render the modern PMS dashboard page."""
    return render(request, "pms/dashboard.html")


@login_required
@permission_required("pms.view_employeeobjective")
def pms_kpi_data(request):
    """Return PMS KPI summary data as JSON, scoped to objectives/feedback active in the picker range."""
    from pms.models import EmployeeKeyResult, EmployeeObjective, Feedback

    objectives = _period_overlap(
        EmployeeObjective.objects.filter(archive=False), request
    )
    key_results = _period_overlap(EmployeeKeyResult.objects.all(), request)
    feedbacks = _period_overlap(Feedback.objects.filter(archive=False), request)

    total_objectives = objectives.count()
    total_key_results = key_results.count()
    total_feedbacks = feedbacks.count()

    # Average progress
    avg_progress = objectives.aggregate(
        avg=Coalesce(Avg("progress_percentage"), 0.0, output_field=FloatField())
    )["avg"]

    # At-risk count
    at_risk = objectives.filter(status="At Risk").count()

    # Closed objectives
    closed = objectives.filter(status="Closed").count()

    completion_rate = (
        round((closed / total_objectives * 100), 1) if total_objectives > 0 else 0
    )

    # Pending feedback (not started + on track)
    pending_feedback = feedbacks.filter(status__in=["Not Started", "On Track"]).count()

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
@permission_required("pms.view_employeeobjective")
def pms_objective_status(request):
    """Objective status distribution for objectives active in the picker range."""
    from pms.models import EmployeeObjective

    objectives = _period_overlap(
        EmployeeObjective.objects.filter(archive=False), request
    )
    statuses = []

    for status, label in EmployeeObjective.STATUS_CHOICES:
        count = objectives.filter(status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
@permission_required("pms.view_employeekeyresult")
def pms_key_result_status(request):
    """Key result status distribution for KRs active in the picker range."""
    from pms.models import EmployeeKeyResult

    key_results = _period_overlap(EmployeeKeyResult.objects.all(), request)
    statuses = []

    for status, label in EmployeeKeyResult.STATUS_CHOICES:
        count = key_results.filter(status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
@permission_required("pms.view_feedback")
def pms_feedback_status(request):
    """Feedback status distribution for feedback active in the picker range."""
    from pms.models import Feedback

    feedbacks = _period_overlap(Feedback.objects.filter(archive=False), request)
    statuses = []

    for status, label in Feedback.STATUS_CHOICES:
        count = feedbacks.filter(status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
@permission_required("pms.view_employeeobjective")
def pms_department_performance(request):
    """Average objective progress by department for objectives active in the picker range."""
    from pms.models import EmployeeObjective

    departments = []

    try:
        data = (
            _period_overlap(EmployeeObjective.objects.filter(archive=False), request)
            .values(
                "employee_id__employee_work_info__department_id",
                "employee_id__employee_work_info__department_id__department",
            )
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
            dept_id = item["employee_id__employee_work_info__department_id"]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "dept_id": dept_id,
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
@permission_required("pms.view_employeeobjective")
def pms_at_risk_objectives(request):
    """Objectives that are at risk or behind, scoped to the picker range."""
    from pms.models import EmployeeObjective

    objectives = []

    try:
        qs = (
            _period_overlap(
                EmployeeObjective.objects.filter(
                    archive=False, status__in=["At Risk", "Behind"]
                ),
                request,
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
                    "avatar": emp.get_avatar() if emp else None,
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
@permission_required("pms.view_employeeobjective")
def pms_top_performers(request):
    """Top performers by objective completion and bonus points, for the picker range."""
    from employee.models import Employee
    from pms.models import EmployeeBonusPoint, EmployeeObjective

    performers = []

    try:
        # By objective progress
        data = (
            _period_overlap(EmployeeObjective.objects.filter(archive=False), request)
            .values(
                "employee_id",
                "employee_id__employee_first_name",
                "employee_id__employee_last_name",
            )
            .annotate(
                avg_progress=Avg("progress_percentage"),
                total_objectives=Count("id"),
                completed=Count("id", filter=Q(status="Closed")),
            )
            .order_by("-avg_progress")[:10]
        )

        avatar_by_employee_id = {
            emp.id: emp.get_avatar()
            for emp in Employee.objects.filter(
                id__in=[item["employee_id"] for item in data]
            )
        }

        for item in data:
            first = item["employee_id__employee_first_name"] or ""
            last = item["employee_id__employee_last_name"] or ""

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
                    "avatar": avatar_by_employee_id.get(item["employee_id"]),
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
@permission_required("pms.view_employeekeyresult")
def pms_kr_progress_overview(request):
    """Key result progress grouped by objective, for objectives active in the picker range."""
    from pms.models import EmployeeKeyResult, EmployeeObjective

    overview = []

    try:
        objectives = (
            _period_overlap(EmployeeObjective.objects.filter(archive=False), request)
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
@permission_required("pms.view_meetings")
def pms_upcoming_meetings(request):
    """PMS meetings scheduled within the selected period."""
    from pms.models import Meetings

    from_date, to_date = _parse_period(request)
    today = date.today()
    meetings = []

    try:
        qs = Meetings.objects.filter(
            date__date__gte=from_date,
            date__date__lte=to_date,
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
@permission_required("pms.view_employeeobjective")
def pms_progress_trend(request):
    """Average objective progress per month within the selected period."""
    from pms.models import EmployeeObjective

    from_date, to_date = _parse_period(request)
    months = []
    try:
        cursor = from_date.replace(day=1)
        end_marker = to_date.replace(day=1)
        while cursor <= end_marker:
            if cursor.month == 12:
                next_month = date(cursor.year + 1, 1, 1)
            else:
                next_month = date(cursor.year, cursor.month + 1, 1)
            month_end = next_month - timedelta(days=1)
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
                    "month": cursor.strftime("%b %Y"),
                    "avg_progress": round(float(avg), 1),
                    "from_date": cursor.isoformat(),
                    "to_date": month_end.isoformat(),
                }
            )
            cursor = next_month
    except Exception:
        pass
    return JsonResponse({"months": months})


@login_required
@permission_required("pms.view_feedback")
def pms_feedback_completion(request):
    """Feedback answer completion rate per feedback cycle active in the picker range."""
    from pms.models import Answer, Feedback, Question

    completions = []
    try:
        feedbacks = _period_overlap(
            Feedback.objects.filter(
                archive=False, status__in=["On Track", "Not Started"]
            ),
            request,
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
