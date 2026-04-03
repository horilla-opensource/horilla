"""
Modern recruitment dashboard views — KPI summary + ApexCharts.

Accessible at /recruitment/dashboard/modern/ alongside the existing dashboard.
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
def modern_recruitment_dashboard(request):
    """Render the modern recruitment dashboard page."""
    return render(request, "recruitment/dashboard_modern.html")


@login_required
def recruitment_kpi_data(request):
    """Return recruitment KPI summary data as JSON."""
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False, is_event_based=False)
    ongoing = recruitments.count()

    total_vacancy = 0
    for rec in recruitments:
        if rec.vacancy is not None:
            total_vacancy += rec.vacancy

    candidates = Candidate.objects.all()
    total_candidates = candidates.count()

    hired_candidates = candidates.filter(
        Q(hired=True) | Q(stage_id__stage_type="hired")
    ).distinct()
    total_hired = hired_candidates.count()

    conversion_rate = 0
    if total_candidates > 0:
        conversion_rate = round((total_hired / total_candidates) * 100, 1)

    acceptance_rate = 0
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
            "onboarding_count": onboarding_count,
        }
    )


@login_required
def recruitment_offer_status(request):
    """Candidate offer letter status breakdown."""
    from recruitment.models import Candidate

    statuses = ["not_sent", "sent", "accepted", "rejected", "joined"]
    labels = ["Not Sent", "Sent", "Accepted", "Rejected", "Joined"]
    data = []

    for status in statuses:
        data.append(Candidate.objects.filter(offer_letter_status=status).count())

    return JsonResponse({"labels": labels, "data": data, "statuses": statuses})


@login_required
def recruitment_stage_summary(request):
    """Candidates grouped by stage type across all active recruitments."""
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False)
    stage_types = dict(Stage.stage_types)

    stages = []
    for type_key, type_label in Stage.stage_types:
        count = Candidate.objects.filter(
            recruitment_id__in=recruitments,
            stage_id__stage_type=type_key,
        ).count()
        stages.append({"type": type_key, "label": str(type_label), "count": count})

    return JsonResponse({"stages": stages})


@login_required
def recruitment_pipeline_data(request):
    """Hiring pipeline — candidates per stage per recruitment."""
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False)
    pipeline = []

    for rec in recruitments:
        if not rec.candidate.exists():
            continue
        stages = {}
        for stage_type, stage_label in Stage.stage_types:
            count = rec.candidate.filter(stage_id__stage_type=stage_type).count()
            stages[stage_type] = count
        pipeline.append(
            {
                "recruitment": rec.title or str(rec),
                "stages": stages,
                "total": rec.candidate.count(),
            }
        )

    return JsonResponse({"pipeline": pipeline, "stage_types": dict(Stage.stage_types)})


@login_required
def recruitment_source_quality(request):
    """Top recruitments by hire rate."""
    from recruitment.models import Candidate, Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    sources = []

    for rec in recruitments:
        total = rec.candidate.count()
        if total == 0:
            continue
        hired = (
            rec.candidate.filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
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
    from recruitment.models import Candidate, Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    data = []

    for rec in recruitments:
        hired = rec.candidate.filter(
            Q(hired=True) | Q(stage_id__stage_type="hired")
        ).distinct()
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
    from recruitment.models import Recruitment

    recruitments = Recruitment.objects.filter(closed=False)
    data = []

    for rec in recruitments:
        managers = [m.get_full_name() for m in rec.recruitment_managers.all()]
        data.append(
            {
                "recruitment": rec.title or str(rec),
                "managers": managers,
                "vacancy": rec.vacancy or 0,
                "candidates": rec.candidate.count(),
            }
        )

    return JsonResponse({"recruitments": data})


@login_required
def recruitment_source_of_hire(request):
    """Candidate count grouped by source (Application, Inside software, Other)."""
    from recruitment.models import Candidate

    sources = []

    try:
        data = (
            Candidate.objects.exclude(source__isnull=True)
            .exclude(source="")
            .values("source")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        source_labels = {
            "application": "Application Form",
            "software": "Inside Software",
            "other": "Other",
        }

        for item in data:
            sources.append(
                {
                    "source": source_labels.get(item["source"], item["source"]),
                    "key": item["source"],
                    "count": item["count"],
                }
            )

        # Add referral count separately
        referral_count = Candidate.objects.filter(referral__isnull=False).count()
        if referral_count > 0:
            sources.append(
                {
                    "source": "Referral",
                    "key": "referral",
                    "count": referral_count,
                }
            )
    except Exception:
        pass

    return JsonResponse({"sources": sources})


@login_required
def recruitment_upcoming_interviews(request):
    """Interviews scheduled in the next 7 days."""
    from recruitment.models import InterviewSchedule

    today = date.today()
    end = today + timedelta(days=7)
    interviews = []

    try:
        qs = (
            InterviewSchedule.objects.filter(
                interview_date__gte=today,
                interview_date__lte=end,
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
    """Open positions grouped by department."""
    from base.models import Department
    from recruitment.models import Recruitment

    departments = []

    try:
        recruitments = Recruitment.objects.filter(closed=False, is_event_based=False)

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
    from recruitment.models import Candidate, Recruitment, Stage

    recruitments = Recruitment.objects.filter(closed=False)
    conversions = []

    try:
        stage_types = [st[0] for st in Stage.stage_types]
        stage_labels = dict(Stage.stage_types)

        counts = {}
        for st in stage_types:
            counts[st] = Candidate.objects.filter(
                recruitment_id__in=recruitments,
                stage_id__stage_type=st,
            ).count()

        # Also count total candidates
        total = Candidate.objects.filter(
            recruitment_id__in=recruitments,
            canceled=False,
        ).count()

        prev_count = total
        for st in stage_types:
            current = counts.get(st, 0)
            rate = round((current / prev_count * 100), 1) if prev_count > 0 else 0
            conversions.append(
                {
                    "stage": str(stage_labels.get(st, st)),
                    "type": st,
                    "count": current,
                    "conversion_rate": rate,
                }
            )
            if current > 0:
                prev_count = current
    except Exception:
        pass

    return JsonResponse(
        {
            "conversions": conversions,
            "total_candidates": total if "total" in dir() else 0,
        }
    )


@login_required
def recruitment_source_conversion(request):
    """Hire rate per candidate source."""
    from django.db.models import Q

    from recruitment.models import Candidate

    sources = []
    try:
        source_choices = [
            ("application", "Application Form"),
            ("software", "Inside Software"),
            ("other", "Other"),
        ]
        for key, label in source_choices:
            total = Candidate.objects.filter(source=key).count()
            hired = (
                Candidate.objects.filter(source=key)
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
        total_ref = Candidate.objects.filter(referral__isnull=False).count()
        hired_ref = (
            Candidate.objects.filter(referral__isnull=False)
            .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
            .distinct()
            .count()
        )
        if total_ref > 0:
            sources.append(
                {
                    "source": "Referral",
                    "total": total_ref,
                    "hired": hired_ref,
                    "rate": round((hired_ref / total_ref * 100), 1),
                }
            )
    except Exception:
        pass
    return JsonResponse({"sources": sources})
