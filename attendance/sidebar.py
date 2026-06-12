"""
attendance/sidebar.py
"""

from datetime import datetime

from django.apps import apps
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.context_processors import enable_late_come_early_out_tracking
from base.templatetags.basefilters import is_reportingmanager
from horilla.menu import settings_menu

MENU = _("Attendance")
IMG_SRC = "images/ui/attendances.svg"


SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("attendance-dashboard"),
        "accessibility": "attendance.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("Attendances"),
        "redirect": reverse_lazy("attendance-view"),
        "accessibility": "attendance.sidebar.attendances_accessibility",
    },
    {
        "menu": _("Attendance Requests"),
        "redirect": reverse_lazy("request-attendance-view"),
    },
    {
        "menu": _("Hour Account"),
        "redirect": reverse_lazy("attendance-overtime-view"),
        "accessibility": "attendance.sidebar.hour_account_accessibility",
    },
    {
        "menu": _("Work Records"),
        "redirect": reverse_lazy("work-records"),
        "accessibility": "attendance.sidebar.work_record_accessibility",
    },
    {
        "menu": _("Attendance Activities"),
        "redirect": reverse_lazy("attendance-activity-view"),
    },
    {
        "menu": _("Late Come Early Out"),
        "redirect": reverse_lazy("late-come-early-out-view"),
        "accessibility": "attendance.sidebar.tracking_accessibility",
    },
    {
        "menu": _("My Attendances"),
        "redirect": reverse_lazy("view-my-attendance"),
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


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def validation_condition_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("attendance.view_attendancevalidationcondition")


def biometric_accessibility(request, submenu, user_perms, *args, **kwargs):
    return apps.is_installed("biometric") and request.user.has_perm(
        "base.view_biometricattendance"
    )


def ip_restriction_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("attendance.add_attendance")


def geo_face_accessibility(request, submenu, user_perms, *args, **kwargs):
    has_geo = apps.is_installed("geofencing") and request.user.has_perm(
        "geofencing.add_geofencing"
    )
    has_face = apps.is_installed("facedetection") and request.user.has_perm(
        "facedetection.add_facedetection"
    )
    return has_geo or has_face


@settings_menu.register
class AttendanceSettings:
    title = _("Attendance")
    order = 5
    condition = lambda self, request: apps.is_installed("attendance")
    items = [
        {
            "label": _("Track Late Come & Early Out"),
            "url": reverse_lazy("track-late-come-early-out"),
            "accessibility": validation_condition_accessibility,
        },
        {
            "label": _("Attendance Break Point"),
            "url": reverse_lazy("attendance-settings-view"),
            "accessibility": validation_condition_accessibility,
        },
        {
            "label": _("Check In/Check Out"),
            "url": reverse_lazy("check-in-check-out-setting"),
            "accessibility": validation_condition_accessibility,
        },
        {
            "label": _("Grace Time"),
            "url": reverse_lazy("grace-settings-view"),
            "accessibility": validation_condition_accessibility,
        },
        {
            "label": _("Biometric Attendance"),
            "url": reverse_lazy("enable-biometric-attendance"),
            "accessibility": biometric_accessibility,
        },
        {
            "label": _("IP Restriction"),
            "url": reverse_lazy("allowed-ips"),
            "accessibility": ip_restriction_accessibility,
        },
        {
            "label": _("Geo & Face Config"),
            "url": reverse_lazy("geo-face-config"),
            "accessibility": geo_face_accessibility,
        },
    ]
