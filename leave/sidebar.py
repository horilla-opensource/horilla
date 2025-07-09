"""
leave/sidebar.py
"""

from django.apps import apps
from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from base.templatetags.basefilters import is_leave_approval_manager, is_reportingmanager
from leave.templatetags.leavefilters import is_compensatory

MENU = trans("")
IMG_SRC = "images/ui/leave.svg"

SUBMENUS = [
    {
        "menu": trans(""),
        "redirect": reverse("leave-dashboard"),
        "accessibility": "leave.sidebar.dashboard_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("user-request-view"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("request-view"),
        "accessibility": "leave.sidebar.leave_request_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("type-view"),
        "accessibility": "leave.sidebar.type_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("assign-view"),
        "accessibility": "leave.sidebar.assign_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("leave-allocation-request-view"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("holiday-view"),
        "accessibility": "leave.sidebar.holiday_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("company-leave-view"),
        "accessibility": "leave.sidebar.company_leave_accessibility",
    },
    {
        "menu": trans(""),
        "redirect": reverse("restrict-view"),
        "accessibility": "leave.sidebar.restrict_leave_accessibility",
    },
]


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    have_perm = request.user.has_perm("leave.view_leaverequest")
    if not have_perm:
        submenu["redirect"] = reverse("leave-employee-dashboard") + "?dashboard=true"
    return True


def leave_request_accessibility(request, submenu, user_perms, *args, **kwargs):
    return (
        request.user.has_perm("leave.view_leaverequest")
        or is_leave_approval_manager(request.user)
        or is_reportingmanager(request.user)
    )


def type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("leave.view_leavetype")


def assign_accessibility(request, submenu, user_perm, *args, **kwargs):
    submenu["redirect"] = submenu["redirect"] + "?field=leave_type_id"
    return request.user.has_perm("leave.view_availableleave") or is_reportingmanager(
        request.user
    )


def holiday_accessibility(request, submenu, user_perms, *args, **kwargs):
    return not request.user.is_superuser and not request.user.has_perm(
        "base.view_holidays"
    )


def company_leave_accessibility(request, submenu, user_perms, *args, **kwargs):
    return not request.user.is_superuser and not request.user.has_perm(
        "base.view_companyleaves"
    )


def restrict_leave_accessibility(request, submenu, user_perms, *args, **kwargs):
    return not request.user.is_superuser and not request.user.has_perm(
        "leave.view_restrictleave"
    )


if apps.is_installed("attendance"):
    SUBMENUS.append(
        {
            "menu": trans("Compensatory Leave Requests"),
            "redirect": reverse("view-compensatory-leave"),
            "accessibility": "leave.sidebar.componstory_accessibility",
        }
    )

    def componstory_accessibility(request, submenu, user_perms, *args, **kwargs):
        return is_compensatory(request.user)
