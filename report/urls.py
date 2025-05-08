from django.urls import path

from report.views import (
    asset_report,
    attendance_report,
    employee_report,
    leave_report,
    payroll_report,
    pms_report,
)

urlpatterns = [
    path("employee-report", employee_report.employee_report, name="employee-report"),
    path("employee-pivot", employee_report.employee_pivot, name="employee-pivot"),
    path(
        "attendance-report",
        attendance_report.attendance_report,
        name="attendance-report",
    ),
    path(
        "attendance-pivot", attendance_report.attendance_pivot, name="attendance-pivot"
    ),
    path("leave-report", leave_report.leave_report, name="leave-report"),
    path("leave-pivot", leave_report.leave_pivot, name="leave-pivot"),
    path("payroll-report", payroll_report.payroll_report, name="payroll-report"),
    path("payroll-pivot", payroll_report.payroll_pivot, name="payroll-pivot"),
    path("asset-report", asset_report.asset_report, name="asset-report"),
    path("asset-pivot", asset_report.asset_pivot, name="asset-pivot"),
    path("pms-report", pms_report.pms_report, name="pms-report"),
    path("pms-pivot", pms_report.pms_pivot, name="pms-pivot"),
]
