"""
pms/sidebar.py
"""

from django.apps import apps
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.templatetags.basefilters import is_reportingmanager
from horilla.menu import settings_menu

MENU = _("Performance")
IMG_SRC = "images/ui/pms.svg"


SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("dashboard-view"),
    },
    {
        "menu": _("Objectives"),
        "redirect": reverse_lazy("objective-list-view"),
    },
    {
        "menu": _("Objective Template"),
        "redirect": reverse_lazy("objective-template-list-view"),
    },
    {
        "menu": _("360 Feedback"),
        "redirect": reverse_lazy("feedback-view"),
    },
    {
        "menu": _("Meetings"),
        "redirect": reverse_lazy("view-meetings"),
    },
    {
        "menu": _("Key Results"),
        "redirect": reverse_lazy("view-key-result"),
        "accessibility": "pms.sidebar.key_result_accessibility",
    },
    {
        "menu": _("Employee Bonus Point"),
        "redirect": reverse_lazy("employee-bonus-point"),
    },
    {
        "menu": _("Period"),
        "redirect": reverse_lazy("period-view"),
        "accessibility": "pms.sidebar.period_accessibility",
    },
    {
        "menu": _("Question Template"),
        "redirect": reverse_lazy("question-template-view"),
        "accessibility": "pms.sidebar.question_template_accessibility",
    },
]


def key_result_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_keyresult")


def period_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_period") or is_reportingmanager(request.user)


def question_template_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_questiontemplate") or is_reportingmanager(
        request.user
    )


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def bonus_point_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.add_bonuspointsetting")


@settings_menu.register
class PerformanceSettings:
    title = _("Performance")
    order = 8
    condition = lambda self, request: apps.is_installed("pms")
    items = [
        {
            "label": _("Bonus Point Setting"),
            "url": reverse_lazy("bonus-point-setting"),
            "accessibility": bonus_point_accessibility,
        },
    ]
