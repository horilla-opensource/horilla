"""
Settings-menu registration for the tour engine.

Adds a "Product Tours" section to the Settings sidebar (the modern
``horilla.menu.settings_menu`` registry). Imported from ``apps.py`` ready()
so the registration runs at startup.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu


def tour_settings_accessibility(
    request, submenu=None, user_perms=None, *args, **kwargs
):
    """Only show to users who can view tours."""
    return request.user.has_perm("horilla_tour.view_tour")


@settings_menu.register
class TourSettings:
    title = _("Product Tours")
    order = 60
    items = [
        {
            "label": _("Manage Tours"),
            "url": reverse_lazy("tour-section"),
            "accessibility": tour_settings_accessibility,
            "search_entries": [
                {
                    "text": _("Manage Tours"),
                    "description": _(
                        "Create and manage guided product tours for users"
                    ),
                },
                {
                    "text": _("Product Tours"),
                    "description": _(
                        "Step-by-step interactive tours to onboard users to features"
                    ),
                },
                {
                    "text": _("Tour Steps"),
                    "description": _(
                        "Configure individual steps within a product tour"
                    ),
                },
                {
                    "text": _("Auto Start Tour"),
                    "description": _(
                        "Automatically launch a tour when a user visits a page"
                    ),
                },
            ],
        },
    ]
