"""
accessibility/middlewares.py
"""

from django.core.cache import cache

from accessibility.methods import check_is_accessible
from accessibility.models import ACCESSBILITY_FEATURE

ACCESSIBILITY_CACHE_USER_KEYS = {}


def update_accessibility_cache(cache_key, request):
    """Cache for get all the queryset"""
    feature_accessible = {}
    for accessibility, _display in ACCESSBILITY_FEATURE:
        feature_accessible[accessibility] = check_is_accessible(
            accessibility, cache_key, getattr(request.user, "employee_get")
        )
    cache.set(cache_key, feature_accessible)


class AccessibilityMiddleware:
    """
    AccessibilityMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_key = request.session.session_key
        if session_key:
            cache_key = session_key + "accessibility_filter"
            exists_user_cache_key = ACCESSIBILITY_CACHE_USER_KEYS.get(
                request.user.id, []
            )
            if not exists_user_cache_key:
                ACCESSIBILITY_CACHE_USER_KEYS[request.user.id] = exists_user_cache_key
            if (
                session_key
                and getattr(request.user, "employee_get", None)
                and not cache.get(cache_key)
            ):
                exists_user_cache_key.append(cache_key)
                update_accessibility_cache(cache_key, request)
        response = self.get_response(request)
        return response
