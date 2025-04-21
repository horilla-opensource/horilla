"""
pms/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as trans

from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Performance")
IMG_SRC = "images/ui/pms.svg"


SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse_lazy("dashboard-view"),
    },
    {
        "menu": trans("Objectives"),
        "redirect": reverse_lazy("objective-list-view"),
    },
    {
        "menu": trans("360 Feedback"),
        "redirect": reverse_lazy("feedback-view"),
    },
    {
        "menu": trans("Meetings"),
        "redirect": reverse_lazy("view-meetings"),
    },
    {
        "menu": trans("Key Results"),
        "redirect": reverse_lazy("view-key-result"),
        "accessibility": "pms.sidebar.key_result_accessibility",
    },
    {
        "menu": trans("Employee Bonus Point"),
        "redirect": reverse_lazy("employee-bonus-point"),
    },
    {
        "menu": trans("Period"),
        "redirect": reverse_lazy("period-view"),
        "accessibility": "pms.sidebar.period_accessibility",
    },
    {
        "menu": trans("Question Template"),
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
