"""
Decorators for API views
"""

from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def api_authentication_required(view_func):
    """
    Decorator to ensure API views require authentication
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return view_func(request, *args, **kwargs)

    return wrapped_view
