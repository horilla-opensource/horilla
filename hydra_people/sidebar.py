from django.urls import reverse
from django.utils.translation import gettext_lazy as _


MENU = _("Hydra")
ACCESSIBILITY = "hydra_people.sidebar.menu_accessibility"
IMG_SRC = "images/ui/employees.svg"

SUBMENUS = [
    {
        "menu": _("People"),
        "redirect": reverse("hydra-person-list"),
        "accessibility": "hydra_people.sidebar.people_accessibility",
    },
    {
        "menu": _("Organization"),
        "redirect": reverse("hydra-organization"),
        "accessibility": "hydra_people.sidebar.organization_accessibility",
    },
    {
        "menu": _("Brigadier"),
        "redirect": reverse("hydra-brigadier-panel"),
        "accessibility": "hydra_people.sidebar.brigadier_accessibility",
    },
    {
        "menu": _("Coordinator"),
        "redirect": reverse("hydra-coordinator-panel"),
        "accessibility": "hydra_people.sidebar.coordinator_accessibility",
    },
    {
        "menu": _("Onboarding content"),
        "redirect": reverse("hydra-onboarding-dashboard"),
        "accessibility": "hydra_people.sidebar.onboarding_content_accessibility",
    },
    {
        "menu": _("Templates"),
        "redirect": reverse("hydra-template-list"),
        "accessibility": "hydra_people.sidebar.templates_accessibility",
    },
    {
        "menu": _("Public links"),
        "redirect": reverse("hydra-public-link-list"),
        "accessibility": "hydra_people.sidebar.public_links_accessibility",
    },
    {
        "menu": _("Reports"),
        "redirect": reverse("hydra-operational-report"),
        "accessibility": "hydra_people.sidebar.reports_accessibility",
    },
]


def menu_accessibility(request, *args, **kwargs):
    return (
        request.user.has_perm("hydra_people.view_person")
        or request.user.has_perm("hydra_coordination.view_location")
        or request.user.has_perm("hydra_coordination.view_brigadier_panel")
        or request.user.has_perm("hydra_coordination.view_coordinator_panel")
        or request.user.has_perm("hydra_onboarding.view_course")
        or request.user.has_perm("hydra_templates.view_messagetemplate")
        or request.user.has_perm("hydra_links.view_publichydralink")
        or request.user.has_perm("hydra_reports.view_operational_report")
    )


def people_accessibility(request, *args, **kwargs):
    return request.user.has_perm("hydra_people.view_person")


def organization_accessibility(request, *args, **kwargs):
    return request.user.has_perm("hydra_coordination.view_location")


def brigadier_accessibility(request, *args, **kwargs):
    return request.user.has_perms(
        (
            "hydra_coordination.view_brigadier_panel",
            "hydra_people.view_person",
            "employee.view_employee",
            "attendance.view_attendance",
            "leave.view_leaverequest",
        )
    )


def coordinator_accessibility(request, *args, **kwargs):
    return request.user.has_perms(
        (
            "hydra_coordination.view_coordinator_panel",
            "hydra_coordination.view_location",
            "hydra_people.view_person",
            "hydra_arrivals.view_arrivalplan",
            "hydra_legalization.view_legalizationcase",
        )
    )


def onboarding_content_accessibility(request, *args, **kwargs):
    return request.user.has_perms(
        (
            "hydra_onboarding.view_course",
            "hydra_onboarding.view_courseversion",
        )
    )


def templates_accessibility(request, *args, **kwargs):
    return request.user.has_perm("hydra_templates.view_messagetemplate")


def public_links_accessibility(request, *args, **kwargs):
    return request.user.has_perm("hydra_links.view_publichydralink")


def reports_accessibility(request, *args, **kwargs):
    return request.user.has_perms(
        (
            "hydra_reports.view_operational_report",
            "hydra_people.view_person",
            "hydra_coordination.view_personassignment",
            "hydra_coordination.view_location",
            "hydra_coordination.view_team",
            "hydra_arrivals.view_arrivalplan",
            "recruitment.view_candidate",
            "hydra_legalization.view_legalizationcase",
        )
    )
