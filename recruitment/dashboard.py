"""
Modern recruitment dashboard views — KPI summary + ApexCharts.

Accessible at /recruitment/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from employee.models import Employee
from horilla.methods import handle_no_permission
from recruitment.models import Recruitment, Stage


def _has_recruitment_permission(request):
    """Return True if the user may access the recruitment dashboard."""
    user = request.user
    if user.is_superuser or user.has_perm("recruitment.view_recruitment"):
        return True
    employee = Employee.objects.filter(employee_user_id=user).first()
    return employee is not None and (
        Stage.objects.filter(stage_managers=employee).exists()
        or Recruitment.objects.filter(recruitment_managers=employee).exists()
    )


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


def _upcoming_interview_period(request):
    """Like _parse_period, but defaults to a forward-looking window.

    This widget shows *upcoming* interviews -- _parse_period's generic
    [month-start, today] default (built for the dashboard's other,
    backward-looking widgets) can never show anything scheduled in the
    future, even though interviews are deliberately scheduled ahead. Only
    applies when neither from_date nor to_date was explicitly requested, so
    an actual date-range-picker selection is still honored exactly as
    before.
    """
    if not request.GET.get("from_date") and not request.GET.get("to_date"):
        today = date.today()
        return today, today + timedelta(days=30)
    return _parse_period(request)


def _candidates_in_period(request):
    """Return Candidate queryset filtered to the requested period (by created_at)."""
    from recruitment.models import Candidate

    from_date, to_date = _parse_period(request)
    return Candidate.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )


@login_required
def recruitment_dashboard_view(request):
    """Render the modern recruitment dashboard page."""
    if not _has_recruitment_permission(request):
        return handle_no_permission(request)
    return render(request, "recruitment/dashboard.html")


@login_required
def recruitment_kpi_data(request):
    """Return recruitment KPI summary data as JSON."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False, is_event_based=False)
    ongoing = recruitments.count()

    total_vacancy = 0
    for rec in recruitments:
        if rec.vacancy is not None:
            total_vacancy += rec.vacancy

    from_date, to_date = _parse_period(request)
    candidates = _candidates_in_period(request)
    total_candidates = candidates.count()

    hired_candidates = candidates.filter(
        Q(hired=True) | Q(stage_id__stage_type="hired")
    ).distinct()
    total_hired = hired_candidates.count()

    conversion_rate = 0
    if total_candidates > 0:
        conversion_rate = round((total_hired / total_candidates) * 100, 1)

    acceptance_rate = 0
    accepted = 0
    try:
        accepted = candidates.filter(offer_letter_status="accepted").count()
        if total_hired > 0:
            acceptance_rate = round((accepted / total_hired) * 100, 1)
    except Exception:
        pass

    onboarding_count = 0
    try:
        onboarding_count = hired_candidates.filter(start_onboard=True).count()
    except Exception:
        pass

    return JsonResponse(
        {
            "total_vacancy": total_vacancy,
            "ongoing_recruitments": ongoing,
            "total_hired": total_hired,
            "total_candidates": total_candidates,
            "conversion_rate": conversion_rate,
            "acceptance_rate": acceptance_rate,
            "accepted_count": accepted,
            "onboarding_count": onboarding_count,
            # Echoed back so the "Hired"/"Acceptance Rate" cards' click-
            # throughs can filter to the exact same period the counts
            # above were computed from, instead of showing all-time data.
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
def recruitment_offer_status(request):
    """Candidate offer letter status breakdown."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Candidate

    statuses = ["not_sent", "sent", "accepted", "rejected", "joined"]
    labels = [_("Not Sent"), _("Sent"), _("Accepted"), _("Rejected"), _("Joined")]
    data = []

    base_qs = Candidate.objects.filter(is_active=True)
    for status in statuses:
        data.append(base_qs.filter(offer_letter_status=status).count())

    return JsonResponse({"labels": labels, "data": data, "statuses": statuses})


@login_required
def recruitment_stage_summary(request):
    """Candidates grouped by stage type across all active recruitments."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False)

    stages = []
    for type_key, type_label in Stage.stage_types:
        count = Candidate.objects.filter(
            stage_id__stage_type=type_key,
            is_active=True,
        ).count()
        stages.append({"type": type_key, "label": str(type_label), "count": count})

    return JsonResponse({"stages": stages})


@login_required
def recruitment_pipeline_data(request):
    """Hiring pipeline — candidates per stage per recruitment."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False)
    period_candidates = _candidates_in_period(request)
    pipeline = []

    for rec in recruitments:
        rec_cands = period_candidates.filter(recruitment_id=rec)
        total = rec_cands.count()
        if not total:
            continue
        stages = {}
        for stage_type, stage_label in Stage.stage_types:
            stages[stage_type] = rec_cands.filter(
                stage_id__stage_type=stage_type
            ).count()
        pipeline.append(
            {
                "id": rec.id,
                "recruitment": rec.title or str(rec),
                "stages": stages,
                "total": total,
            }
        )

    return JsonResponse({"pipeline": pipeline, "stage_types": dict(Stage.stage_types)})


@login_required
def recruitment_source_quality(request):
    """Top recruitments by hire rate."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    period_candidates = _candidates_in_period(request)
    sources = []

    for rec in recruitments:
        rec_cands = period_candidates.filter(recruitment_id=rec)
        total = rec_cands.count()
        if total == 0:
            continue
        hired = (
            rec_cands.filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
            .distinct()
            .count()
        )
        rate = round((hired / total) * 100, 1) if total > 0 else 0
        sources.append(
            {
                "recruitment": rec.title or str(rec),
                "total": total,
                "hired": hired,
                "rate": rate,
            }
        )

    sources.sort(key=lambda x: x["rate"], reverse=True)

    return JsonResponse({"sources": sources[:10]})


@login_required
def recruitment_time_to_hire(request):
    """Average time from candidate creation to hired stage, per recruitment."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    period_candidates = _candidates_in_period(request)
    data = []

    for rec in recruitments:
        hired = (
            period_candidates.filter(recruitment_id=rec)
            .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
            .distinct()
        )
        if not hired.exists():
            continue

        days_list = []
        for c in hired:
            if c.joining_date and c.created_at:
                try:
                    delta = (c.joining_date - c.created_at.date()).days
                    if delta >= 0:
                        days_list.append(delta)
                except Exception:
                    pass

        avg_days = round(sum(days_list) / len(days_list)) if days_list else None
        data.append(
            {
                "recruitment": rec.title or str(rec),
                "avg_days": avg_days,
                "hired_count": hired.count(),
            }
        )

    return JsonResponse({"data": [d for d in data if d["avg_days"] is not None]})


@login_required
def recruitment_managers_data(request):
    """Ongoing recruitments with their managers."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    period_candidates = _candidates_in_period(request)
    data = []

    for rec in recruitments:
        managers = [m.get_full_name() for m in rec.recruitment_managers.all()]
        data.append(
            {
                "recruitment": rec.title or str(rec),
                "managers": managers,
                "vacancy": rec.vacancy or 0,
                "candidates": period_candidates.filter(recruitment_id=rec).count(),
            }
        )

    return JsonResponse({"recruitments": data})


@login_required
def recruitment_source_of_hire(request):
    """Candidate count grouped by source (Application, Inside software, Other)."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from django.db.models import Q

    from recruitment.models import Candidate

    base_qs = Candidate.objects.filter(is_active=True)
    sources = []

    try:
        source_labels = {
            "application": _("Application Form"),
            "software": _("Inside Software"),
            "other": _("Other"),
        }

        for key, label in source_labels.items():
            count = base_qs.filter(source=key).count()
            if count > 0:
                sources.append({"source": label, "key": key, "count": count})

        referral_count = base_qs.filter(referral__isnull=False).count()
        if referral_count > 0:
            sources.append(
                {"source": _("Referral"), "key": "referral", "count": referral_count}
            )

        not_set_count = base_qs.filter(
            Q(source__isnull=True) | Q(source=""), referral__isnull=True
        ).count()
        if not_set_count > 0:
            sources.append(
                {
                    "source": _("Not Specified"),
                    "key": "not_set",
                    "count": not_set_count,
                }
            )

        sources.sort(key=lambda x: x["count"], reverse=True)

    except Exception:
        pass

    return JsonResponse({"sources": sources})


@login_required
def recruitment_upcoming_interviews(request):
    """Interviews scheduled within the selected period."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import InterviewSchedule

    from_date, to_date = _upcoming_interview_period(request)
    today = date.today()
    interviews = []

    try:
        qs = (
            InterviewSchedule.objects.filter(
                interview_date__gte=from_date,
                interview_date__lte=to_date,
            )
            .select_related("candidate_id", "candidate_id__stage_id")
            .order_by("interview_date", "interview_time")[:15]
        )

        for iv in qs:
            cand = iv.candidate_id
            interviews.append(
                {
                    "id": iv.id,
                    "candidate": cand.name if cand else "—",
                    "candidate_id": cand.id if cand else None,
                    "stage": cand.stage_id.stage if cand and cand.stage_id else "—",
                    "date": iv.interview_date.strftime("%b %d"),
                    "time": (
                        iv.interview_time.strftime("%I:%M %p")
                        if iv.interview_time
                        else ""
                    ),
                    "days_away": (iv.interview_date - today).days,
                }
            )
    except Exception:
        pass

    return JsonResponse({"interviews": interviews})


@login_required
def recruitment_open_by_department(request):
    """Open positions grouped by department, scoped to recruitments active in the selected period."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from base.models import Department
    from recruitment.models import Recruitment

    from_date, to_date = _parse_period(request)
    departments = []

    try:
        recruitments = Recruitment.objects.filter(
            closed=False,
            is_event_based=False,
            start_date__lte=to_date,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=from_date))

        dept_data = {}
        for rec in recruitments:
            vacancy = rec.vacancy or 0
            filled = (
                rec.candidate.filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
                .distinct()
                .count()
            )
            open_count = max(0, vacancy - filled)

            if rec.job_position_id and rec.job_position_id.department_id:
                dept_name = rec.job_position_id.department_id.department
            else:
                dept_name = "Unassigned"

            if dept_name not in dept_data:
                dept_data[dept_name] = {"open": 0, "total_vacancy": 0, "filled": 0}
            dept_data[dept_name]["open"] += open_count
            dept_data[dept_name]["total_vacancy"] += vacancy
            dept_data[dept_name]["filled"] += filled

        for dept, counts in dept_data.items():
            if counts["total_vacancy"] > 0:
                departments.append(
                    {
                        "department": dept,
                        "open": counts["open"],
                        "filled": counts["filled"],
                        "total": counts["total_vacancy"],
                    }
                )

        departments.sort(key=lambda x: x["open"], reverse=True)
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def recruitment_stage_conversion(request):
    """Funnel conversion rates between stages."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from recruitment.models import Candidate, Stage

    conversions = []

    try:
        stage_types = [st[0] for st in Stage.stage_types]
        stage_labels = dict(Stage.stage_types)

        counts = {}
        for st in stage_types:
            counts[st] = Candidate.objects.filter(
                stage_id__stage_type=st,
                is_active=True,
            ).count()

        total = Candidate.objects.filter(
            is_active=True,
            canceled=False,
        ).count()

        # Each stage_type is an independent category a candidate's current
        # stage falls into (not a nested cohort that must first pass through
        # every earlier stage_type), so "% of previous stage" can exceed
        # 100% whenever a later, wider stage (e.g. "Applied") holds more
        # candidates than an earlier, narrower one (e.g. "Initial"). Share of
        # the total pool is the metric that's actually well-defined here and
        # is naturally bounded to 0-100%.
        for st in stage_types:
            current = counts.get(st, 0)
            rate = round((current / total * 100), 1) if total > 0 else 0
            conversions.append(
                {
                    "stage": str(stage_labels.get(st, st)),
                    "type": st,
                    "count": current,
                    "conversion_rate": rate,
                }
            )
    except Exception:
        pass

    return JsonResponse(
        {
            "conversions": conversions,
            "total_candidates": conversions[0]["count"] if conversions else 0,
        }
    )


@login_required
def recruitment_source_conversion(request):
    """Hire rate per candidate source."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from django.db.models import Q

    candidates = _candidates_in_period(request)

    sources = []
    try:
        source_choices = [
            ("application", _("Application Form")),
            ("software", _("Inside Software")),
            ("other", _("Other")),
        ]
        for key, label in source_choices:
            total = candidates.filter(source=key).count()
            hired = (
                candidates.filter(source=key)
                .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
                .distinct()
                .count()
            )
            rate = round((hired / total * 100), 1) if total > 0 else 0
            if total > 0:
                sources.append(
                    {"source": label, "total": total, "hired": hired, "rate": rate}
                )
        # Referrals
        total_ref = candidates.filter(referral__isnull=False).count()
        hired_ref = (
            candidates.filter(referral__isnull=False)
            .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
            .distinct()
            .count()
        )
        if total_ref > 0:
            sources.append(
                {
                    "source": _("Referral"),
                    "total": total_ref,
                    "hired": hired_ref,
                    "rate": round((hired_ref / total_ref * 100), 1),
                }
            )

        # Not Specified — candidates with no source and no referral
        total_ns = candidates.filter(
            Q(source__isnull=True) | Q(source=""), referral__isnull=True
        ).count()
        if total_ns > 0:
            hired_ns = (
                candidates.filter(
                    Q(source__isnull=True) | Q(source=""), referral__isnull=True
                )
                .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
                .distinct()
                .count()
            )
            sources.append(
                {
                    "source": _("Not Specified"),
                    "total": total_ns,
                    "hired": hired_ns,
                    "rate": round((hired_ns / total_ns * 100), 1),
                }
            )
    except Exception:
        pass
    return JsonResponse({"sources": sources})


@login_required
def recruitment_joinings_monthly(request):
    """Employee joinings grouped by month within the selected period."""
    if not _has_recruitment_permission(request):
        return JsonResponse({"no_permission": True})
    from employee.models import EmployeeWorkInformation

    from_date, to_date = _parse_period(request)

    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    buckets = []
    cursor = date(from_date.year, from_date.month, 1)
    end_marker = date(to_date.year, to_date.month, 1)
    while cursor <= end_marker:
        buckets.append({"year": cursor.year, "month": cursor.month, "count": 0})
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    qs = EmployeeWorkInformation.objects.filter(
        date_joining__gte=from_date,
        date_joining__lte=to_date,
    )
    for info in qs:
        if not info.date_joining:
            continue
        for b in buckets:
            if (
                b["year"] == info.date_joining.year
                and b["month"] == info.date_joining.month
            ):
                b["count"] += 1
                break

    multi_year = from_date.year != to_date.year
    labels = [
        (
            f"{month_names[b['month'] - 1][:3]} {b['year']}"
            if multi_year
            else month_names[b["month"] - 1]
        )
        for b in buckets
    ]
    data = [b["count"] for b in buckets]

    return JsonResponse({"labels": labels, "data": data, "buckets": buckets})
