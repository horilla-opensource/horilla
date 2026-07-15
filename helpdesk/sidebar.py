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
        "menu": _("Tickets"),
        "redirect": reverse_lazy("ticket-view"),
    },
    {
        "menu": _("FAQs"),
        "redirect": reverse_lazy("faq-category-view"),
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
            "search_entries": [
                {
                    "text": _("Helpdesk Department Manager"),
                    "description": _(
                        "Assign managers responsible for helpdesk tickets per department"
                    ),
                },
            ],
        },
        {
            "label": _("Ticket Type"),
            "url": reverse_lazy("ticket-type-view"),
            "accessibility": ticket_type_accessibility,
            "search_entries": [
                {
                    "text": _("Ticket Type"),
                    "description": _("Define categories of helpdesk tickets"),
                },
                {
                    "text": _("Ticket Prefix"),
                    "description": _("Short prefix used in ticket IDs"),
                },
            ],
        },
        {
            "label": _("Helpdesk Tags"),
            "url": reverse_lazy("helpdesk-tag-view"),
            "accessibility": helpdesk_tag_accessibility,
            "search_entries": [
                {
                    "text": _("Helpdesk Tag"),
                    "description": _("Create tags for classifying helpdesk tickets"),
                },
            ],
        },
    ]
