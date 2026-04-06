"""
Modern dashboard views — KPI summary + ApexCharts.

Accessible at /dashboard/modern/ alongside the existing dashboard.
"""

import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


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
def modern_dashboard(request):
    """Render the modern dashboard page."""
    return render(request, "dashboard_modern.html")


@login_required
def dashboard_kpi_data(request):
    """Return KPI summary data as JSON."""
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date

    total_employees = Employee.objects.filter(is_active=True).count()

    new_joiners = 0
    try:
        from employee.models import EmployeeWorkInformation

        new_joiners = EmployeeWorkInformation.objects.filter(
            date_joining__gte=first_of_month,
            date_joining__lte=today,
        ).count()
    except Exception:
        pass

    present_today = 0
    try:
        from attendance.models import Attendance

        present_today = (
            Attendance.objects.filter(
                attendance_date=today,
            )
            .values("employee_id")
            .distinct()
            .count()
        )
    except Exception:
        pass

    absent_today = max(0, total_employees - present_today)
    attendance_rate = (
        round((present_today / total_employees * 100), 1) if total_employees > 0 else 0
    )

    on_leave = 0
    try:
        from leave.models import LeaveRequest

        on_leave = (
            LeaveRequest.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                status="approved",
            )
            .values("employee_id")
            .distinct()
            .count()
        )
    except Exception:
        pass

    pending_leaves = 0
    try:
        from leave.models import LeaveRequest

        pending_leaves = LeaveRequest.objects.filter(status="requested").count()
    except Exception:
        pass

    open_recruitments = 0
    try:
        from recruitment.models import Recruitment

        open_recruitments = Recruitment.objects.filter(
            is_active=True, closed=False
        ).count()
    except Exception:
        pass

    return JsonResponse(
        {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "attendance_rate": attendance_rate,
            "on_leave": on_leave,
            "pending_leaves": pending_leaves,
            "new_joiners": new_joiners,
            "open_recruitments": open_recruitments,
            "date": today.isoformat(),
        }
    )


@login_required
def dashboard_attendance_trend(request):
    """Weekly attendance trend for the last 12 weeks."""
    today = date.today()
    weeks = []

    try:
        from attendance.models import Attendance
        from employee.models import Employee

        total = Employee.objects.filter(is_active=True).count()

        current_week_monday = today - timedelta(days=today.weekday())
        for i in range(11, -1, -1):
            week_start = current_week_monday - timedelta(weeks=i)
            # For the current week, use today as the end; otherwise use Friday
            if i == 0:
                week_end = today
            else:
                week_end = week_start + timedelta(days=4)

            present = (
                Attendance.objects.filter(
                    attendance_date__gte=week_start,
                    attendance_date__lte=week_end,
                )
                .values("employee_id")
                .distinct()
                .count()
            )

            rate = round((present / total * 100), 1) if total > 0 else 0
            label = week_start.strftime("%b %d") + (" (now)" if i == 0 else "")
            weeks.append({"week": label, "rate": rate, "present": present})
    except Exception:
        weeks = [{"week": f"W{i+1}", "rate": 0, "present": 0} for i in range(12)]

    return JsonResponse({"weeks": weeks})


@login_required
def dashboard_leave_breakdown(request):
    """Leave type breakdown for the selected period."""
    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    breakdown = []

    try:
        from django.db.models import Count, Sum

        from leave.models import LeaveRequest

        data = (
            LeaveRequest.objects.filter(
                start_date__gte=first_of_month,
                status__in=["approved", "requested"],
            )
            .values("leave_type_id__name")
            .annotate(count=Count("id"), total_days=Sum("requested_days"))
            .order_by("-count")[:8]
        )

        for item in data:
            breakdown.append(
                {
                    "type": item["leave_type_id__name"] or "Unknown",
                    "count": item["count"],
                    "days": float(item["total_days"] or 0),
                }
            )
    except Exception:
        pass

    return JsonResponse({"breakdown": breakdown, "month": today.strftime("%B %Y")})


@login_required
def dashboard_department_headcount(request):
    """Department-wise headcount."""
    departments = []

    try:
        from django.db.models import Count

        from employee.models import Employee

        data = (
            Employee.objects.filter(is_active=True)
            .values("employee_work_info__department_id__department")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        for item in data:
            dept = item["employee_work_info__department_id__department"]
            if dept:
                departments.append({"department": dept, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def dashboard_gender_split(request):
    """Gender distribution."""
    genders = []

    try:
        from django.db.models import Count

        from employee.models import Employee

        data = (
            Employee.objects.filter(is_active=True)
            .values("gender")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        gender_map = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
            "": "Not Specified",
        }
        for item in data:
            genders.append(
                {
                    "gender": gender_map.get(
                        item["gender"], item["gender"] or "Not Specified"
                    ),
                    "count": item["count"],
                }
            )
    except Exception:
        pass

    return JsonResponse({"genders": genders})


@login_required
def dashboard_announcements(request):
    """Active announcements for the current user."""
    from base.models import Announcement

    today = date.today()
    announcements = []

    try:
        from django.db.models import Q

        qs = Announcement.objects.filter(
            Q(expire_date__gte=today) | Q(expire_date__isnull=True),
        ).order_by("-created_at")[:20]

        for ann in qs:
            announcements.append(
                {
                    "id": ann.id,
                    "title": ann.title,
                    "description": (ann.description or "")[:160],
                    "date": (
                        ann.created_at.strftime("%b %d, %Y") if ann.created_at else ""
                    ),
                    "expire_date": (
                        ann.expire_date.strftime("%b %d") if ann.expire_date else None
                    ),
                }
            )
    except Exception:
        pass

    return JsonResponse({"announcements": announcements})


@login_required
def dashboard_announcement_detail(request, pk):
    """Return a single announcement's full details as JSON."""
    from base.models import Announcement, AnnouncementView

    try:
        ann = Announcement.objects.get(pk=pk)
    except Announcement.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # Track view (field is employee_id, not employee)
    employee = getattr(request.user, "employee_get", None)
    if employee:
        AnnouncementView.objects.get_or_create(
            announcement=ann, user=request.user, defaults={"employee_id": employee}
        )

    attachments = []
    for att in ann.attachments.all():
        try:
            url = att.file.url
            name = att.file.name.split("/")[-1]
            is_image = any(
                url.lower().endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
            )
            attachments.append({"url": url, "name": name, "is_image": is_image})
        except Exception:
            pass

    departments = [d.department for d in ann.department.all()]
    job_positions = [j.job_position for j in ann.job_position.all()]
    views_count = ann.get_views().count() if hasattr(ann, "get_views") else 0

    return JsonResponse(
        {
            "id": ann.id,
            "title": ann.title,
            "description": ann.description or "",
            "date": (
                ann.created_at.strftime("%B %d, %Y at %I:%M %p")
                if ann.created_at
                else ""
            ),
            "expire_date": (
                ann.expire_date.strftime("%b %d, %Y") if ann.expire_date else None
            ),
            "attachments": attachments,
            "departments": departments,
            "job_positions": job_positions,
            "views_count": views_count,
            "comments_disabled": ann.disable_comments,
        }
    )


@login_required
def dashboard_todays_leave(request):
    """Employees on leave today."""
    today = date.today()
    leaves = []

    try:
        from leave.models import LeaveRequest

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
            leaves.append(
                {
                    "id": lr.id,
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "badge_id": getattr(emp, "badge_id", "") or "",
                    "avatar": (
                        (
                            emp.employee_profile.url
                            if emp and emp.employee_profile
                            else None
                        )
                        if emp
                        else None
                    ),
                    "leave_type": lr.leave_type_id.name if lr.leave_type_id else "—",
                    "start": lr.start_date.strftime("%b %d"),
                    "end": lr.end_date.strftime("%b %d"),
                    "days": float(lr.requested_days) if lr.requested_days else 1,
                }
            )
    except Exception:
        pass

    return JsonResponse({"leaves": leaves, "date": today.isoformat()})


@login_required
def dashboard_upcoming_holidays(request):
    """Upcoming holidays in the next 7 days for the current company."""
    today = date.today()
    next_week = today + timedelta(days=7)
    holidays_data = []

    try:
        from base.models import Holiday

        company_id = request.session.get("selected_company")
        qs = Holiday.objects.filter(
            start_date__gte=today,
            start_date__lte=next_week,
        )
        if company_id:
            qs = qs.filter(company_id=company_id)

        for h in qs.order_by("start_date")[:10]:
            holidays_data.append(
                {
                    "id": h.pk,
                    "name": h.name,
                    "start_date": h.start_date.strftime("%b %d"),
                    "end_date": h.end_date.strftime("%b %d") if h.end_date else None,
                    "days_away": (h.start_date - today).days,
                }
            )
    except Exception:
        pass

    return JsonResponse({"holidays": holidays_data})


@login_required
def dashboard_birthdays_anniversaries(request):
    """Upcoming birthdays and work anniversaries in the next 7 days."""
    today = date.today()
    end = today + timedelta(days=7)
    birthdays = []
    anniversaries = []

    try:
        from employee.models import Employee, EmployeeWorkInformation

        # Birthdays — compare month/day to handle year-wrap
        for emp in Employee.objects.filter(is_active=True).exclude(dob__isnull=True):
            dob = emp.dob
            this_year_bday = dob.replace(year=today.year)
            if this_year_bday < today:
                this_year_bday = dob.replace(year=today.year + 1)
            if today <= this_year_bday <= end:
                birthdays.append(
                    {
                        "id": emp.id,
                        "name": emp.get_full_name(),
                        "avatar": (
                            emp.employee_profile.url if emp.employee_profile else None
                        ),
                        "date": this_year_bday.strftime("%b %d"),
                        "days_away": (this_year_bday - today).days,
                    }
                )

        birthdays.sort(key=lambda x: x["days_away"])

        # Work anniversaries
        for wi in (
            EmployeeWorkInformation.objects.filter(
                employee_id__is_active=True,
            )
            .exclude(date_joining__isnull=True)
            .select_related("employee_id")
        ):
            join = wi.date_joining
            this_year_ann = join.replace(year=today.year)
            if this_year_ann < today:
                this_year_ann = join.replace(year=today.year + 1)
            if today <= this_year_ann <= end:
                years = today.year - join.year
                if this_year_ann.year > today.year:
                    years += 1
                emp = wi.employee_id
                anniversaries.append(
                    {
                        "id": emp.id,
                        "name": emp.get_full_name(),
                        "avatar": (
                            emp.employee_profile.url if emp.employee_profile else None
                        ),
                        "date": this_year_ann.strftime("%b %d"),
                        "years": years,
                        "days_away": (this_year_ann - today).days,
                    }
                )

        anniversaries.sort(key=lambda x: x["days_away"])
    except Exception:
        pass

    return JsonResponse(
        {
            "birthdays": birthdays[:10],
            "anniversaries": anniversaries[:10],
        }
    )


@login_required
def dashboard_recruitment_pipeline(request):
    """Recruitment pipeline funnel — candidates by stage for active recruitments."""
    stages = []

    try:
        from django.db.models import Count

        from recruitment.models import Candidate, Recruitment, Stage

        active_recruitments = Recruitment.objects.filter(is_active=True, closed=False)
        total_active = active_recruitments.count()

        data = (
            Candidate.objects.filter(
                recruitment_id__in=active_recruitments,
                canceled=False,
            )
            .values("stage_id__stage", "stage_id__stage_type", "stage_id__sequence")
            .annotate(count=Count("id"))
            .order_by("stage_id__sequence")
        )

        for item in data:
            stages.append(
                {
                    "stage": item["stage_id__stage"] or "Unknown",
                    "type": item["stage_id__stage_type"] or "",
                    "count": item["count"],
                }
            )

        # Summary counts
        total_candidates = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, canceled=False
        ).count()
        hired = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, hired=True
        ).count()
        rejected = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, canceled=True
        ).count()
    except Exception:
        total_active = 0
        total_candidates = 0
        hired = 0
        rejected = 0

    return JsonResponse(
        {
            "stages": stages,
            "active_recruitments": total_active,
            "total_candidates": total_candidates,
            "hired": hired,
            "rejected": rejected,
        }
    )


@login_required
def dashboard_payroll_summary(request):
    """Payroll summary — selected period vs previous period."""
    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    period_days = (to_date - from_date).days or 30
    prev_month_end = first_of_month - timedelta(days=1)
    prev_month_start = prev_month_end - timedelta(days=period_days)

    current = {"gross": 0, "deductions": 0, "net": 0, "count": 0}
    previous = {"gross": 0, "deductions": 0, "net": 0, "count": 0}

    try:
        from django.db.models import Sum

        from payroll.models.models import Payslip

        def _aggregate(qs):
            agg = qs.aggregate(
                total_gross=Sum("gross_pay"),
                total_deductions=Sum("deduction"),
                total_net=Sum("net_pay"),
            )
            return {
                "gross": round(float(agg["total_gross"] or 0), 2),
                "deductions": round(float(agg["total_deductions"] or 0), 2),
                "net": round(float(agg["total_net"] or 0), 2),
                "count": qs.count(),
            }

        current_qs = Payslip.objects.filter(
            start_date__gte=first_of_month,
            start_date__lte=today,
            status__in=["confirmed", "paid", "review_ongoing"],
        )
        current = _aggregate(current_qs)

        prev_qs = Payslip.objects.filter(
            start_date__gte=prev_month_start,
            start_date__lte=prev_month_end,
            status__in=["confirmed", "paid"],
        )
        previous = _aggregate(prev_qs)
    except Exception:
        pass

    # Trend calculation
    change_pct = 0
    if previous["net"] > 0:
        change_pct = round(
            ((current["net"] - previous["net"]) / previous["net"]) * 100, 1
        )

    return JsonResponse(
        {
            "current_month": today.strftime("%B %Y"),
            "previous_month": prev_month_start.strftime("%B %Y"),
            "current": current,
            "previous": previous,
            "change_percent": change_pct,
        }
    )


@login_required
def dashboard_pending_approvals(request):
    """Pending items awaiting the logged-in user's approval."""
    user = request.user
    pending = {}

    # Leave requests
    try:
        from leave.models import LeaveRequest

        leave_count = LeaveRequest.objects.filter(status="requested").count()
        pending["leave_requests"] = leave_count
    except Exception:
        pending["leave_requests"] = 0

    # Attendance requests
    try:
        from attendance.models import Attendance

        att_count = Attendance.objects.filter(
            is_validate_request=True,
            is_validate_request_approved=False,
        ).count()
        pending["attendance_requests"] = att_count
    except Exception:
        pending["attendance_requests"] = 0

    # Asset requests
    try:
        from asset.models import AssetRequest

        asset_count = AssetRequest.objects.filter(
            asset_request_status="Requested",
        ).count()
        pending["asset_requests"] = asset_count
    except Exception:
        pending["asset_requests"] = 0

    # Shift requests
    try:
        from base.models import ShiftRequest

        shift_count = ShiftRequest.objects.filter(
            approved=False,
            canceled=False,
        ).count()
        pending["shift_requests"] = shift_count
    except Exception:
        pending["shift_requests"] = 0

    # Work type requests
    try:
        from base.models import WorkTypeRequest

        wt_count = WorkTypeRequest.objects.filter(
            approved=False,
            canceled=False,
        ).count()
        pending["work_type_requests"] = wt_count
    except Exception:
        pending["work_type_requests"] = 0

    # Reimbursement requests
    try:
        from payroll.models.models import Reimbursement

        reimb_count = Reimbursement.objects.filter(status="requested").count()
        pending["reimbursements"] = reimb_count
    except Exception:
        pending["reimbursements"] = 0

    pending["total"] = sum(pending.values())

    return JsonResponse({"pending": pending})


@login_required
@require_http_methods(["POST"])
def save_dashboard_prefs(request):
    """Persist dashboard customisation to DashboardEmployeeCharts model."""
    try:
        from base.models import DashboardEmployeeCharts

        data = json.loads(request.body)
        excluded = [
            p["id"] for p in data.get("prefs", []) if not p.get("visible", True)
        ]
        emp = request.user.employee_get
        DashboardEmployeeCharts.objects.update_or_create(
            employee=emp, defaults={"charts": excluded}
        )
    except Exception:
        pass
    return JsonResponse({"status": "ok"})


@login_required
def load_dashboard_prefs(request):
    """Return saved dashboard preferences for the current employee."""
    try:
        from base.models import DashboardEmployeeCharts

        emp = request.user.employee_get
        obj = DashboardEmployeeCharts.objects.filter(employee=emp).first()
        excluded = obj.charts if obj and obj.charts else []
        return JsonResponse({"excluded": excluded})
    except Exception:
        return JsonResponse({"excluded": []})


@login_required
def dashboard_turnover(request):
    """Employee turnover — new hires vs exits over the last 6 months ending at selected period."""
    _, to_date = _parse_period(request)
    today = to_date
    months = []

    try:
        from django.db.models import Count, Q

        from employee.models import Employee, EmployeeWorkInformation

        for i in range(5, -1, -1):
            # Calculate month boundaries
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

            # New hires (joined this month)
            hires = EmployeeWorkInformation.objects.filter(
                date_joining__gte=month_start,
                date_joining__lte=month_end,
            ).count()

            # Exits (inactive employees whose last working date falls in this month)
            exits = 0
            try:
                exits = (
                    Employee.objects.filter(
                        is_active=False,
                    )
                    .filter(
                        Q(employee_work_info__contract_end_date__gte=month_start)
                        & Q(employee_work_info__contract_end_date__lte=month_end)
                    )
                    .count()
                )
            except Exception:
                pass

            months.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "hires": hires,
                    "exits": exits,
                    "net": hires - exits,
                }
            )

        # Overall turnover rate
        total_employees = Employee.objects.filter(is_active=True).count()
        total_exits_6m = sum(m["exits"] for m in months)
        turnover_rate = (
            round((total_exits_6m / total_employees * 100), 1)
            if total_employees > 0
            else 0
        )
    except Exception:
        months = [
            {"month": f"M{i+1}", "hires": 0, "exits": 0, "net": 0} for i in range(6)
        ]
        turnover_rate = 0

    return JsonResponse(
        {
            "months": months,
            "turnover_rate_6m": turnover_rate,
        }
    )
