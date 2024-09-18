"""
accessibility/methods.py
"""

from django.core.cache import cache
from horilla.horilla_middlewares import _thread_locals
from accessibility.models import DefaultAccessibility
from accessibility.filters import AccessibilityFilter


def check_is_accessibile(feature, cache_key, employee):
    """
    Method to check the employee is accessible for the feature or not
    """
    if not employee:
        return False

    accessibility = DefaultAccessibility.objects.filter(feature=feature).first()

    if not feature or not accessibility:
        return True

    data: dict = cache.get(cache_key, default={})
    if data and data.get(feature) is not None:
        return data.get(feature)

    filter = accessibility.filter
    employees = AccessibilityFilter(data=filter).qs
    accessibile = employee in employees
    return accessibile
