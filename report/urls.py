from django.urls import path

from report.views import (
    attendance_report,
    employee_report,
    leave_report,
    payroll_report,
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
]
