"""Explorer domain picker — landing page linking to the per-module ad-hoc pivot explorers."""

from __future__ import annotations

from django.apps import apps
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _lazy

from horilla.decorators import login_required

_DOMAINS = (
    (
        "employee",
        "employee-report",
        _lazy("Employee"),
        _lazy("Headcount, demographics, and workforce composition pivots."),
        "employee.view_employee",
    ),
    (
        "attendance",
        "attendance-report",
        _lazy("Attendance"),
        _lazy("Clock-in/out, overtime, and attendance pattern pivots."),
        "attendance.view_attendance",
    ),
    (
        "leave",
        "leave-report",
        _lazy("Leave"),
        _lazy("Leave balances, requests, and utilization pivots."),
        "leave.view_leaverequest",
    ),
    (
        "payroll",
        "payroll-report",
        _lazy("Payroll"),
        _lazy("Payslip, allowance, and deduction pivots."),
        "payroll.view_payslip",
    ),
    (
        "recruitment",
        "recruitment-report",
        _lazy("Recruitment"),
        _lazy("Candidate pipeline and hiring funnel pivots."),
        "recruitment.view_recruitment",
    ),
    (
        "asset",
        "asset-report",
        _lazy("Asset"),
        _lazy("Asset allocation and inventory pivots."),
        "asset.view_asset",
    ),
    (
        "pms",
        "pms-report",
        _lazy("Performance"),
        _lazy("Objectives, KPIs, and performance pivots."),
        "pms.view_objective",
    ),
)


def explorer_domain_entries(request) -> list[dict]:
    """Explorer modules the current user can open, in fixed display order."""
    user = request.user
    entries = []
    for app_label, url_name, name, description, permission in _DOMAINS:
        if not apps.is_installed(app_label):
            continue
        if not (user.is_superuser or user.has_perm(permission)):
            continue
        entries.append(
            {
                "name": name,
                "description": description,
                "url": reverse(url_name),
            }
        )
    return entries


@login_required
def explorer_picker(request):
    return render(
        request,
        "report/explorer_picker.html",
        {"entries": explorer_domain_entries(request)},
    )
