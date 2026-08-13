"""Workforce / employee analytics metrics."""

from __future__ import annotations

from collections import Counter
from datetime import date

from django.db.models import Count, Q
from django.utils.translation import gettext as _

from report.engine import (
    ReportFilters,
    apply_org_filters,
    empty_report,
    iter_months,
    month_offset,
)


def _work_info(filters: ReportFilters):
    from employee.models import EmployeeWorkInformation

    return apply_org_filters(
        EmployeeWorkInformation.objects.all(),
        filters,
        prefix="",
        employee_prefix="employee_id",
    )


def _employees(filters: ReportFilters, *, apply_status: bool = True):
    from employee.models import Employee

    return apply_org_filters(
        Employee.objects.all(),
        filters,
        prefix="employee_work_info",
        employee_prefix="",
        apply_employment_status=apply_status,
    )


def workforce_composition(filters: ReportFilters) -> dict:
    from employee.models import Employee

    work_info = _work_info(filters)
    active = _employees(filters)
    headcount = active.count()

    by_dept = list(
        work_info.filter(department_id__isnull=False)
        .values("department_id__department")
        .annotate(count=Count("employee_id", distinct=True))
        .order_by("-count")
    )
    by_type = list(
        work_info.filter(employee_type_id__isnull=False)
        .values("employee_type_id__employee_type")
        .annotate(count=Count("employee_id", distinct=True))
        .order_by("-count")
    )
    by_job = list(
        work_info.filter(job_position_id__isnull=False)
        .values("job_position_id__job_position")
        .annotate(count=Count("employee_id", distinct=True))
        .order_by("-count")[:15]
    )
    by_location = list(
        work_info.filter(location__isnull=False)
        .exclude(location="")
        .values("location")
        .annotate(count=Count("employee_id", distinct=True))
        .order_by("-count")[:15]
    )

    # FTE proxy: count full-time-ish types containing "full" else treat as 0.5
    fte = 0.0
    for row in by_type:
        label = (row["employee_type_id__employee_type"] or "").lower()
        weight = 1.0 if "full" in label or "permanent" in label else 0.5
        if "part" in label or "intern" in label or "contract" in label:
            weight = 0.5
        fte += row["count"] * weight
    if not by_type:
        fte = float(headcount)

    return {
        "title": _("Workforce Composition"),
        "kpis": [
            {
                "label": _("Headcount"),
                "value": headcount,
                "hint": _("Active employees"),
            },
            {
                "label": _("FTE (proxy)"),
                "value": round(fte, 1),
                "hint": _("From employee type"),
            },
            {
                "label": _("Departments"),
                "value": len(by_dept),
                "hint": _("With active staff"),
            },
            {
                "label": _("Job positions"),
                "value": len(by_job),
                "hint": _("Top roles shown in table"),
            },
        ],
        "charts": [
            {
                "id": "by_dept",
                "type": "bar",
                "title": _("Headcount by Department"),
                "categories": [r["department_id__department"] for r in by_dept[:12]],
                "series": [
                    {
                        "name": _("Employees"),
                        "data": [r["count"] for r in by_dept[:12]],
                    }
                ],
            },
            {
                "id": "by_type",
                "type": "donut",
                "title": _("By Employee Type"),
                "categories": [r["employee_type_id__employee_type"] for r in by_type],
                "series": [
                    {
                        "name": _("Employees"),
                        "data": [r["count"] for r in by_type],
                    }
                ],
            },
        ],
        "table": {
            "columns": [
                {"key": "dimension", "label": _("Dimension")},
                {"key": "value", "label": _("Value")},
                {"key": "count", "label": _("Count")},
            ],
            "rows": (
                [
                    {
                        "dimension": _("Department"),
                        "value": r["department_id__department"],
                        "count": r["count"],
                    }
                    for r in by_dept
                ]
                + [
                    {
                        "dimension": _("Job Position"),
                        "value": r["job_position_id__job_position"],
                        "count": r["count"],
                    }
                    for r in by_job
                ]
                + [
                    {
                        "dimension": _("Location"),
                        "value": r["location"],
                        "count": r["count"],
                    }
                    for r in by_location
                ]
            ),
        },
        "explorer_url_name": "employee-report",
    }


def diversity_snapshot(filters: ReportFilters) -> dict:
    from employee.models import Employee

    employees = _employees(filters)
    total = employees.count()
    if not total:
        return empty_report(_("Diversity Snapshot"), filters, _("No active employees."))

    gender_counts = Counter(employees.values_list("gender", flat=True))
    gender_labels = {"male": _("Male"), "female": _("Female"), "other": _("Other")}
    genders = [
        {
            "key": g or "unknown",
            "label": gender_labels.get(g, g or _("Unknown")),
            "count": c,
            "pct": round(c / total * 100, 1),
        }
        for g, c in gender_counts.items()
        if c > 0
    ]
    genders.sort(key=lambda x: -x["count"])

    today = filters.to_date
    age_bands = {
        _("Under 25"): 0,
        _("25–34"): 0,
        _("35–44"): 0,
        _("45–54"): 0,
        _("55+"): 0,
        _("Unknown"): 0,
    }
    for dob in employees.values_list("dob", flat=True):
        if not dob:
            age_bands[_("Unknown")] += 1
            continue
        age = (today - dob).days // 365
        if age < 25:
            age_bands[_("Under 25")] += 1
        elif age < 35:
            age_bands[_("25–34")] += 1
        elif age < 45:
            age_bands[_("35–44")] += 1
        elif age < 55:
            age_bands[_("45–54")] += 1
        else:
            age_bands[_("55+")] += 1

    marital = Counter(employees.values_list("marital_status", flat=True))

    # Leadership gender: employees who are reporting managers
    managers = employees.filter(
        id__in=employees.exclude(
            employee_work_info__reporting_manager_id__isnull=True
        ).values_list("employee_work_info__reporting_manager_id", flat=True)
    )
    mgr_gender = Counter(managers.values_list("gender", flat=True))

    female_pct = next((g["pct"] for g in genders if g["key"] == "female"), 0)

    return {
        "title": _("Diversity Snapshot"),
        "kpis": [
            {"label": _("Headcount"), "value": total, "hint": _("Active")},
            {
                "label": _("Female %"),
                "value": f"{female_pct}%",
                "hint": _("Of active workforce"),
            },
            {
                "label": _("Managers"),
                "value": managers.count(),
                "hint": _("Reporting managers"),
            },
            {
                "label": _("Age known"),
                "value": total - age_bands[_("Unknown")],
                "hint": _("With date of birth"),
            },
        ],
        "charts": [
            {
                "id": "gender",
                "type": "donut",
                "title": _("Gender Distribution"),
                "categories": [g["label"] for g in genders],
                "series": [
                    {"name": _("Employees"), "data": [g["count"] for g in genders]}
                ],
            },
            {
                "id": "age",
                "type": "bar",
                "title": _("Age Bands"),
                "categories": list(age_bands.keys()),
                "series": [{"name": _("Employees"), "data": list(age_bands.values())}],
            },
        ],
        "table": {
            "columns": [
                {"key": "category", "label": _("Category")},
                {"key": "value", "label": _("Value")},
                {"key": "count", "label": _("Count")},
                {"key": "pct", "label": _("%")},
            ],
            "rows": (
                [
                    {
                        "category": _("Gender"),
                        "value": g["label"],
                        "count": g["count"],
                        "pct": g["pct"],
                    }
                    for g in genders
                ]
                + [
                    {
                        "category": _("Age"),
                        "value": band,
                        "count": count,
                        "pct": round(count / total * 100, 1) if total else 0,
                    }
                    for band, count in age_bands.items()
                    if count
                ]
                + [
                    {
                        "category": _("Marital status"),
                        "value": status or _("Unknown"),
                        "count": count,
                        "pct": round(count / total * 100, 1),
                    }
                    for status, count in marital.items()
                    if count
                ]
                + [
                    {
                        "category": _("Leadership gender"),
                        "value": gender_labels.get(g, g or _("Unknown")),
                        "count": c,
                        "pct": (
                            round(c / managers.count() * 100, 1)
                            if managers.count()
                            else 0
                        ),
                    }
                    for g, c in mgr_gender.items()
                    if c
                ]
            ),
        },
        "explorer_url_name": "employee-report",
    }


def tenure_longevity(filters: ReportFilters) -> dict:
    from employee.models import EmployeeWorkInformation

    work_info = _work_info(filters).exclude(date_joining__isnull=True)
    today = filters.to_date
    bands = {
        _("0–1 years"): 0,
        _("1–3 years"): 0,
        _("3–5 years"): 0,
        _("5–10 years"): 0,
        _("10+ years"): 0,
    }
    tenures = []
    by_dept: dict[str, list[float]] = {}

    for row in work_info.select_related("department_id").values(
        "date_joining", "department_id__department"
    ):
        joining = row["date_joining"]
        years = (today - joining).days / 365.25
        tenures.append(years)
        dept = row["department_id__department"] or _("Unassigned")
        by_dept.setdefault(dept, []).append(years)
        if years < 1:
            bands[_("0–1 years")] += 1
        elif years < 3:
            bands[_("1–3 years")] += 1
        elif years < 5:
            bands[_("3–5 years")] += 1
        elif years < 10:
            bands[_("5–10 years")] += 1
        else:
            bands[_("10+ years")] += 1

    avg_tenure = round(sum(tenures) / len(tenures), 1) if tenures else 0
    dept_rows = [
        {
            "department": dept,
            "count": len(vals),
            "avg_tenure": round(sum(vals) / len(vals), 1),
        }
        for dept, vals in sorted(by_dept.items(), key=lambda x: -len(x[1]))
    ]

    return {
        "title": _("Tenure & Longevity"),
        "kpis": [
            {
                "label": _("Avg tenure (yrs)"),
                "value": avg_tenure,
                "hint": _("Active employees with joining date"),
            },
            {
                "label": _("With joining date"),
                "value": len(tenures),
                "hint": _("Included in calculation"),
            },
            {
                "label": _("Under 1 year"),
                "value": bands[_("0–1 years")],
                "hint": _("New joiners band"),
            },
            {
                "label": _("10+ years"),
                "value": bands[_("10+ years")],
                "hint": _("Long-tenure cohort"),
            },
        ],
        "charts": [
            {
                "id": "tenure_bands",
                "type": "bar",
                "title": _("Tenure Bands"),
                "categories": list(bands.keys()),
                "series": [{"name": _("Employees"), "data": list(bands.values())}],
            }
        ],
        "table": {
            "columns": [
                {"key": "department", "label": _("Department")},
                {"key": "count", "label": _("Headcount")},
                {"key": "avg_tenure", "label": _("Avg Tenure (yrs)")},
            ],
            "rows": dept_rows,
        },
        "explorer_url_name": "employee-report",
    }


def turnover_attrition(filters: ReportFilters) -> dict:
    from employee.models import Employee, EmployeeWorkInformation

    months = []
    for month_start, month_end, label in iter_months(filters.to_date, 6):
        hires_qs = EmployeeWorkInformation.objects.filter(
            date_joining__gte=month_start,
            date_joining__lte=month_end,
        )
        hires_qs = apply_org_filters(
            hires_qs, filters, prefix="", employee_prefix="employee_id"
        )
        hires = hires_qs.count()

        exits_qs = Employee.objects.filter(is_active=False).filter(
            Q(employee_work_info__contract_end_date__gte=month_start)
            & Q(employee_work_info__contract_end_date__lte=month_end)
        )
        exits_qs = apply_org_filters(
            exits_qs,
            filters,
            prefix="employee_work_info",
            employee_prefix="",
            apply_employment_status=False,
        )
        exits = exits_qs.count()
        months.append(
            {"month": label, "hires": hires, "exits": exits, "net": hires - exits}
        )

    active_qs = _employees(filters)
    total_employees = active_qs.count()
    total_exits = sum(m["exits"] for m in months)
    turnover_rate = (
        round(total_exits / total_employees * 100, 1) if total_employees else 0
    )

    # First-year turnover proxy: inactive with joining within 365 days of contract end
    first_year = 0
    window_start = month_offset(filters.to_date, 5)
    inactive = apply_org_filters(
        Employee.objects.filter(is_active=False).select_related("employee_work_info"),
        filters,
        prefix="employee_work_info",
        employee_prefix="",
        apply_employment_status=False,
    )
    for emp in inactive.iterator():
        wi = getattr(emp, "employee_work_info", None)
        if not wi or not wi.date_joining or not wi.contract_end_date:
            continue
        if (wi.contract_end_date - wi.date_joining).days <= 365:
            if window_start <= wi.contract_end_date <= filters.to_date:
                first_year += 1

    by_dept = list(
        apply_org_filters(
            Employee.objects.filter(
                is_active=False,
                employee_work_info__contract_end_date__gte=filters.from_date,
                employee_work_info__contract_end_date__lte=filters.to_date,
            ),
            filters,
            prefix="employee_work_info",
            employee_prefix="",
            apply_employment_status=False,
        )
        .values("employee_work_info__department_id__department")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        "title": _("Turnover & Attrition"),
        "kpis": [
            {
                "label": _("Turnover rate (6m)"),
                "value": f"{turnover_rate}%",
                "hint": _("Exits / active headcount"),
            },
            {
                "label": _("Exits (6m)"),
                "value": total_exits,
                "hint": _("Contract end in window"),
            },
            {
                "label": _("Hires (6m)"),
                "value": sum(m["hires"] for m in months),
                "hint": _("Joined in window"),
            },
            {
                "label": _("First-year exits"),
                "value": first_year,
                "hint": _("Proxy: tenure ≤ 1 year at exit"),
            },
        ],
        "charts": [
            {
                "id": "hires_exits",
                "type": "line",
                "title": _("Hires vs Exits"),
                "categories": [m["month"] for m in months],
                "series": [
                    {"name": _("Hires"), "data": [m["hires"] for m in months]},
                    {"name": _("Exits"), "data": [m["exits"] for m in months]},
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "month", "label": _("Month")},
                {"key": "hires", "label": _("Hires")},
                {"key": "exits", "label": _("Exits")},
                {"key": "net", "label": _("Net")},
            ],
            "rows": months
            + [
                {
                    "month": _("Dept exit: %(dept)s")
                    % {
                        "dept": r["employee_work_info__department_id__department"]
                        or _("Unassigned")
                    },
                    "hires": "",
                    "exits": r["count"],
                    "net": "",
                }
                for r in by_dept
            ],
        },
        "explorer_url_name": "employee-report",
    }


def joiners_leavers(filters: ReportFilters) -> dict:
    from employee.models import Employee, EmployeeWorkInformation

    hires_qs = EmployeeWorkInformation.objects.filter(
        date_joining__gte=filters.from_date,
        date_joining__lte=filters.to_date,
    )
    hires_qs = apply_org_filters(
        hires_qs, filters, prefix="", employee_prefix="employee_id"
    )
    hires = hires_qs.count()

    exits_qs = Employee.objects.filter(is_active=False).filter(
        Q(employee_work_info__contract_end_date__gte=filters.from_date)
        & Q(employee_work_info__contract_end_date__lte=filters.to_date)
    )
    exits_qs = apply_org_filters(
        exits_qs,
        filters,
        prefix="employee_work_info",
        employee_prefix="",
        apply_employment_status=False,
    )
    exits = exits_qs.count()

    trend = []
    for month_start, month_end, label in iter_months(filters.to_date, 6):
        count = apply_org_filters(
            EmployeeWorkInformation.objects.filter(date_joining__lte=month_end),
            filters,
            prefix="",
            employee_prefix="employee_id",
        ).count()
        trend.append({"month": label, "count": count})

    hire_rows = list(
        hires_qs.select_related("employee_id", "department_id")
        .order_by("-date_joining")[:50]
        .values(
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "department_id__department",
            "date_joining",
            "job_position_id__job_position",
        )
    )

    return {
        "title": _("Joiners & Leavers"),
        "kpis": [
            {"label": _("Joiners"), "value": hires, "hint": _("In selected period")},
            {"label": _("Leavers"), "value": exits, "hint": _("In selected period")},
            {
                "label": _("Net change"),
                "value": hires - exits,
                "hint": _("Joiners − leavers"),
            },
            {
                "label": _("Headcount (latest)"),
                "value": trend[-1]["count"] if trend else 0,
                "hint": _("Active with joining ≤ month end"),
            },
        ],
        "charts": [
            {
                "id": "headcount_trend",
                "type": "line",
                "title": _("Headcount Trend"),
                "categories": [t["month"] for t in trend],
                "series": [
                    {"name": _("Headcount"), "data": [t["count"] for t in trend]}
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "name", "label": _("Employee")},
                {"key": "department", "label": _("Department")},
                {"key": "position", "label": _("Position")},
                {"key": "date_joining", "label": _("Joining Date")},
            ],
            "rows": [
                {
                    "name": f"{r['employee_id__employee_first_name']} {r['employee_id__employee_last_name'] or ''}".strip(),
                    "department": r["department_id__department"] or "",
                    "position": r["job_position_id__job_position"] or "",
                    "date_joining": (
                        r["date_joining"].isoformat() if r["date_joining"] else ""
                    ),
                }
                for r in hire_rows
            ],
        },
        "explorer_url_name": "employee-report",
    }


def workforce_composition_drilldown(
    filters: ReportFilters, params: dict, request=None
) -> dict:
    """Drill into workforce composition by department / type / location label."""
    from report.drilldown import (
        apply_subordinate_scope,
        drilldown_payload,
        employee_link,
        empty_drilldown,
    )

    dimension = (params.get("dimension") or "department").strip().lower()
    value = (params.get("value") or "").strip()
    if not value:
        return empty_drilldown(
            _("Workforce Composition"), dimension, value, _("Missing dimension value.")
        )

    qs = _employees(filters)
    qs = apply_subordinate_scope(request, qs, perm="employee.view_employee", field="id")

    title = _("Workforce Composition")
    if dimension in ("department", "dept", "by_dept"):
        qs = qs.filter(employee_work_info__department_id__department=value)
        dimension = "department"
        title = _("Employees in %(dept)s") % {"dept": value}
    elif dimension in ("employee_type", "type", "by_type"):
        qs = qs.filter(employee_work_info__employee_type_id__employee_type=value)
        dimension = "employee_type"
        title = _("Employees · %(type)s") % {"type": value}
    elif dimension in ("location",):
        qs = qs.filter(employee_work_info__location=value)
        title = _("Employees in %(loc)s") % {"loc": value}
    elif dimension in ("job_position", "job"):
        qs = qs.filter(employee_work_info__job_position_id__job_position=value)
        dimension = "job_position"
        title = _("Employees · %(job)s") % {"job": value}
    else:
        return empty_drilldown(title, dimension, value, _("Unsupported dimension."))

    limit = int((params.get("limit") or filters.extra.get("row_limit") or 200))
    total = qs.count()
    rows = []
    for emp in qs.select_related(
        "employee_work_info",
        "employee_work_info__department_id",
        "employee_work_info__job_position_id",
    ).order_by("employee_first_name", "employee_last_name")[:limit]:
        wi = getattr(emp, "employee_work_info", None)
        dept = ""
        job = ""
        try:
            dept = wi.department_id.department if wi and wi.department_id_id else ""
        except Exception:
            dept = ""
        try:
            job = (
                wi.job_position_id.job_position if wi and wi.job_position_id_id else ""
            )
        except Exception:
            job = ""
        rows.append(
            {
                "employee": (
                    emp.get_full_name() if hasattr(emp, "get_full_name") else str(emp)
                ),
                "badge": getattr(emp, "badge_id", "") or "",
                "department": dept,
                "job_position": job,
                "link": employee_link(emp.id),
            }
        )
    return drilldown_payload(
        title=title,
        dimension=dimension,
        value=value,
        columns=[
            {"key": "employee", "label": _("Employee")},
            {"key": "badge", "label": _("Badge")},
            {"key": "department", "label": _("Department")},
            {"key": "job_position", "label": _("Job position")},
            {"key": "link", "label": _("Open"), "type": "link"},
        ],
        rows=rows,
        truncated=total > len(rows),
    )
