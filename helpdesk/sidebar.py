"""
helpdesk/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

MENU = trans("")
IMG_SRC = "images/ui/headset-solid.svg"

SUBMENUS = [
    {
        "menu": trans(""),
        "redirect": reverse("faq-category-view"),
    },
    {
        "menu": trans(""),
        "redirect": reverse("ticket-view"),
    },
]
