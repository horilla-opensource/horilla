"""
helpdesk/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

MENU = trans("Help Desk")
IMG_SRC = "images/ui/headset-solid.svg"

SUBMENUS = [
    {
        "menu": trans("FAQs"),
        "redirect": reverse("faq-category-view"),
    },
    {
        "menu": trans("Tickets"),
        "redirect": reverse("ticket-view"),
    },
]
