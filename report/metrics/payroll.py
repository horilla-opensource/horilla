"""Payroll and labor cost metrics."""

from __future__ import annotations

from django.db.models import Avg, Count, Q, Sum
from django.utils.translation import gettext as _

from report.engine import ReportFilters, apply_org_filters, iter_months


def _payslips(filters: ReportFilters):
    from payroll.models.models import Payslip

    qs = Payslip.objects.filter(
        start_date__lte=filters.to_date,
        end_date__gte=filters.from_date,
    )
    if filters.payslip_status:
        qs = qs.filter(status=filters.payslip_status)
    return apply_org_filters(
        qs,
        filters,
        prefix="employee_id__employee_work_info",
        employee_prefix="employee_id",
    )


def labor_cost_summary(filters: ReportFilters) -> dict:
    qs = _payslips(filters)
    agg = qs.aggregate(
        gross=Sum("gross_pay"),
        net=Sum("net_pay"),
        deduction=Sum("deduction"),
        count=Count("id"),
        employees=Count("employee_id", distinct=True),
    )
    gross = round(agg["gross"] or 0, 2)
    net = round(agg["net"] or 0, 2)
    deduction = round(agg["deduction"] or 0, 2)
    # Employer cost proxy ≈ gross (employer contributions not always modeled)
    employer_proxy = gross

    by_dept = list(
        qs.filter(employee_id__employee_work_info__department_id__isnull=False)
        .values("employee_id__employee_work_info__department_id__department")
        .annotate(
            gross=Sum("gross_pay"),
            net=Sum("net_pay"),
            deduction=Sum("deduction"),
            count=Count("id"),
        )
        .order_by("-gross")
    )

    trend = []
    from payroll.models.models import Payslip

    for month_start, month_end, label in iter_months(filters.to_date, 6):
        month_qs = apply_org_filters(
            Payslip.objects.filter(
                start_date__lte=month_end,
                end_date__gte=month_start,
            ),
            filters,
            prefix="employee_id__employee_work_info",
            employee_prefix="employee_id",
        )
        if filters.payslip_status:
            month_qs = month_qs.filter(status=filters.payslip_status)
        m = month_qs.aggregate(gross=Sum("gross_pay"), net=Sum("net_pay"))
        trend.append(
            {
                "month": label,
                "gross": round(m["gross"] or 0, 2),
                "net": round(m["net"] or 0, 2),
            }
        )

    return {
        "title": _("Labor Cost Summary"),
        "kpis": [
            {"label": _("Gross pay"), "value": gross, "hint": _("Period payslips")},
            {"label": _("Net pay"), "value": net, "hint": _("Period payslips")},
            {"label": _("Deductions"), "value": deduction, "hint": _("Period")},
            {
                "label": _("Gross (employer cost proxy)"),
                "value": employer_proxy,
                "hint": _("≈ gross until employer contribs modeled"),
            },
        ],
        "charts": [
            {
                "id": "cost_trend",
                "type": "line",
                "title": _("Labor Cost Trend"),
                "categories": [t["month"] for t in trend],
                "series": [
                    {"name": _("Gross"), "data": [t["gross"] for t in trend]},
                    {"name": _("Net"), "data": [t["net"] for t in trend]},
                ],
            },
            {
                "id": "cost_dept",
                "type": "bar",
                "title": _("Gross by Department"),
                "categories": [
                    r["employee_id__employee_work_info__department_id__department"]
                    for r in by_dept[:12]
                ],
                "series": [
                    {
                        "name": _("Gross"),
                        "data": [round(r["gross"] or 0, 2) for r in by_dept[:12]],
                    }
                ],
            },
        ],
        "table": {
            "columns": [
                {"key": "department", "label": _("Department")},
                {"key": "gross", "label": _("Gross")},
                {"key": "deduction", "label": _("Deductions")},
                {"key": "net", "label": _("Net")},
                {"key": "count", "label": _("Payslips")},
            ],
            "rows": [
                {
                    "department": r[
                        "employee_id__employee_work_info__department_id__department"
                    ],
                    "gross": round(r["gross"] or 0, 2),
                    "deduction": round(r["deduction"] or 0, 2),
                    "net": round(r["net"] or 0, 2),
                    "count": r["count"],
                }
                for r in by_dept
            ],
        },
        "meta": {"employees": agg["employees"] or 0, "payslips": agg["count"] or 0},
        "explorer_url_name": "payroll-report",
    }


def cost_composition(filters: ReportFilters) -> dict:
    qs = _payslips(filters)
    allowance_total = 0.0
    deduction_total = 0.0
    allowance_map: dict[str, float] = {}
    deduction_map: dict[str, float] = {}

    for slip in qs.only("pay_head_data", "gross_pay", "deduction").iterator():
        data = slip.pay_head_data or {}
        if not isinstance(data, dict):
            continue
        for key in ("allowances", "allowance"):
            items = data.get(key) or []
            if isinstance(items, dict):
                items = list(items.values()) if items else []
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = (
                    item.get("title")
                    or item.get("allowance")
                    or item.get("name")
                    or _("Allowance")
                )
                amount = float(item.get("amount") or item.get("amt") or 0)
                allowance_map[title] = allowance_map.get(title, 0) + amount
                allowance_total += amount
        for key in ("deductions", "deduction_list"):
            items = data.get(key) or []
            if isinstance(items, dict):
                items = list(items.values()) if items else []
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = (
                    item.get("title")
                    or item.get("deduction")
                    or item.get("name")
                    or _("Deduction")
                )
                amount = float(item.get("amount") or item.get("amt") or 0)
                deduction_map[title] = deduction_map.get(title, 0) + amount
                deduction_total += amount

    # Fallback if pay_head_data lacks structured lists
    unsplit_fallback = False
    if not allowance_total and not deduction_total:
        agg = qs.aggregate(gross=Sum("gross_pay"), deduction=Sum("deduction"))
        allowance_total = float(agg["gross"] or 0)
        deduction_total = float(agg["deduction"] or 0)
        allowance_map[_("Gross (unsplit)")] = allowance_total
        deduction_map[_("Deductions (unsplit)")] = deduction_total
        unsplit_fallback = True

    allow_rows = sorted(
        [
            {"component": k, "amount": round(v, 2), "kind": _("Allowance")}
            for k, v in allowance_map.items()
        ],
        key=lambda x: -x["amount"],
    )[:30]
    ded_rows = sorted(
        [
            {"component": k, "amount": round(v, 2), "kind": _("Deduction")}
            for k, v in deduction_map.items()
        ],
        key=lambda x: -x["amount"],
    )[:30]

    return {
        "title": _("Cost Composition"),
        "kpis": [
            {
                "label": _("Allowances total"),
                "value": round(allowance_total, 2),
                "hint": (
                    _("Unsplit gross — pay_head_data missing structured lists")
                    if unsplit_fallback
                    else _("From payslip heads")
                ),
            },
            {
                "label": _("Deductions total"),
                "value": round(deduction_total, 2),
                "hint": (
                    _("Unsplit deduction field — not componentized")
                    if unsplit_fallback
                    else _("From payslip heads")
                ),
            },
            {
                "label": _("Allowance components"),
                "value": len(allowance_map),
                "hint": _("Unsplit fallback") if unsplit_fallback else "",
            },
            {
                "label": _("Deduction components"),
                "value": len(deduction_map),
                "hint": "",
            },
        ],
        "charts": [
            {
                "id": "allowances",
                "type": "donut",
                "title": _("Top Allowances"),
                "categories": [r["component"] for r in allow_rows[:8]],
                "series": [
                    {
                        "name": _("Amount"),
                        "data": [r["amount"] for r in allow_rows[:8]],
                    }
                ],
            },
            {
                "id": "deductions",
                "type": "donut",
                "title": _("Top Deductions"),
                "categories": [r["component"] for r in ded_rows[:8]],
                "series": [
                    {
                        "name": _("Amount"),
                        "data": [r["amount"] for r in ded_rows[:8]],
                    }
                ],
            },
        ],
        "table": {
            "columns": [
                {"key": "kind", "label": _("Type")},
                {"key": "component", "label": _("Component")},
                {"key": "amount", "label": _("Amount")},
            ],
            "rows": allow_rows + ded_rows,
        },
        "explorer_url_name": "payroll-report",
    }


def payroll_headcount_cost(filters: ReportFilters) -> dict:
    from employee.models import Employee

    qs = _payslips(filters)
    by_dept = list(
        qs.filter(employee_id__employee_work_info__department_id__isnull=False)
        .values(
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__department_id__department",
        )
        .annotate(
            gross=Sum("gross_pay"),
            net=Sum("net_pay"),
            payslips=Count("id"),
            employees=Count("employee_id", distinct=True),
            avg_net=Avg("net_pay"),
        )
        .order_by("-gross")
    )

    active = apply_org_filters(
        Employee.objects.all(),
        filters,
        prefix="employee_work_info",
        employee_prefix="",
    ).count()
    total_gross = qs.aggregate(g=Sum("gross_pay"))["g"] or 0
    cost_per_fte = round(total_gross / active, 2) if active else 0
    avg_net = qs.aggregate(a=Avg("net_pay"))["a"] or 0

    rows = []
    for r in by_dept:
        emp_count = r["employees"] or 1
        rows.append(
            {
                "department": r[
                    "employee_id__employee_work_info__department_id__department"
                ],
                "employees": r["employees"],
                "gross": round(r["gross"] or 0, 2),
                "avg_net": round(r["avg_net"] or 0, 2),
                "cost_per_head": round((r["gross"] or 0) / emp_count, 2),
            }
        )

    return {
        "title": _("Payroll Headcount Cost"),
        "kpis": [
            {
                "label": _("Cost per head (proxy)"),
                "value": cost_per_fte,
                "hint": _("Gross / active headcount — not hours-based FTE"),
            },
            {
                "label": _("Avg net pay"),
                "value": round(avg_net, 2),
                "hint": _("Per payslip"),
            },
            {"label": _("Active headcount"), "value": active, "hint": ""},
            {
                "label": _("Total gross"),
                "value": round(total_gross, 2),
                "hint": _("Period"),
            },
        ],
        "charts": [
            {
                "id": "cost_per_head",
                "type": "bar",
                "title": _("Cost per Head by Department"),
                "categories": [r["department"] for r in rows[:12]],
                "series": [
                    {
                        "name": _("Cost / head"),
                        "data": [r["cost_per_head"] for r in rows[:12]],
                    }
                ],
            }
        ],
        "table": {
            "columns": [
                {"key": "department", "label": _("Department")},
                {"key": "employees", "label": _("Employees")},
                {"key": "gross", "label": _("Gross")},
                {"key": "avg_net", "label": _("Avg Net")},
                {"key": "cost_per_head", "label": _("Cost / Head")},
            ],
            "rows": rows,
        },
        "explorer_url_name": "payroll-report",
    }


def payslip_register(filters: ReportFilters) -> dict:
    qs = (
        _payslips(filters)
        .select_related(
            "employee_id",
            "employee_id__employee_work_info",
            "employee_id__employee_work_info__department_id",
        )
        .order_by("-end_date", "employee_id__employee_first_name")
    )
    total = qs.count()
    # Cap rows for UI; export uses same query with higher limit via engine caller
    limit = int(filters.extra.get("row_limit", 500))
    rows = []
    for slip in qs[:limit]:
        emp = slip.employee_id
        dept = ""
        try:
            dept = emp.employee_work_info.department_id.department
        except Exception:
            dept = ""
        rows.append(
            {
                "employee": (
                    emp.get_full_name() if hasattr(emp, "get_full_name") else str(emp)
                ),
                "badge": getattr(emp, "badge_id", "") or "",
                "department": dept,
                "start_date": slip.start_date.isoformat() if slip.start_date else "",
                "end_date": slip.end_date.isoformat() if slip.end_date else "",
                "gross": round(slip.gross_pay or 0, 2),
                "deduction": round(slip.deduction or 0, 2),
                "net": round(slip.net_pay or 0, 2),
                "status": (
                    slip.get_status() if hasattr(slip, "get_status") else slip.status
                ),
            }
        )

    agg = qs.aggregate(
        gross=Sum("gross_pay"), net=Sum("net_pay"), deduction=Sum("deduction")
    )

    return {
        "title": _("Payslip Register"),
        "kpis": [
            {"label": _("Payslips"), "value": total, "hint": _("In period")},
            {
                "label": _("Gross total"),
                "value": round(agg["gross"] or 0, 2),
                "hint": "",
            },
            {
                "label": _("Net total"),
                "value": round(agg["net"] or 0, 2),
                "hint": "",
            },
            {
                "label": _("Shown rows"),
                "value": len(rows),
                "hint": _("Capped for display"),
            },
        ],
        "charts": [],
        "table": {
            "columns": [
                {"key": "employee", "label": _("Employee")},
                {"key": "badge", "label": _("Badge")},
                {"key": "department", "label": _("Department")},
                {"key": "start_date", "label": _("Start")},
                {"key": "end_date", "label": _("End")},
                {"key": "gross", "label": _("Gross")},
                {"key": "deduction", "label": _("Deduction")},
                {"key": "net", "label": _("Net")},
                {"key": "status", "label": _("Status")},
            ],
            "rows": rows,
        },
        "explorer_url_name": "payroll-report",
    }


def payslip_register_drilldown(
    filters: ReportFilters, params: dict, request=None
) -> dict:
    """Drill payslip register by department label or employee badge/name."""
    from report.drilldown import (
        apply_subordinate_scope,
        drilldown_payload,
        employee_link,
        empty_drilldown,
        payslip_link,
    )

    dimension = (params.get("dimension") or "department").strip().lower()
    value = (params.get("value") or "").strip()
    if not value:
        return empty_drilldown(
            _("Payslip Register"), dimension, value, _("Missing dimension value.")
        )

    qs = _payslips(filters)
    qs = apply_subordinate_scope(
        request, qs, perm="payroll.view_payslip", field="employee_id"
    )

    title = _("Payslip Register")
    if dimension in ("department", "dept"):
        qs = qs.filter(employee_id__employee_work_info__department_id__department=value)
        title = _("Payslips · %(dept)s") % {"dept": value}
        dimension = "department"
    elif dimension in ("employee", "badge"):
        qs = qs.filter(
            Q(employee_id__badge_id__iexact=value)
            | Q(employee_id__employee_first_name__icontains=value)
            | Q(employee_id__employee_last_name__icontains=value)
        )
        title = _("Payslips · %(emp)s") % {"emp": value}
        dimension = "employee"
    elif dimension in ("status",):
        qs = qs.filter(status__iexact=value)
        title = _("Payslips · status %(s)s") % {"s": value}
    else:
        return empty_drilldown(title, dimension, value, _("Unsupported dimension."))

    limit = int((params.get("limit") or filters.extra.get("row_limit") or 200))
    total = qs.count()
    rows = []
    for slip in qs.select_related(
        "employee_id",
        "employee_id__employee_work_info__department_id",
    ).order_by("-end_date")[:limit]:
        emp = slip.employee_id
        dept = ""
        try:
            dept = emp.employee_work_info.department_id.department
        except Exception:
            dept = ""
        rows.append(
            {
                "employee": (
                    emp.get_full_name() if hasattr(emp, "get_full_name") else str(emp)
                ),
                "badge": getattr(emp, "badge_id", "") or "",
                "department": dept,
                "end_date": slip.end_date.isoformat() if slip.end_date else "",
                "net": round(slip.net_pay or 0, 2),
                "status": (
                    slip.get_status() if hasattr(slip, "get_status") else slip.status
                ),
                "link": payslip_link(slip.id),
                "employee_link": employee_link(emp.id if emp else None),
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
            {"key": "end_date", "label": _("End")},
            {"key": "net", "label": _("Net")},
            {"key": "status", "label": _("Status")},
            {"key": "link", "label": _("Payslip"), "type": "link"},
        ],
        rows=rows,
        truncated=total > len(rows),
    )
