"""
assets/sidebar.py
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

MENU = trans("Assets")
IMG_SRC = "images/ui/assets.svg"

SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("asset-dashboard"),
        "accessability": "asset.sidebar.dashboard_accessability",
    },
    {
        "menu": trans("Asset View"),
        "redirect": reverse("asset-category-view"),
        "accessability": "asset.sidebar.dashboard_accessability",
    },
    {
        "menu": trans("Request and Allocation"),
        "redirect": reverse("asset-request-allocation-view"),
    },
    {
        "menu": trans("Asset History"),
        "redirect": reverse("asset-history"),
    },
]


def dashboard_accessability(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("asset.view_assetcategory")
