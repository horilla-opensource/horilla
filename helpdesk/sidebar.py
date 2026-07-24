"""
helpdesk/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Helpdesk")
IMG_SRC = "images/ui/headset-solid.svg"

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("helpdesk-dashboard"),
        "accessibility": "helpdesk.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("Tickets"),
        "redirect": reverse_lazy("ticket-view"),
    },
    {
        "menu": _("FAQs"),
        "redirect": reverse_lazy("faq-category-view"),
        # The individual FAQ list page (faq-view/<id>/) is a sibling URL, not a
        # sub-path of faq-category-view/, so it needs an explicit prefix here
        # for the sidebar's path-based active-link highlighting to match it.
        "match_prefixes": ["/helpdesk/faq-view/"],
    },
    {
        "menu": _("Configuration"),
        "redirect": reverse_lazy("helpdesk-settings-view"),
        "accessibility": "helpdesk.sidebar.helpdesk_settings_accessibility",
    },
]


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("helpdesk.view_ticket")


def helpdesk_settings_accessibility(request, submenu, user_perms, *args, **kwargs):
    return (
        request.user.has_perm("helpdesk.view_departmentmanager")
        or request.user.has_perm("helpdesk.view_tickettype")
        or request.user.has_perm("base.view_tags")
    )
