"""
accessibility/methods.py
"""

from django.core.cache import cache

from accessibility.filters import AccessibilityFilter
from accessibility.models import DefaultAccessibility
from horilla.horilla_middlewares import _thread_locals


def check_is_accessible(feature, cache_key, employee):
    """
    Method to check the employee is accessible for the feature or not
    """
    if not employee:
        return False

    accessibility = DefaultAccessibility.objects.filter(feature=feature).first()

    if accessibility and accessibility.exclude_all:
        return False
    if not feature or not accessibility:
        return True

    data: dict = cache.get(cache_key, default={})
    if data and data.get(feature) is not None:
        return data.get(feature)

    filter = accessibility.filter
    employees = AccessibilityFilter(data=filter).qs
    accessible = employee in employees
    return accessible
