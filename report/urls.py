from django.apps import apps
from django.urls import path

from report.views import (
    asset_report,
    attendance_report,
    employee_report,
    leave_report,
    payroll_report,
    pms_report,
    recruitment_report,
)

urlpatterns = [
    path("employee-report", employee_report.employee_report, name="employee-report"),
    path("employee-pivot", employee_report.employee_pivot, name="employee-pivot"),
]


if apps.is_installed("recruitment"):
    urlpatterns.extend(
        [
            path(
                "recruitment-report",
                recruitment_report.recruitment_report,
                name="recruitment-report",
            ),
            path(
                "recruitment-pivot",
                recruitment_report.recruitment_pivot,
                name="recruitment-pivot",
            ),
        ]
    )

if apps.is_installed("attendance"):
    urlpatterns.extend(
        [
            path(
                "attendance-report",
                attendance_report.attendance_report,
                name="attendance-report",
            ),
            path(
                "attendance-pivot",
                attendance_report.attendance_pivot,
                name="attendance-pivot",
            ),
        ]
    )

if apps.is_installed("leave"):
    urlpatterns.extend(
        [
            path("leave-report", leave_report.leave_report, name="leave-report"),
            path("leave-pivot", leave_report.leave_pivot, name="leave-pivot"),
        ]
    )

if apps.is_installed("payroll"):
    urlpatterns.extend(
        [
            path(
                "payroll-report", payroll_report.payroll_report, name="payroll-report"
            ),
            path("payroll-pivot", payroll_report.payroll_pivot, name="payroll-pivot"),
        ]
    )

if apps.is_installed("asset"):
    urlpatterns.extend(
        [
            path("asset-report", asset_report.asset_report, name="asset-report"),
            path("asset-pivot", asset_report.asset_pivot, name="asset-pivot"),
        ]
    )

if apps.is_installed("pms"):
    urlpatterns.extend(
        [
            path("pms-report", pms_report.pms_report, name="pms-report"),
            path("pms-pivot", pms_report.pms_pivot, name="pms-pivot"),
        ]
    )
