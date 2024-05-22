"""
attendance/sidebar.py
"""

from datetime import datetime

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from base.context_processors import biometric_app_exists
from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Attendance")
IMG_SRC = "images/ui/attendances.svg"


SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("attendance-dashboard"),
    },
    {
        "menu": trans("Attendances"),
        "redirect": reverse("attendance-view"),
        "accessibility": "attendance.sidebar.attendances_accessibility",
    },
    {
        "menu": trans("Attendance Requests"),
        "redirect": reverse("request-attendance-view"),
    },
    {
        "menu": trans("Hour Account"),
        "redirect": reverse("attendance-overtime-view"),
        "accessibility": "attendance.sidebar.hour_account_accessibility",
    },
    {
        "menu": trans("Work Records"),
        "redirect": reverse("work-records"),
        "accessibility": "attendance.sidebar.work_record_accessibility",
    },
    {
        "menu": trans("Attendance Activities"),
        "redirect": reverse("attendance-activity-view"),
    },
    {
        "menu": trans("Late Come Early Out"),
        "redirect": reverse("late-come-early-out-view"),
    },
    {
        "menu": trans("My Attendances"),
        "redirect": reverse("view-my-attendance"),
    },
]


def attendances_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(
        request.user
    )


def hour_account_accessibility(request, submenu, user_perms, *args, **kwargs):
    submenu["redirect"] = submenu["redirect"] + f"?year={datetime.now().year}"
    return True


def work_record_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("attendance.view_attendance") or is_reportingmanager(
        request.user
    )
