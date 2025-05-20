from django.apps import apps
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as trans

MENU = trans("Reports")
IMG_SRC = "images/ui/report.svg"
ACCESSIBILITY = "report.sidebar.menu_accessibility"


SUBMENUS = []

# Dynamically adding submenu if the app is installed
if apps.is_installed("recruitment"):
    SUBMENUS.append(
        {
            "menu": "Recruitment",
            "redirect": reverse_lazy("recruitment-report"),
            "accessibility": "report.sidebar.recruitment_accessibility",
        }
    )

if apps.is_installed("employee"):
    SUBMENUS.append(
        {
            "menu": "Employee",
            "redirect": reverse_lazy("employee-report"),
            "accessibility": "report.sidebar.employee_accessibility",
        }
    )

if apps.is_installed("attendance"):
    SUBMENUS.append(
        {
            "menu": "Attendance",
            "redirect": reverse_lazy("attendance-report"),
            "accessibility": "report.sidebar.attendance_accessibility",
        }
    )

if apps.is_installed("leave"):
    SUBMENUS.append(
        {
            "menu": "Leave",
            "redirect": reverse_lazy("leave-report"),
            "accessibility": "report.sidebar.leave_accessibility",
        }
    )

if apps.is_installed("payroll"):
    SUBMENUS.append(
        {
            "menu": "Payroll",
            "redirect": reverse_lazy("payroll-report"),
            "accessibility": "report.sidebar.payroll_accessibility",
        }
    )

if apps.is_installed("asset"):
    SUBMENUS.append(
        {
            "menu": "Asset",
            "redirect": reverse_lazy("asset-report"),
            "accessibility": "report.sidebar.asset_accessibility",
        }
    )

if apps.is_installed("pms"):
    SUBMENUS.append(
        {
            "menu": "Performance",
            "redirect": reverse_lazy("pms-report"),
            "accessibility": "report.sidebar.pms_accessibility",
        }
    )


def menu_accessibility(request, submenu, user_perms, *args, **kwargs):
    return (
        request.user.is_superuser
        or request.user.has_perm("recruitment.view_recruitment")
        or request.user.has_perm("employee.view_employee")
        or request.user.has_perm("pms.view_objective")
        or request.user.has_perm("attendance.view_attendance")
        or request.user.has_perm("leave.view_leaverequest")
        or request.user.has_perm("payroll.view_payslip")
        or request.user.has_perm("asset.view_asset")
    )


def recruitment_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm(
        "recruitment.view_recruitment"
    )


def employee_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm("employee.view_employee")


def attendance_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm(
        "attendance.view_attendance"
    )


def leave_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm("leave.view_leaverequest")


def payroll_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm("payroll.view_payslip")


def asset_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm("asset.view_asset")


def pms_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm("pms.view_objective")
