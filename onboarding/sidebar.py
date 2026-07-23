"""
onboarding/sidebar.py

To set Horilla sidebar for onboarding
"""

from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from onboarding.templatetags.onboardingfilters import is_taskmanager

MENU = _("Onboarding")
ACCESSIBILITY = "onboarding.sidebar.menu_accessibilty"
IMG_SRC = "images/ui/rocket.svg"

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse("onboarding-dashboard"),
    },
    {
        "menu": _("Candidates"),
        "redirect": reverse("candidates-view"),
        "accessibility": "onboarding.sidebar.candidates_view_accessibility",
        # The "Create" button on this page links to recruitment's standalone
        # candidate-create/ page (a sibling URL under a different app prefix,
        # not a sub-path of candidates-view/), so it needs an explicit prefix
        # here for the sidebar's path-based active-link highlighting to match it.
        "match_prefixes": ["/recruitment/candidate-create/"],
    },
    {
        "menu": _("Onboarding Tasks"),
        "redirect": reverse("cbv-pipeline-onboarding") + "?closed=false",
        "accessibility": "onboarding.sidebar.onboarding_view_accessibility",
    },
]


def menu_accessibilty(
    request, _menu: str = "", user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return (
        is_taskmanager(request.user)
        or "recruitment" in user_perms
        or "onboarding" in user_perms
    )


def onboarding_view_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return is_taskmanager(request.user) or request.user.has_perm(
        "onboarding.view_onboardingstage"
    )


def candidates_view_accessibility(
    request, _submenu: dict = {}, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    return request.user.has_perm("onboarding.view_onboardingcandidate")
