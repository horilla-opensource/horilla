"""
pms/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from base.templatetags.basefilters import is_reportingmanager

MENU = trans("Performance")
IMG_SRC = "images/ui/pms.svg"


SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("dashboard-view"),
    },
    {
        "menu": trans("Objectives"),
        "redirect": reverse("objective-list-view"),
    },
    {
        "menu": trans("360 Feedback"),
        "redirect": reverse("feedback-view"),
    },
    {
        "menu": trans("Meetings"),
        "redirect": reverse("view-meetings"),
    },
    {
        "menu": trans("Key Results"),
        "redirect": reverse("view-key-result"),
        "accessibility": "pms.sidebar.key_result_accessibility",
    },
    {
        "menu": trans("Employee Bonus Point"),
        "redirect": reverse("employee-bonus-point"),
    },
    {
        "menu": trans("Period"),
        "redirect": reverse("period-view"),
        "accessibility": "pms.sidebar.key_result_accessibility",
    },
    {
        "menu": trans("Question Template"),
        "redirect": reverse("question-template-view"),
        "accessibility": "pms.sidebar.question_template_accessibility",
    },
]


def key_result_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_period") or is_reportingmanager(request.user)


def question_template_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("pms.view_questiontemplate") or is_reportingmanager(
        request.user
    )
