from django.apps import apps
from django.urls import path

from report.views import (
    asset_report,
    attendance_report,
    check_export_access,
    employee_report,
    leave_report,
    payroll_report,
    pms_report,
    recruitment_report,
    report_templates,
)

urlpatterns = [
    path("employee-report/", employee_report.employee_report, name="employee-report"),
    path("employee-pivot/", employee_report.employee_pivot, name="employee-pivot"),
    path(
        "employee-filter-options/",
        employee_report.employee_filter_field_options,
        name="employee-filter-options",
    ),
    path(
        "report-templates/list/",
        report_templates.list_report_templates,
        name="report-templates-list",
    ),
    path(
        "report-templates/save/",
        report_templates.save_report_template,
        name="report-templates-save",
    ),
    path(
        "report-templates/<int:template_id>/",
        report_templates.get_report_template,
        name="report-templates-get",
    ),
    path(
        "report-templates/<int:template_id>/delete/",
        report_templates.delete_report_template,
        name="report-templates-delete",
    ),
    path(
        "check-export-access/", check_export_access, name="report-check-export-access"
    ),
]


if apps.is_installed("recruitment"):
    urlpatterns.extend(
        [
            path(
                "recruitment-report/",
                recruitment_report.recruitment_report,
                name="recruitment-report",
            ),
            path(
                "recruitment-pivot/",
                recruitment_report.recruitment_pivot,
                name="recruitment-pivot",
            ),
            path(
                "recruitment-filter-options/",
                recruitment_report.recruitment_filter_field_options,
                name="recruitment-filter-options",
            ),
        ]
    )

if apps.is_installed("attendance"):
    urlpatterns.extend(
        [
            path(
                "attendance-report/",
                attendance_report.attendance_report,
                name="attendance-report",
            ),
            path(
                "attendance-pivot/",
                attendance_report.attendance_pivot,
                name="attendance-pivot",
            ),
            path(
                "attendance-filter-options/",
                attendance_report.attendance_filter_field_options,
                name="attendance-filter-options",
            ),
        ]
    )

if apps.is_installed("leave"):
    urlpatterns.extend(
        [
            path("leave-report/", leave_report.leave_report, name="leave-report"),
            path("leave-pivot/", leave_report.leave_pivot, name="leave-pivot"),
            path(
                "leave-filter-options/",
                leave_report.leave_filter_field_options,
                name="leave-filter-options",
            ),
        ]
    )

if apps.is_installed("payroll"):
    urlpatterns.extend(
        [
            path(
                "payroll-report/", payroll_report.payroll_report, name="payroll-report"
            ),
            path("payroll-pivot/", payroll_report.payroll_pivot, name="payroll-pivot"),
            path(
                "payroll-filter-options/",
                payroll_report.payroll_filter_field_options,
                name="payroll-filter-options",
            ),
        ]
    )

if apps.is_installed("asset"):
    urlpatterns.extend(
        [
            path("asset-report/", asset_report.asset_report, name="asset-report"),
            path("asset-pivot/", asset_report.asset_pivot, name="asset-pivot"),
            path(
                "asset-filter-options/",
                asset_report.asset_filter_field_options,
                name="asset-filter-options",
            ),
        ]
    )

if apps.is_installed("pms"):
    urlpatterns.extend(
        [
            path("pms-report/", pms_report.pms_report, name="pms-report"),
            path("pms-pivot/", pms_report.pms_pivot, name="pms-pivot"),
            path(
                "pms-filter-options/",
                pms_report.pms_filter_field_options,
                name="pms-filter-options",
            ),
        ]
    )
