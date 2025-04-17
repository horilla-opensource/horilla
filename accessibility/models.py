"""
accessibility/models.py
"""

from django.db import models

from accessibility.accessibility import ACCESSBILITY_FEATURE
from employee.models import Employee
from horilla.models import HorillaModel


class DefaultAccessibility(HorillaModel):
    """
    DefaultAccessibilityModel
    """

    feature = models.CharField(max_length=100, choices=ACCESSBILITY_FEATURE)
    filter = models.JSONField()
    exclude_all = models.BooleanField(default=False)
    employees = models.ManyToManyField(
        Employee, blank=True, related_name="default_accessibility"
    )
    is_enabled = models.BooleanField(default=True)
