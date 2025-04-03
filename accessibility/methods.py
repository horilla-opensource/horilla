"""
accessibility/methods.py
"""

from django.core.cache import cache

from accessibility.accessibility import ACCESSBILITY_FEATURE
from accessibility.filters import AccessibilityFilter
from accessibility.models import DefaultAccessibility
from horilla.horilla_middlewares import _thread_locals


def check_is_accessible(feature, cache_key, employee):
    """
    Method to check the employee is accessible for the feature or not
    """
    if not employee:
        return False

    accessibility = DefaultAccessibility.objects.filter(
        feature=feature, is_enabled=True
    ).first()

    if accessibility and accessibility.exclude_all:
        return False
    if not feature or not accessibility:
        return True

    data: dict = cache.get(cache_key, default={})
    if data and data.get(feature) is not None:
        return data.get(feature)

    employees = accessibility.employees.all()
    accessible = employee in employees
    return accessible


def update_employee_accessibility_cache(cache_key, employee):
    """
    Cache for get all the queryset
    """
    feature_accessible = {}
    for accessibility, _display in ACCESSBILITY_FEATURE:
        feature_accessible[accessibility] = check_is_accessible(
            accessibility, cache_key, employee
        )
    cache.set(cache_key, feature_accessible)
