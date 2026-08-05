"""
Modern dashboard views — KPI summary + ApexCharts.

Accessible at /dashboard/modern/ alongside the existing dashboard.
"""

import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods


def _safe_url(url_name):
    """Reverse a URL name; return '#' if the URL is not registered."""
    try:
        return reverse(url_name)
    except Exception:
        return "#"


# ---------------------------------------------------------------------------
# Setup checklist helpers
# ---------------------------------------------------------------------------


def _is_setup_admin(request):
    """
    True for superusers, staff, and any user who can manage HR setup entities.
    Regular employees (no management perms) are excluded — they can't complete
    setup steps and should not see setup prompts.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        return True
    return user.has_perm("base.add_department") or user.has_perm("base.add_company")


def _resolve_checklist_company(request):
    """
    Return the integer PK of the company currently active for this request.

    Priority:
      1. The company stored in the ContextVar by the middleware
      2. The first company in the DB (fresh install with no session yet)
      3. None  (no company exists — the "Company" step is the first to do)
    """
    from horilla.horilla_middlewares import get_selected_company

    company_id = get_selected_company()
    if company_id and company_id != "all":
        try:
            return int(company_id)
        except (TypeError, ValueError):
            pass

    # "all" or None → fall back to first company in the DB
    from base.models import Company

    first = Company.objects.first()
    return first.pk if first else None


def _exists_for_company(ModelClass, company_id):
    """
    Return True if at least one record of ModelClass is visible for the given
    company.  Mirrors HorillaCompanyManager: a record is visible when it is
    explicitly assigned to this company OR has no company assignment at all
    (meaning it is shared across all companies — common for lookup tables like
    WorkType, EmployeeType, EmployeeShift whose M2M company_id may be empty).
    """
    try:
        filter_path = ModelClass.objects.get_company_filter_path()
        if not filter_path:
            return False
        null_path = f"{filter_path}__isnull"
        return (
            ModelClass.objects.entire()
            .filter(Q(**{filter_path: company_id}) | Q(**{null_path: True}))
            .exists()
        )
    except Exception:
        return False


def _get_setup_checklist_context(request):
    """
    Builds the context for the onboarding setup checklist banner.

    Returns ``{"show_setup_checklist": False}`` when:
      • the user is not an admin/manager (regular employees skip it)
      • the user has already dismissed the banner for the active company
      • all 8 steps are complete for the active company

    In DEBUG mode only, ``?preview_checklist=1`` forces the banner visible
    with every step shown as incomplete — useful for testing on populated DBs
    without deleting any data.
    """
    from django.conf import settings

    from base.models import (
        Company,
        Department,
        DynamicEmailConfiguration,
        EmployeeShift,
        EmployeeShiftSchedule,
        JobPosition,
        SetupChecklistDismissal,
        WorkType,
    )

    # 1. Permission gate — only show to admins / managers
    if not _is_setup_admin(request):
        return {"show_setup_checklist": False}

    preview_mode = settings.DEBUG and request.GET.get("preview_checklist") == "1"

    # 2. Resolve the company we're scoping the checklist to
    company_pk = _resolve_checklist_company(request)

    # 3. Check per-user, per-company dismissal
    if not preview_mode:
        dismissed = SetupChecklistDismissal.objects.filter(
            user=request.user, company_id=company_pk
        ).exists()
        if dismissed:
            return {"show_setup_checklist": False}

    # 4. Build steps — each checks live DB scoped to the active company
    def _has_company():
        # Company itself is the root tenant object; any company existing is enough.
        try:
            return Company.objects.exists()
        except Exception:
            return False

    def _has_employees():
        try:
            from employee.models import Employee

            return _exists_for_company(Employee, company_pk)
        except Exception:
            return False

    def _has_mail_server():
        try:
            return DynamicEmailConfiguration.objects.filter(
                is_primary=True, host__isnull=False
            ).exists()
        except Exception:
            return False

    steps = [
        {
            "key": "company",
            "title": _("Company"),
            "description": _("Add your company profile — name, logo and timezone."),
            "url": _safe_url("company-view"),
            "done": _has_company(),
        },
        {
            "key": "department",
            "title": _("Departments"),
            "description": _("Create the departments your employees will belong to."),
            "url": _safe_url("department-view"),
            "done": (
                _exists_for_company(Department, company_pk) if company_pk else False
            ),
        },
        {
            "key": "job_position",
            "title": _("Job Positions"),
            "description": _("Define named roles within each department."),
            "url": _safe_url("job-position-view"),
            "done": (
                _exists_for_company(JobPosition, company_pk) if company_pk else False
            ),
        },
        {
            "key": "shift",
            "title": _("Shift"),
            "description": _("Define working schedules — Morning, Evening, Night."),
            "url": _safe_url("employee-shift-view"),
            "done": (
                _exists_for_company(EmployeeShift, company_pk) if company_pk else False
            ),
        },
        {
            "key": "shift_schedule",
            "title": _("Shift Schedule"),
            "description": _("Set day-wise timings for each shift."),
            "url": _safe_url("employee-shift-schedule-view"),
            "done": (
                _exists_for_company(EmployeeShiftSchedule, company_pk)
                if company_pk
                else False
            ),
        },
        {
            "key": "work_type",
            "title": _("Work Type"),
            "description": _("Set engagement types — Full Time, Part Time, Contract."),
            "url": _safe_url("work-type-view"),
            "done": _exists_for_company(WorkType, company_pk) if company_pk else False,
        },
        {
            "key": "mail_server",
            "title": _("Mail Server"),
            "description": _(
                "Configure an outgoing mail server so Horilla can send emails."
            ),
            "url": _safe_url("mail-server-conf"),
            "done": _has_mail_server(),
        },
        {
            "key": "first_employee",
            "title": _("First Employee"),
            "description": _("Add your first employee to bring everything together."),
            "url": _safe_url("employee-view-new"),
            "done": _has_employees() if company_pk else False,
        },
    ]

    # 5. Preview mode overrides all done flags to False
    if preview_mode:
        for s in steps:
            s["done"] = False

    completed = sum(1 for s in steps if s["done"])
    total = len(steps)

    # Auto-hide once all steps are complete (no dismiss record needed)
    if not preview_mode and completed == total:
        return {"show_setup_checklist": False}

    # 6. Precompute connector-line state for the template.
    for i, step in enumerate(steps):
        step["left_line_active"] = (i > 0) and steps[i - 1]["done"]
        step["right_line_active"] = step["done"] and (i < total - 1)

    next_step = next((s for s in steps if not s["done"]), None)
    progress_pct = int(completed / total * 100)

    return {
        "show_setup_checklist": True,
        "setup_steps": steps,
        "setup_completed": completed,
        "setup_total": total,
        "setup_next_step": next_step,
        "setup_progress_pct": progress_pct,
        "setup_dismiss_url": _safe_url("dashboard-dismiss-setup-checklist"),
        "setup_company_pk": company_pk,
    }


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


def _is_manager(user):
    """Return True if user is a reporting manager for at least one active employee."""
    try:
        from employee.models import EmployeeWorkInformation

        emp = getattr(user, "employee_get", None)
        if not emp:
            return False
        return EmployeeWorkInformation.objects.filter(reporting_manager_id=emp).exists()
    except Exception:
        return False


@login_required
def main_dashboard_view(request):
    """Render the modern dashboard page."""
    from django.apps import apps

    from horilla.methods import get_horilla_model_class

    enabled_timerunner = True
    get_forecasted_at_work = None

    if apps.is_installed("attendance"):
        try:
            AttendanceGeneralSetting = get_horilla_model_class(
                app_label="attendance", model="attendancegeneralsetting"
            )
            first = AttendanceGeneralSetting.objects.first()
            if first:
                enabled_timerunner = first.time_runner
        except Exception:
            pass

        try:
            get_forecasted_at_work = request.user.employee_get.get_forecasted_at_work()
        except Exception:
            pass

    # Load saved chart preferences from DB for the current employee
    employee_chart_prefs = "[]"
    try:
        from base.models import DashboardEmployeeCharts

        emp = request.user.employee_get
        obj = DashboardEmployeeCharts.objects.filter(employee=emp).first()
        if obj and obj.charts:
            employee_chart_prefs = json.dumps(obj.charts)
    except Exception:
        pass

    context = {
        "enabled_timerunner": enabled_timerunner,
        "get_forecasted_at_work": get_forecasted_at_work,
        "employee_chart_prefs": employee_chart_prefs,
    }
    context.update(_get_setup_checklist_context(request))
    return render(request, "dashboard.html", context)


@login_required
@require_http_methods(["POST"])
def dismiss_setup_checklist(request):
    """
    HTMX endpoint — records per-user, per-company dismissal and returns empty
    HTML so the banner is removed via outerHTML swap.
    Only admins can dismiss (non-admins never see the banner anyway).
    """
    from base.models import SetupChecklistDismissal

    if _is_setup_admin(request):
        company_pk = _resolve_checklist_company(request)
        SetupChecklistDismissal.objects.get_or_create(
            user=request.user,
            company_id=company_pk,
        )
    return HttpResponse("")


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
        from leave.models import LeaveRequest

        real_today = date.today()
        leave_employee_ids = list(
            LeaveRequest.objects.filter(
                start_date__lte=real_today,
                status="approved",
            )
            .filter(
                Q(end_date__gte=real_today)
                | Q(end_date__isnull=True, start_date=real_today)
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )
        present_today = (
            Attendance.objects.filter(attendance_date=today)
            .exclude(employee_id__in=leave_employee_ids)
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

        real_today = date.today()
        on_leave = (
            LeaveRequest.objects.filter(
                start_date__lte=real_today,
                status="approved",
            )
            .filter(
                Q(end_date__gte=real_today)
                | Q(end_date__isnull=True, start_date=real_today)
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
    """Weekly attendance trend.

    Requires attendance.view_attendance permission or superuser.
    """
    user = request.user
    if not (user.is_superuser or user.has_perm("attendance.view_attendance")):
        return JsonResponse({"no_permission": True})

    today = date.today()
    weeks = []

    has_period = bool(request.GET.get("from_date") and request.GET.get("to_date"))
    if has_period:
        from_date, to_date = _parse_period(request)
    else:
        to_date = today
        from_date = today - timedelta(weeks=11) - timedelta(days=today.weekday())

    try:
        from attendance.models import Attendance
        from employee.models import Employee

        total = Employee.objects.filter(is_active=True).count()

        bucket_start = from_date - timedelta(days=from_date.weekday())
        last_monday = to_date - timedelta(days=to_date.weekday())
        while bucket_start <= last_monday:
            week_end = min(bucket_start + timedelta(days=6), to_date)
            week_start_q = max(bucket_start, from_date)

            present = (
                Attendance.objects.filter(
                    attendance_date__gte=week_start_q,
                    attendance_date__lte=week_end,
                )
                .values("employee_id")
                .distinct()
                .count()
            )
            rate = round((present / total * 100), 1) if total > 0 else 0

            is_current = bucket_start <= today <= bucket_start + timedelta(days=6)
            label = bucket_start.strftime("%b %d") + (" (now)" if is_current else "")
            weeks.append({"week": label, "rate": rate, "present": present})
            bucket_start += timedelta(weeks=1)
    except Exception:
        weeks = [{"week": f"W{i+1}", "rate": 0, "present": 0} for i in range(12)]

    return JsonResponse({"weeks": weeks})


@login_required
def dashboard_leave_breakdown(request):
    """Leave type breakdown for the selected period.

    Requires leave.view_leaverequest permission or superuser.
    """
    user = request.user
    if not (user.is_superuser or user.has_perm("leave.view_leaverequest")):
        return JsonResponse({"no_permission": True})

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
                    "type": item["leave_type_id__name"] or _("Unknown"),
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
            "male": _("Male"),
            "female": _("Female"),
            "other": _("Other"),
            "": _("Not Specified"),
        }
        for item in data:
            genders.append(
                {
                    "gender": gender_map.get(
                        item["gender"], item["gender"] or _("Not Specified")
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
    """Employees on leave today.

    Users without leave view permission see only their own leave.
    """
    today = date.today()
    leaves = []

    user = request.user
    is_mgr = _is_manager(user)
    can_view_all = user.has_perm("leave.view_leaverequest") or is_mgr

    try:
        from leave.models import LeaveRequest

        qs = LeaveRequest.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            status="approved",
        ).select_related("employee_id", "leave_type_id")

        if not can_view_all:
            employee = getattr(user, "employee_get", None)
            qs = qs.filter(employee_id=employee) if employee else qs.none()
        elif is_mgr and not user.has_perm("leave.view_leaverequest"):
            from base.methods import filtersubordinates

            qs = filtersubordinates(request, qs, "leave.view_leaverequest")

        qs = qs.order_by("employee_id__employee_first_name")[:20]

        for lr in qs:
            emp = lr.employee_id
            leaves.append(
                {
                    "id": lr.id,
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "badge_id": getattr(emp, "badge_id", "") or "",
                    "avatar": emp.get_avatar() if emp else None,
                    "leave_type": lr.leave_type_id.name if lr.leave_type_id else "—",
                    "start": lr.start_date.strftime("%b %d"),
                    "end": lr.end_date.strftime("%b %d"),
                    "days": float(lr.requested_days) if lr.requested_days else 1,
                }
            )
    except Exception:
        pass

    return JsonResponse(
        {"leaves": leaves, "date": today.isoformat(), "is_restricted": not can_view_all}
    )


@login_required
def dashboard_upcoming_holidays(request):
    """Upcoming holidays in the next 7 days for the current company."""
    today = date.today()
    next_week = today + timedelta(days=7)
    holidays_data = []

    try:
        from django.db.models import Q

        from base.models import Holidays

        company_id = request.session.get("selected_company")
        qs = Holidays.objects.filter(
            Q(start_date__gte=today, start_date__lte=next_week)
            | Q(start_date__lte=today, end_date__gte=today),
            is_specific=False,
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
                        "avatar": emp.get_avatar(),
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
                        "avatar": emp.get_avatar(),
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
    """Recruitment pipeline funnel — candidates aggregated by stage type.

    Hidden for users without recruitment view permission.
    """
    user = request.user
    is_mgr = _is_manager(user)
    if not (user.has_perm("recruitment.view_recruitment") or is_mgr):
        response = JsonResponse({"no_permission": True})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    stages = []

    try:
        from django.db.models import Count

        from recruitment.models import Candidate, Recruitment, Stage

        active_recruitments = Recruitment.objects.filter(is_active=True, closed=False)
        total_active = active_recruitments.count()

        # Aggregate by stage_type so duplicate stage names across recruitments collapse
        stage_type_order = [t[0] for t in Stage.stage_types]
        stage_type_labels = {t[0]: str(t[1]) for t in Stage.stage_types}

        data = (
            Candidate.objects.filter(
                # recruitment_id__in=active_recruitments,
                is_active=True,
            )
            .values("stage_id__stage_type")
            .annotate(count=Count("id"))
        )

        # Build ordered dict keyed by stage_type
        totals = {}
        for item in data:
            st = item["stage_id__stage_type"] or ""
            totals[st] = totals.get(st, 0) + item["count"]

        # Output in canonical stage order
        for st in stage_type_order:
            if st in totals:
                stages.append(
                    {
                        "stage": stage_type_labels.get(st, st.capitalize()),
                        "type": st,
                        "count": totals[st],
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

    response = JsonResponse(
        {
            "stages": stages,
            "total_active": total_active,
            "total_candidates": total_candidates,
            "hired": hired,
            "rejected": rejected,
        }
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@login_required
def dashboard_payroll_summary(request):
    """Payroll summary — selected period vs previous period."""
    if not (request.user.is_superuser or request.user.has_perm("payroll.view_payslip")):
        return JsonResponse({"no_permission": True})
    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    # Always use full calendar month boundaries for previous month
    prev_month_end = first_of_month - timedelta(days=1)  # last day of previous month
    prev_month_start = prev_month_end.replace(day=1)  # first day of previous month

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
    """Pending items awaiting the logged-in user's approval.

    For users without any approval permission, shows their own pending requests
    (items they submitted that are waiting for approval).
    """
    user = request.user
    pending = {}

    has_leave_perm = user.has_perm("leave.change_leaverequest")
    has_attendance_perm = user.has_perm("attendance.change_validateattendance")
    has_asset_perm = user.has_perm("asset.change_assetrequest")
    has_shift_perm = user.has_perm("base.change_shiftrequest")
    has_wt_perm = user.has_perm("base.change_worktyperequest")
    has_reimb_perm = user.has_perm("payroll.change_reimbursement")
    is_mgr = _is_manager(user)

    can_approve = any(
        [
            has_leave_perm,
            has_attendance_perm,
            has_asset_perm,
            has_shift_perm,
            has_wt_perm,
            has_reimb_perm,
            is_mgr,
        ]
    )
    is_restricted = not can_approve
    employee = getattr(user, "employee_get", None)

    # Leave requests
    try:
        from leave.models import LeaveRequest

        if can_approve:
            if has_leave_perm:
                leave_count = LeaveRequest.objects.filter(status="requested").count()
            else:
                from base.methods import filtersubordinates

                qs = LeaveRequest.objects.filter(status="requested")
                leave_count = filtersubordinates(
                    request, qs, "leave.change_leaverequest"
                ).count()
        else:
            leave_count = (
                LeaveRequest.objects.filter(
                    employee_id=employee, status="requested"
                ).count()
                if employee
                else 0
            )
        pending["leave_requests"] = leave_count
    except Exception:
        pending["leave_requests"] = 0

    # Attendance requests
    try:
        from attendance.models import Attendance

        if can_approve:
            if has_attendance_perm:
                att_count = Attendance.objects.filter(
                    is_validate_request=True,
                    is_validate_request_approved=False,
                ).count()
            else:
                from base.methods import filtersubordinates

                qs = Attendance.objects.filter(
                    is_validate_request=True,
                    is_validate_request_approved=False,
                )
                att_count = filtersubordinates(
                    request, qs, "attendance.change_validateattendance"
                ).count()
        else:
            att_count = (
                Attendance.objects.filter(
                    employee_id=employee,
                    is_validate_request=True,
                    is_validate_request_approved=False,
                ).count()
                if employee
                else 0
            )
        pending["attendance_requests"] = att_count
    except Exception:
        pending["attendance_requests"] = 0

    # Asset requests
    try:
        from asset.models import AssetRequest

        if can_approve and has_asset_perm:
            asset_count = AssetRequest.objects.filter(
                asset_request_status="Requested",
            ).count()
        else:
            asset_count = (
                AssetRequest.objects.filter(
                    requested_employee_id=employee,
                    asset_request_status="Requested",
                ).count()
                if employee
                else 0
            )
        pending["asset_requests"] = asset_count
    except Exception:
        pending["asset_requests"] = 0

    # Shift requests
    try:
        from base.models import ShiftRequest

        if can_approve:
            if has_shift_perm:
                shift_count = ShiftRequest.objects.filter(
                    approved=False,
                    canceled=False,
                ).count()
            else:
                from base.methods import filtersubordinates

                qs = ShiftRequest.objects.filter(approved=False, canceled=False)
                shift_count = filtersubordinates(
                    request, qs, "base.change_shiftrequest"
                ).count()
        else:
            shift_count = (
                ShiftRequest.objects.filter(
                    employee_id=employee,
                    approved=False,
                    canceled=False,
                ).count()
                if employee
                else 0
            )
        pending["shift_requests"] = shift_count
    except Exception:
        pending["shift_requests"] = 0

    # Work type requests
    try:
        from base.models import WorkTypeRequest

        if can_approve:
            if has_wt_perm:
                wt_count = WorkTypeRequest.objects.filter(
                    approved=False,
                    canceled=False,
                ).count()
            else:
                from base.methods import filtersubordinates

                qs = WorkTypeRequest.objects.filter(approved=False, canceled=False)
                wt_count = filtersubordinates(
                    request, qs, "base.change_worktyperequest"
                ).count()
        else:
            wt_count = (
                WorkTypeRequest.objects.filter(
                    employee_id=employee,
                    approved=False,
                    canceled=False,
                ).count()
                if employee
                else 0
            )
        pending["work_type_requests"] = wt_count
    except Exception:
        pending["work_type_requests"] = 0

    # Reimbursement requests
    try:
        from payroll.models.models import Reimbursement

        if can_approve and has_reimb_perm:
            reimb_count = Reimbursement.objects.filter(status="requested").count()
        else:
            reimb_count = (
                Reimbursement.objects.filter(
                    employee_id=employee, status="requested"
                ).count()
                if employee
                else 0
            )
        pending["reimbursements"] = reimb_count
    except Exception:
        pending["reimbursements"] = 0

    pending["total"] = sum(pending.values())

    return JsonResponse({"pending": pending, "is_restricted": is_restricted})


@login_required
@require_http_methods(["POST"])
def save_dashboard_prefs(request):
    """Persist dashboard customisation to DashboardEmployeeCharts model."""
    try:
        from base.models import DashboardEmployeeCharts

        data = json.loads(request.body)
        prefs = data.get("prefs", [])
        # Store full prefs (order + visibility) so DB can fully restore state
        clean_prefs = [
            {"id": p["id"], "visible": p.get("visible", True)} for p in prefs
        ]
        emp = request.user.employee_get
        DashboardEmployeeCharts.objects.update_or_create(
            employee=emp, defaults={"charts": clean_prefs}
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
        prefs = obj.charts if obj and obj.charts else []
        return JsonResponse({"prefs": prefs})
    except Exception:
        return JsonResponse({"prefs": []})


@login_required
def dashboard_turnover(request):
    """Employee turnover — new hires vs exits over the last 6 months ending at selected period.

    Hidden for users without employee view permission (org-level metric).
    """
    user = request.user
    is_mgr = _is_manager(user)
    if not (user.has_perm("employee.view_employee") or is_mgr):
        return JsonResponse({"no_permission": True})

    _, to_date = _parse_period(request)
    today = to_date
    months = []

    try:
        from django.db.models import Count, Q

        from employee.models import Employee, EmployeeWorkInformation

        for i in range(5, -1, -1):
            # Calculate month boundaries using calendar-correct month subtraction
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = today.replace(year=year, month=month, day=1)
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
