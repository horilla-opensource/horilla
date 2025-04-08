"""
offboarding/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.context_processors import resignation_request_enabled
from offboarding.templatetags.offboarding_filter import (
    any_manager,
    is_offboarding_employee,
)

MENU = _("Offboarding")
IMG_SRC = "images/ui/exit-outline.svg"
ACCESSIBILITY = "offboarding.sidebar.offboarding_accessibility"


SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse("offboarding-dashboard"),
        "accessibility": "offboarding.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("Exit Process"),
        "redirect": reverse("offboarding-pipeline"),
    },
    {
        "menu": _("Resignation Letters"),
        "redirect": reverse("resignation-request-view"),
        "accessibility": "offboarding.sidebar.resignation_letter_accessibility",
    },
]


def offboarding_accessibility(request, menu, user_perms, *args, **kwargs):
    accessible = False
    try:
        accessible = (
            request.user.has_module_perms("offboarding")
            or any_manager(request.user.employee_get)
            or is_offboarding_employee(request.user.employee_get)
        )
    finally:
        return accessible


def resignation_letter_accessibility(request, menu, user_perms, *args, **kwargs):
    return resignation_request_enabled(request)[
        "enabled_resignation_request"
    ] and request.user.has_perm("offboarding.view_resignationletter")


def dashboard_accessibility(request, *args):
    """
    Check if the user has permission to view the dashboard.
    """

    return request.user.has_module_perms("offboarding") or any_manager(
        request.user.employee_get
    )
