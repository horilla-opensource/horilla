"""
Authentication utilities for the API
"""

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class SwaggerAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for Swagger UI
    """

    def authenticate(self, request):
        # Get the authentication header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        # Try JWT authentication first
        if auth_header.startswith("Bearer "):
            jwt_auth = JWTAuthentication()
            try:
                return jwt_auth.authenticate(request)
            except:
                pass

        # Fall back to session authentication
        if request.user and request.user.is_authenticated:
            return (request.user, None)

        return None


class RejectBasicAuthentication(authentication.BaseAuthentication):
    """
    Explicitly reject HTTP Basic Auth across the API with a clear error message.
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Basic "):
            raise AuthenticationFailed(
                "Basic authentication is disabled. Use Bearer token (JWT) in the Authorization header."
            )
        return None
