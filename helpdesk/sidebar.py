"""
helpdesk/sidebar.py
"""

from django.apps import apps
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu

MENU = _("Helpdesk")
IMG_SRC = "images/ui/headset-solid.svg"

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("helpdesk-dashboard"),
        "accessibility": "helpdesk.sidebar.dashboard_accessibility",
    },
    {
        "menu": _("FAQs"),
        "redirect": reverse_lazy("faq-category-view"),
    },
    {
        "menu": _("Tickets"),
        "redirect": reverse_lazy("ticket-view"),
    },
]


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("helpdesk.view_ticket")


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def department_manager_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("helpdesk.view_departmentmanager")


def ticket_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("helpdesk.view_tickettype")


def helpdesk_tag_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("helpdesk.view_tag")


@settings_menu.register
class HelpdeskSettings:
    title = _("Helpdesk")
    order = 9
    condition = lambda self, request: apps.is_installed("helpdesk")
    items = [
        {
            "label": _("Department Managers"),
            "url": reverse_lazy("department-manager-view"),
            "accessibility": department_manager_accessibility,
        },
        {
            "label": _("Ticket Type"),
            "url": reverse_lazy("ticket-type-view"),
            "accessibility": ticket_type_accessibility,
        },
        {
            "label": _("Helpdesk Tags"),
            "url": reverse_lazy("helpdesk-tag-view"),
            "accessibility": helpdesk_tag_accessibility,
        },
    ]
