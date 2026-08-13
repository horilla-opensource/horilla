"""Talent metrics: recruitment, onboarding, performance."""

from __future__ import annotations

from django.db.models import Count, Q
from django.utils.translation import gettext as _

from report.engine import ReportFilters


def _candidates_in_period(filters: ReportFilters):
    from recruitment.models import Candidate

    qs = Candidate.objects.filter(
        is_active=True,
        created_at__date__gte=filters.from_date,
        created_at__date__lte=filters.to_date,
    )
    if filters.recruitment_id:
        qs = qs.filter(recruitment_id=filters.recruitment_id)
    if filters.gender:
        qs = qs.filter(gender=filters.gender)
    if filters.source:
        qs = qs.filter(source=filters.source)
    if filters.offer_letter_status:
        qs = qs.filter(offer_letter_status=filters.offer_letter_status)
    if filters.job_position_id:
        qs = qs.filter(job_position_id=filters.job_position_id)
    if filters.department_id:
        qs = qs.filter(job_position_id__department_id=filters.department_id)
    if filters.company_id:
        qs = qs.filter(recruitment_id__company_id=filters.company_id)
    return qs


def recruitment_funnel(filters: ReportFilters) -> dict:
    from recruitment.models import Candidate, Recruitment, Stage

    period_cands = _candidates_in_period(filters)
    total = period_cands.count()
    hired = (
        period_cands.filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
        .distinct()
        .count()
    )

    by_stage = list(
        period_cands.filter(stage_id__isnull=False)
        .values("stage_id__stage", "stage_id__stage_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    sources = []
    source_labels = {
        "application": _("Application Form"),
        "software": _("Inside Software"),
        "other": _("Other"),
    }
    for key, label in source_labels.items():
        count = period_cands.filter(source=key).count()
        if count:
            sources.append({"source": label, "count": count})
    referral = period_cands.filter(referral__isnull=False).count()
    if referral:
        sources.append({"source": _("Referral"), "count": referral})

    open_reqs = Recruitment.objects.filter(closed=False).count()
    conversion = round(hired / total * 100, 1) if total else 0

    return {
        "title": _("Recruitment Funnel"),
        "kpis": [
            {"label": _("Candidates"), "value": total, "hint": _("In period")},
            {"label": _("Hired"), "value": hired, "hint": _("In period")},
            {
                "label": _("Conversion"),
                "value": f"{conversion}%",
                "hint": _("Hired / candidates"),
            },
            {"label": _("Open requisitions"), "value": open_reqs, "hint": ""},
        ],
        "charts": [
            {
                "id": "funnel_stages",
                "type": "bar",
                "title": _("Candidates by Stage"),
                "categories": [r["stage_id__stage"] for r in by_stage],
                "series": [
                    {"name": _("Candidates"), "data": [r["count"] for r in by_stage]}
                ],
            },
            {
                "id": "sources",
                "type": "donut",
                "title": _("Source Mix"),
                "categories": [s["source"] for s in sources],
                "series": [
                    {"name": _("Candidates"), "data": [s["count"] for s in sources]}
                ],
            },
        ],
        "table": {
            "columns": [
                {"key": "stage", "label": _("Stage")},
                {"key": "type", "label": _("Type")},
                {"key": "count", "label": _("Count")},
            ],
            "rows": [
                {
                    "stage": r["stage_id__stage"],
                    "type": r["stage_id__stage_type"] or "",
                    "count": r["count"],
                }
                for r in by_stage
            ]
            + [
                {
                    "stage": _("Source: %(s)s") % {"s": s["source"]},
                    "type": "",
                    "count": s["count"],
                }
                for s in sources
            ],
        },
        "explorer_url_name": "recruitment-report",
    }


def time_to_hire(filters: ReportFilters) -> dict:
    from recruitment.models import Recruitment

    period_candidates = _candidates_in_period(filters)
    recruitments = Recruitment.objects.filter(closed=False)
    if filters.recruitment_id:
        recruitments = recruitments.filter(id=filters.recruitment_id)
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
        if not days_list:
            continue
        data.append(
            {
                "recruitment": rec.title or str(rec),
                "avg_days": round(sum(days_list) / len(days_list)),
                "hired_count": hired.count(),
                "min_days": min(days_list),
                "max_days": max(days_list),
            }
        )

    overall_avg = round(sum(d["avg_days"] for d in data) / len(data)) if data else 0

    # Open req aging
    aging = []
    for rec in Recruitment.objects.filter(closed=False):
        created = getattr(rec, "created_at", None)
        if not created:
            continue
        age = (filters.to_date - created.date()).days
        aging.append(
            {
                "recruitment": rec.title or str(rec),
                "vacancy": rec.vacancy or 0,
                "age_days": age,
            }
        )
    aging.sort(key=lambda x: -x["age_days"])

    return {
        "title": _("Time to Hire / Fill"),
        "kpis": [
            {
                "label": _("Avg days to hire"),
                "value": overall_avg,
                "hint": _("Across open recruitments"),
            },
            {
                "label": _("Recruitments measured"),
                "value": len(data),
                "hint": _("With hired candidates"),
            },
            {
                "label": _("Open reqs"),
                "value": len(aging),
                "hint": _("Aging listed in table"),
            },
            {
                "label": _("Oldest open (days)"),
                "value": aging[0]["age_days"] if aging else 0,
                "hint": "",
            },
        ],
        "charts": [
            {
                "id": "tth",
                "type": "bar",
                "title": _("Avg Days to Hire"),
                "categories": [d["recruitment"] for d in data[:12]],
                "series": [
                    {"name": _("Days"), "data": [d["avg_days"] for d in data[:12]]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "recruitment", "label": _("Recruitment")},
                {"key": "avg_days", "label": _("Avg Days")},
                {"key": "hired_count", "label": _("Hired")},
                {"key": "age_days", "label": _("Open Age (days)")},
                {"key": "vacancy", "label": _("Vacancy")},
            ],
            "rows": [
                {
                    "recruitment": d["recruitment"],
                    "avg_days": d["avg_days"],
                    "hired_count": d["hired_count"],
                    "age_days": "",
                    "vacancy": "",
                }
                for d in data
            ]
            + [
                {
                    "recruitment": a["recruitment"],
                    "avg_days": "",
                    "hired_count": "",
                    "age_days": a["age_days"],
                    "vacancy": a["vacancy"],
                }
                for a in aging[:20]
            ],
        },
        "explorer_url_name": "recruitment-report",
    }


def offer_acceptance(filters: ReportFilters) -> dict:
    candidates = _candidates_in_period(filters)
    status_counts = list(
        candidates.values("offer_letter_status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    labels = dict(
        [
            ("not_sent", _("Not Sent")),
            ("sent", _("Sent")),
            ("accepted", _("Accepted")),
            ("rejected", _("Rejected")),
            ("joined", _("Joined")),
        ]
    )
    sent = candidates.filter(
        offer_letter_status__in=["sent", "accepted", "rejected", "joined"]
    ).count()
    accepted = candidates.filter(offer_letter_status__in=["accepted", "joined"]).count()
    rejected = candidates.filter(offer_letter_status="rejected").count()
    rate = round(accepted / sent * 100, 1) if sent else 0

    rows = [
        {
            "status": labels.get(
                r["offer_letter_status"], r["offer_letter_status"] or _("Unknown")
            ),
            "count": r["count"],
        }
        for r in status_counts
    ]

    return {
        "title": _("Offer & Acceptance"),
        "kpis": [
            {"label": _("Offers touched"), "value": sent, "hint": _("Sent or decided")},
            {"label": _("Accepted / joined"), "value": accepted, "hint": ""},
            {"label": _("Rejected"), "value": rejected, "hint": ""},
            {
                "label": _("Acceptance rate"),
                "value": f"{rate}%",
                "hint": _("Accepted÷sent"),
            },
        ],
        "charts": [
            {
                "id": "offer_status",
                "type": "donut",
                "title": _("Offer Letter Status"),
                "categories": [r["status"] for r in rows],
                "series": [
                    {"name": _("Candidates"), "data": [r["count"] for r in rows]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "status", "label": _("Status")},
                {"key": "count", "label": _("Count")},
            ],
            "rows": rows,
        },
        "explorer_url_name": "recruitment-report",
    }


def onboarding_progress(filters: ReportFilters) -> dict:
    from django.apps import apps

    if not apps.is_installed("onboarding"):
        return {
            "title": _("Onboarding Progress"),
            "kpis": [],
            "charts": [],
            "table": {"columns": [], "rows": []},
            "message": _("Onboarding app is not installed."),
        }

    from onboarding.models import CandidateStage, CandidateTask
    from recruitment.models import Candidate

    candidates = Candidate.objects.filter(
        start_onboard=True,
        created_at__date__gte=filters.from_date,
        created_at__date__lte=filters.to_date,
    )
    total = candidates.count()

    stage_rows = list(
        CandidateStage.objects.filter(candidate_id__in=candidates)
        .values("onboarding_stage_id__stage_title")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    if not stage_rows:
        stage_rows = list(
            CandidateStage.objects.values("onboarding_stage_id__stage_title")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

    task_status = list(
        CandidateTask.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    completed_tasks = sum(
        t["count"] for t in task_status if str(t.get("status", "")).lower() == "done"
    )
    total_tasks = sum(t["count"] for t in task_status)
    completion = round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0

    return {
        "title": _("Onboarding Progress"),
        "kpis": [
            {
                "label": _("Onboardees (period)"),
                "value": total,
                "hint": _("start_onboard candidates"),
            },
            {
                "label": _("Task completion"),
                "value": f"{completion}%",
                "hint": _("Completed tasks"),
            },
            {"label": _("Total tasks"), "value": total_tasks, "hint": ""},
            {
                "label": _("Stages tracked"),
                "value": len(stage_rows),
                "hint": "",
            },
        ],
        "charts": [
            {
                "id": "onboard_stages",
                "type": "bar",
                "title": _("Candidates by Onboarding Stage"),
                "categories": [
                    r["onboarding_stage_id__stage_title"] or _("Unknown")
                    for r in stage_rows
                ],
                "series": [
                    {"name": _("Candidates"), "data": [r["count"] for r in stage_rows]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "item", "label": _("Item")},
                {"key": "status", "label": _("Status / Stage")},
                {"key": "count", "label": _("Count")},
            ],
            "rows": [
                {
                    "item": _("Stage"),
                    "status": r["onboarding_stage_id__stage_title"] or _("Unknown"),
                    "count": r["count"],
                }
                for r in stage_rows
            ]
            + [
                {
                    "item": _("Task"),
                    "status": t.get("status") or _("Unknown"),
                    "count": t["count"],
                }
                for t in task_status
            ],
        },
        "explorer_url_name": "recruitment-report",
    }


def performance_distribution(filters: ReportFilters) -> dict:
    from django.db.models import DateField, DateTimeField

    from pms.models import EmployeeKeyResult, EmployeeObjective, Feedback

    def _period_filter(qs, model):
        field = model._meta.get_field("created_at")
        if isinstance(field, DateTimeField):
            return qs.filter(
                created_at__date__gte=filters.from_date,
                created_at__date__lte=filters.to_date,
            )
        if isinstance(field, DateField):
            return qs.filter(
                created_at__gte=filters.from_date,
                created_at__lte=filters.to_date,
            )
        return qs

    objectives = _period_filter(
        EmployeeObjective.objects.filter(archive=False), EmployeeObjective
    )
    obj_status = list(
        objectives.values("status").annotate(count=Count("id")).order_by("-count")
    )

    kr_qs = _period_filter(EmployeeKeyResult.objects.all(), EmployeeKeyResult)
    kr_status = list(
        kr_qs.values("status").annotate(count=Count("id")).order_by("-count")
    )

    feedbacks = _period_filter(Feedback.objects.all(), Feedback)
    fb_status = list(
        feedbacks.values("status").annotate(count=Count("id")).order_by("-count")
    )

    def labelize(rows, prefix):
        return [
            {
                "category": prefix,
                "status": r["status"] or _("Unknown"),
                "count": r["count"],
            }
            for r in rows
        ]

    return {
        "title": _("Performance Distribution"),
        "kpis": [
            {
                "label": _("Objectives"),
                "value": sum(r["count"] for r in obj_status),
                "hint": _("In period"),
            },
            {
                "label": _("Key results"),
                "value": sum(r["count"] for r in kr_status),
                "hint": "",
            },
            {
                "label": _("Feedbacks"),
                "value": sum(r["count"] for r in fb_status),
                "hint": "",
            },
            {
                "label": _("Objective statuses"),
                "value": len(obj_status),
                "hint": "",
            },
        ],
        "charts": [
            {
                "id": "obj_status",
                "type": "donut",
                "title": _("Objective Status"),
                "categories": [r["status"] or _("Unknown") for r in obj_status],
                "series": [
                    {"name": _("Count"), "data": [r["count"] for r in obj_status]}
                ],
            },
            {
                "id": "kr_status",
                "type": "bar",
                "title": _("Key Result Status"),
                "categories": [r["status"] or _("Unknown") for r in kr_status],
                "series": [
                    {"name": _("Count"), "data": [r["count"] for r in kr_status]}
                ],
            },
        ],
        "table": {
            "columns": [
                {"key": "category", "label": _("Category")},
                {"key": "status", "label": _("Status")},
                {"key": "count", "label": _("Count")},
            ],
            "rows": (
                labelize(obj_status, _("Objective"))
                + labelize(kr_status, _("Key Result"))
                + labelize(fb_status, _("Feedback"))
            ),
        },
        "explorer_url_name": "pms-report",
    }


def recruitment_funnel_drilldown(
    filters: ReportFilters, params: dict, request=None
) -> dict:
    """Drill recruitment funnel by stage name or source label."""
    from report.drilldown import candidate_link, drilldown_payload, empty_drilldown

    dimension = (params.get("dimension") or "stage").strip().lower()
    value = (params.get("value") or "").strip()
    if not value:
        return empty_drilldown(
            _("Recruitment Funnel"), dimension, value, _("Missing dimension value.")
        )

    qs = _candidates_in_period(filters)
    # Candidates are not employee-subordinate scoped the same way; keep org filters only.
    title = _("Recruitment Funnel")
    if dimension in ("stage", "funnel_stages"):
        qs = qs.filter(stage_id__stage=value)
        dimension = "stage"
        title = _("Candidates · stage %(s)s") % {"s": value}
    elif dimension in ("source", "sources"):
        # Reverse display labels used in recruitment_funnel
        source_map = {
            str(_("Application Form")): "application",
            str(_("Inside Software")): "software",
            str(_("Other")): "other",
            "Application Form": "application",
            "Inside Software": "software",
            "Other": "other",
            "application": "application",
            "software": "software",
            "other": "other",
        }
        if value in (str(_("Referral")), "Referral"):
            qs = qs.filter(referral__isnull=False)
        else:
            key = source_map.get(value, value)
            qs = qs.filter(source=key)
        dimension = "source"
        title = _("Candidates · source %(s)s") % {"s": value}
    else:
        return empty_drilldown(title, dimension, value, _("Unsupported dimension."))

    limit = int((params.get("limit") or filters.extra.get("row_limit") or 200))
    total = qs.count()
    rows = []
    for cand in qs.select_related("stage_id", "recruitment_id").order_by("-created_at")[
        :limit
    ]:
        rows.append(
            {
                "candidate": str(cand),
                "stage": getattr(getattr(cand, "stage_id", None), "stage", "") or "",
                "source": cand.source or "",
                "hired": _("Yes") if getattr(cand, "hired", False) else _("No"),
                "link": candidate_link(cand.id),
            }
        )
    return drilldown_payload(
        title=title,
        dimension=dimension,
        value=value,
        columns=[
            {"key": "candidate", "label": _("Candidate")},
            {"key": "stage", "label": _("Stage")},
            {"key": "source", "label": _("Source")},
            {"key": "hired", "label": _("Hired")},
            {"key": "link", "label": _("Open"), "type": "link"},
        ],
        rows=rows,
        truncated=total > len(rows),
    )
