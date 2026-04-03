"""
Modern offboarding dashboard views — KPI summary + ApexCharts.

Accessible at /offboarding/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.apps import apps
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
def modern_offboarding_dashboard(request):
    """Render the modern offboarding dashboard page."""
    return render(request, "offboarding/dashboard_modern.html")


@login_required
def offboarding_kpi_data(request):
    """Return offboarding KPI summary data as JSON."""
    from employee.models import Employee
    from offboarding.models import EmployeeTask, OffboardingEmployee, ResignationLetter

    employees = Employee.objects.filter(is_active=True).count()
    total_offboarding = OffboardingEmployee.objects.all().count()
    archived = OffboardingEmployee.objects.filter(stage_id__type="archived").count()

    exit_ratio = round((archived / employees * 100), 1) if employees > 0 else 0

    # Resignation stats
    pending_resignations = ResignationLetter.objects.filter(status="requested").count()
    approved_resignations = ResignationLetter.objects.filter(status="approved").count()

    # Task completion
    total_tasks = EmployeeTask.objects.all().count()
    completed_tasks = EmployeeTask.objects.filter(status="completed").count()
    task_completion = (
        round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    )

    # Active offboarding (not archived)
    active_offboarding = OffboardingEmployee.objects.exclude(
        stage_id__type="archived"
    ).count()

    # Notice periods ending soon (next 7 days)
    today = date.today()
    notice_ending_soon = (
        OffboardingEmployee.objects.filter(
            notice_period_ends__gte=today,
            notice_period_ends__lte=today + timedelta(days=7),
        )
        .exclude(stage_id__type="archived")
        .count()
    )

    return JsonResponse(
        {
            "total_employees": employees,
            "total_offboarding": total_offboarding,
            "active_offboarding": active_offboarding,
            "archived": archived,
            "exit_ratio": exit_ratio,
            "pending_resignations": pending_resignations,
            "approved_resignations": approved_resignations,
            "task_completion": task_completion,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "notice_ending_soon": notice_ending_soon,
        }
    )


@login_required
def offboarding_pipeline(request):
    """Employees grouped by offboarding stage."""
    from offboarding.models import OffboardingEmployee, OffboardingStage

    stages = []

    try:
        stage_qs = OffboardingStage.objects.all().order_by("sequence")
        for stage in stage_qs:
            count = OffboardingEmployee.objects.filter(stage_id=stage).count()
            stages.append(
                {
                    "stage": stage.title,
                    "type": stage.type,
                    "count": count,
                }
            )
    except Exception:
        pass

    return JsonResponse({"stages": stages})


@login_required
def offboarding_resignation_status(request):
    """Resignation letter status breakdown."""
    from offboarding.models import ResignationLetter

    statuses = [
        {
            "status": "requested",
            "label": "Requested",
            "count": ResignationLetter.objects.filter(status="requested").count(),
        },
        {
            "status": "approved",
            "label": "Approved",
            "count": ResignationLetter.objects.filter(status="approved").count(),
        },
        {
            "status": "rejected",
            "label": "Rejected",
            "count": ResignationLetter.objects.filter(status="rejected").count(),
        },
    ]

    return JsonResponse({"statuses": statuses})


@login_required
def offboarding_task_status(request):
    """Task completion status breakdown."""
    from offboarding.models import EmployeeTask

    statuses = []
    for status, label in EmployeeTask.statuses:
        count = EmployeeTask.objects.filter(status=status).count()
        statuses.append({"status": status, "label": str(label), "count": count})

    return JsonResponse({"statuses": statuses})


@login_required
def offboarding_department_attrition(request):
    """Offboarding count by department."""
    from offboarding.models import OffboardingEmployee

    departments = []

    try:
        data = (
            OffboardingEmployee.objects.all()
            .values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "count": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def offboarding_exit_reasons(request):
    """Exit reasons breakdown."""
    from offboarding.models import ExitReason

    reasons = []

    try:
        data = (
            ExitReason.objects.all()
            .values("title")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            reasons.append(
                {
                    "reason": item["title"],
                    "count": item["count"],
                }
            )
    except Exception:
        pass

    return JsonResponse({"reasons": reasons})


@login_required
def offboarding_notice_period_tracker(request):
    """Employees with active notice periods."""
    from offboarding.models import OffboardingEmployee

    today = date.today()
    employees = []

    try:
        qs = (
            OffboardingEmployee.objects.filter(
                notice_period_ends__isnull=False,
            )
            .exclude(stage_id__type="archived")
            .select_related("employee_id", "stage_id")
            .order_by("notice_period_ends")[:15]
        )

        for oe in qs:
            emp = oe.employee_id
            days_left = (
                (oe.notice_period_ends - today).days if oe.notice_period_ends else None
            )
            employees.append(
                {
                    "id": emp.id if emp else None,
                    "name": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "stage": oe.stage_id.title if oe.stage_id else "—",
                    "notice_ends": (
                        oe.notice_period_ends.strftime("%b %d, %Y")
                        if oe.notice_period_ends
                        else "—"
                    ),
                    "days_left": days_left,
                    "status": (
                        "ended"
                        if days_left is not None and days_left < 0
                        else (
                            "ending"
                            if days_left is not None and days_left <= 7
                            else "active"
                        )
                    ),
                }
            )
    except Exception:
        pass

    return JsonResponse({"employees": employees})


@login_required
def offboarding_unreturned_assets(request):
    """Unreturned assets from offboarding employees."""
    assets = []

    try:
        if apps.is_installed("asset"):
            from asset.models import AssetAssignment
            from offboarding.models import OffboardingEmployee

            offboarding_emp_ids = OffboardingEmployee.objects.values_list(
                "employee_id", flat=True
            )

            qs = AssetAssignment.objects.filter(
                assigned_to_employee_id__in=offboarding_emp_ids,
                return_status__isnull=True,
            ).select_related("assigned_to_employee_id", "asset_id")[:15]

            for aa in qs:
                emp = aa.assigned_to_employee_id
                assets.append(
                    {
                        "id": emp.id if emp else None,
                        "employee": emp.get_full_name() if emp else "—",
                        "asset": aa.asset_id.asset_name if aa.asset_id else "—",
                        "category": (
                            aa.asset_id.asset_category_id.asset_category
                            if aa.asset_id and aa.asset_id.asset_category_id
                            else "—"
                        ),
                    }
                )
    except Exception:
        pass

    return JsonResponse({"assets": assets})


@login_required
def offboarding_joining_vs_exiting(request):
    """Monthly joining vs exiting trend for the last 6 months."""
    from employee.models import EmployeeWorkInformation
    from offboarding.models import ResignationLetter

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

        joining = EmployeeWorkInformation.objects.filter(
            date_joining__gte=month_start,
            date_joining__lte=month_end,
        ).count()

        exiting = ResignationLetter.objects.filter(
            planned_to_leave_on__gte=month_start,
            planned_to_leave_on__lte=month_end,
            status__in=["approved", "requested"],
        ).count()

        months.append(
            {
                "month": month_start.strftime("%b %Y"),
                "joining": joining,
                "exiting": exiting,
            }
        )

    return JsonResponse({"months": months})


@login_required
def offboarding_avg_duration(request):
    """Average offboarding duration from notice start to archived."""
    from offboarding.models import OffboardingEmployee

    avg_days = None
    try:
        archived = OffboardingEmployee.objects.filter(
            stage_id__type="archived",
            notice_period_starts__isnull=False,
        )
        durations = []
        for oe in archived:
            if oe.notice_period_ends and oe.notice_period_starts:
                delta = (oe.notice_period_ends - oe.notice_period_starts).days
                if delta >= 0:
                    durations.append(delta)
        if durations:
            avg_days = round(sum(durations) / len(durations), 1)
    except Exception:
        pass
    return JsonResponse(
        {
            "avg_days": avg_days,
            "total_archived": len(durations) if "durations" in dir() else 0,
        }
    )
