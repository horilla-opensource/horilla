"""
helpdesk/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Help Desk")
IMG_SRC = "images/ui/headset-solid.svg"

SUBMENUS = [
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("helpdesk-modern-dashboard"),
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
