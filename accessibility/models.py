"""
accessibility/models.py
"""

from django.db import models
from horilla.models import HorillaModel
from accessibility.accessibility import ACCESSBILITY_FEATURE


class DefaultAccessibility(HorillaModel):
    """
    DefaultAccessibilityModel
    """

    feature = models.CharField(max_length=100, choices=ACCESSBILITY_FEATURE)
    filter = models.JSONField()
