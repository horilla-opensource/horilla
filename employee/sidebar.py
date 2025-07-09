"""
employee/sidebar.py

To set Horilla sidebar for employee
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from accessibility.methods import check_is_accessible
from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Employee")
IMG_SRC = "images/ui/employees.svg"

SUBMENUS = [
    {
        "menu": trans("Profile"),
        "redirect": reverse("employee-profile"),
        "accessibility": "employee.sidebar.profile_accessibility",
    },
    {
        "menu": trans("Employees"),
        "redirect": reverse("employee-view"),
        "accessibility": "employee.sidebar.employee_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("document-request-view"),
        "accessibility": "employee.sidebar.document_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("shift-request-view"),
    },
    {
        "menu": trans("Work Type Requests"),
        "redirect": reverse("work-type-request-view"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("rotating-shift-assign"),
        "accessibility": "employee.sidebar.rotating_shift_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("rotating-work-type-assign"),
        "accessibility": "employee.sidebar.rotating_work_type_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("disciplinary-actions"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("view-policies"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("organisation-chart"),
    },
]


def profile_accessibility(request, submenu, user_perms, *args, **kwargs):
    accessible = False
    try:
        accessible = request.session["selected_company"] == "all" or str(
            request.user.employee_get.employee_work_info.company_id.id
        ) == str(request.session["selected_company"])
    finally:
        return accessible


def document_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "horilla_documents.view_documentrequest"
    ) or is_reportingmanager(request.user)


def rotating_shift_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingshiftassign"
    ) or is_reportingmanager(request.user)


def rotating_work_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_rotatingworktypeassign"
    ) or is_reportingmanager(request.user)


def employee_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Employee accessibility method
    """
    cache_key = request.session.session_key + "accessibility_filter"
    employee = getattr(request.user, "employee_get", None)
    return (
        is_reportingmanager(request.user)
        or request.user.has_perm("employee.view_employee")
        or check_is_accessible("employee_view", cache_key, employee)
    )
