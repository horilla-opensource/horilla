"""
recruitment/sidebar.py

To set Horilla sidebar for onboarding
"""

from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from recruitment.models import InterviewSchedule
from recruitment.templatetags.recruitmentfilters import is_stagemanager

MENU = trans("Recruitment")
ACCESSIBILITY = "recruitment.sidebar.menu_accessibilty"
IMG_SRC = "images/ui/recruitment.svg"

SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("recruitment-dashboard"),
    },
    {
        "menu": trans("Recruitment Pipeline"),
        "redirect": reverse("pipeline"),
        "accessibility": "recruitment.sidebar.pipeline_accessibility",
    },
    {
        "menu": trans("Recruitment Survey"),
        "redirect": reverse("recruitment-survey-question-template-view"),
        "accessibility": "recruitment.sidebar.survey_accessibility",
    },
    {
        "menu": trans("Candidates"),
        "redirect": reverse("candidate-view"),
        "accessibility": "recruitment.sidebar.candidates_accessibility",
    },
    {
        "menu": trans("Interview"),
        "redirect": reverse("interview-view"),
        "accessibility": "recruitment.sidebar.interview_accessibility",
    },
    {
        "menu": trans("Recruitment"),
        "redirect": reverse("recruitment-view"),
        "accessibility": "recruitment.sidebar.recruitment_accessibility",
    },
    {
        "menu": trans("Open Jobs"),
        "redirect": reverse("open-recruitments"),
        "accessibility": "recruitment.sidebar.recruitment_accessibility",
    },
    {
        "menu": trans("Stages"),
        "redirect": reverse("rec-stage-view"),
        "accessibility": "recruitment.sidebar.stage_accessibility",
    },
    {
        "menu": trans("Skill Zone"),
        "redirect": reverse("skill-zone-view"),
        "accessibility": "recruitment.sidebar.skill_zone_accessibility",
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
    return request.user.has_perm("recruitment.view_recruitmentsurvey")


def recruitment_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return request.user.has_perm("recruitment.view_recruitment")


def interview_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    interviews = InterviewSchedule.objects.all()
    interviewers = []
    for interview in interviews:
        for emp in interview.employee_id.all():
            interviewers.append(emp)
    if (
        getattr(request.user, "employee_get", None)
        and request.user.employee_get in interviewers
    ):
        view_interview = True
    else:
        view_interview = False

    return request.user.has_perm("recruitment.view_interviewschedule") or view_interview


def stage_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return request.user.has_perm("recruitment.view_stage")


def skill_zone_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return is_stagemanager(request.user) or request.user.has_perm(
        "recruitment.view_skillzone"
    )
