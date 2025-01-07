"""
employee/accessibility.py
"""

from django.utils.translation import gettext_lazy as _

from accessibility.accessibility import ACCESSBILITY_FEATURE

ACCESSBILITY_FEATURE += [
    ("profile_edit", _("Profile Edit Access")),
]
