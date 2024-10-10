from functools import wraps

from django.http import HttpResponseForbidden
from django.utils.decorators import method_decorator


def or_condition(*decorators):
    """
    Combines multiple decorators with OR logic.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if any of the decorators allow access
            for dec in decorators:
                if dec(view_func)(request, *args, **kwargs):
                    return view_func(request, *args, **kwargs)
            # If none of the decorators allow access, return forbidden response
            return HttpResponseForbidden(
                "You don't have permission to access this page."
            )

        return _wrapped_view

    return decorator
