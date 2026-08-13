from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Reports")
IMG_SRC = "images/ui/report.svg"
ACCESSIBILITY = "report.sidebar.menu_accessibility"


SUBMENUS = [
    {
        "menu": _("Standard Reports"),
        "redirect": reverse_lazy("standard-report-catalog"),
        "accessibility": "report.sidebar.standard_accessibility",
    },
    {
        "menu": _("Explorer"),
        "redirect": reverse_lazy("report-explorer"),
        "accessibility": "report.sidebar.standard_accessibility",
    },
]


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


def standard_accessibility(request, submenu, user_perms, *args, **kwargs):
    return menu_accessibility(request, submenu, user_perms, *args, **kwargs)


# Per-domain gates below are no longer wired into SUBMENUS (the Explorer
# picker page does its own per-domain permission check instead of a
# separate sidebar entry per app), but they're kept as importable helpers
# since other code/tests still depend on them individually.
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
