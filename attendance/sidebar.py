"""
attendance/sidebar.py
"""

from datetime import datetime

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.context_processors import enable_late_come_early_out_tracking
from base.templatetags.basefilters import is_reportingmanager

MENU = _("Attendance")
IMG_SRC = "images/ui/attendances.svg"


SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse("attendance-dashboard"),
        "accessibility": "attendance.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("Attendances"),
        "redirect": reverse("attendance-view"),
        "accessibility": "attendance.sidebar.attendances_accessibility",
    },
    {
        "menu": _("Attendance Requests"),
        "redirect": reverse("request-attendance-view"),
    },
    {
        "menu": _("Hour Account"),
        "redirect": reverse("attendance-overtime-view"),
        "accessibility": "attendance.sidebar.hour_account_accessibility",
    },
    {
        "menu": _("Work Records"),
        "redirect": reverse("work-records"),
        "accessibility": "attendance.sidebar.work_record_accessibility",
    },
    {
        "menu": _("Attendance Activities"),
        "redirect": reverse("attendance-activity-view"),
    },
    {
        "menu": _("Late Come Early Out"),
        "redirect": reverse("late-come-early-out-view"),
        "accessibility": "attendance.sidebar.tracking_accessibility",
    },
    {
        "menu": _("My Attendances"),
        "redirect": reverse("view-my-attendance"),
    },
]


def attendances_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if the user has permission to view attendance or is a reporting manager.
    """
    return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(
        request.user
    )


def hour_account_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Modify the submenu redirect URL to include the current year as a query parameter.
    """
    submenu["redirect"] = submenu["redirect"] + f"?year={datetime.now().year}"
    return True


def work_record_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if the user has permission to view attendance or is a reporting manager.
    """
    return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(
        request.user
    )


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if the user has permission to view attendance or is a reporting manager.
    """
    return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(
        request.user
    )


def tracking_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Determine if late come/early out tracking is enabled.
    """
    return enable_late_come_early_out_tracking(None).get("tracking")
