"""
recruitment/sidebar.py

To set Horilla sidebar for onboarding
"""

from django.apps import apps
from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu
from recruitment.models import InterviewSchedule
from recruitment.templatetags.recruitmentfilters import (
    is_recruitmentmangers,
    is_stagemanager,
)

MENU = _("Recruitment")
ACCESSIBILITY = "recruitment.sidebar.menu_accessibilty"
IMG_SRC = "images/ui/recruitment.svg"

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse("recruitment-dashboard"),
    },
    {
        "menu": _("Recruitment Pipeline"),
        "redirect": reverse("cbv-pipeline"),
        "accessibility": "recruitment.sidebar.pipeline_accessibility",
    },
    {
        "menu": _("Open Recruitments"),
        "redirect": reverse("open-recruitments"),
        "accessibility": "recruitment.sidebar.recruitment_accessibility",
    },
    {
        "menu": _("Candidates"),
        "redirect": reverse("candidate-view"),
        "accessibility": "recruitment.sidebar.candidates_accessibility",
        # The candidate edit page (candidate-update/<id>/) is a sibling URL, not a
        # sub-path of candidate-view/, so it needs an explicit prefix here for the
        # sidebar's path-based active-link highlighting to match it.
        "match_prefixes": ["/recruitment/candidate-update/"],
    },
    {
        "menu": _("Interviews"),
        "redirect": reverse("interview-view"),
        "accessibility": "recruitment.sidebar.interview_accessibility",
    },
    {
        "menu": _("Job Openings"),
        "redirect": reverse("recruitment-view"),
        "accessibility": "recruitment.sidebar.recruitment_accessibility",
    },
    {
        "menu": _("Recruitment Survey"),
        "redirect": reverse("recruitment-survey-question-template-view"),
        "accessibility": "recruitment.sidebar.survey_accessibility",
    },
    {
        "menu": _("Talent Pool"),
        "redirect": reverse("skill-zone-view"),
        "accessibility": "recruitment.sidebar.skill_zone_accessibility",
    },
    {
        "menu": _("Configuration"),
        "redirect": reverse("recruitment-settings-view"),
        "accessibility": "recruitment.sidebar.recruitment_settings_accessibility",
    },
]


def menu_accessibilty(
    request, _menu: str = "", user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return is_stagemanager(request.user) or "recruitment" in user_perms


def pipeline_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    _submenu["redirect"] = _submenu["redirect"] + "?closed=false"
    return is_stagemanager(request.user) or request.user.has_perm(
        "recruitment.view_recruitment"
    )


def candidates_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return request.user.has_perm("recruitment.view_candidate")


def survey_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    _submenu["redirect"] = _submenu["redirect"] + "?closed=false"
    return is_recruitmentmangers(request.user) or request.user.has_perm(
        "recruitment.view_recruitmentsurvey"
    )


def recruitment_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return request.user.has_perm("recruitment.view_recruitment")


def interview_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    employee = getattr(request.user, "employee_get", None)
    view_interview = (
        bool(employee)
        and InterviewSchedule.objects.filter(employee_id=employee).exists()
    )

    return request.user.has_perm("recruitment.view_interviewschedule") or view_interview


def skill_zone_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return is_stagemanager(request.user) or request.user.has_perm(
        "recruitment.view_skillzone"
    )


def recruitment_settings_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        request.user.has_perm("recruitment.view_rejectreason")
        or request.user.has_perm("recruitment.view_recruitment")
        or request.user.has_perm("recruitment.view_stage")
    )


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    return is_stagemanager(request.user) or "recruitment" in user_perms


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def self_tracking_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("recruitment.view_recruitment")


@settings_menu.register
class RecruitmentSettings:
    title = _("Recruitment")
    order = 4
    condition = lambda self, request: apps.is_installed("recruitment")
    items = [
        {
            "label": _("Candidate Portal"),
            "url": reverse_lazy("self-tracking-feature"),
            "accessibility": self_tracking_accessibility,
            "search_entries": [
                {
                    "text": _("Application Tracking"),
                    "description": _(
                        "Allow candidates to track their recruitment pipeline status"
                    ),
                },
                {
                    "text": _("Rating Visibility"),
                    "description": _(
                        "Allow candidates to view their recruitment rating"
                    ),
                },
            ],
        },
    ]
