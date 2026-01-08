from django.http import JsonResponse


class RejectBasicAuthMiddleware:
    """
    Middleware that rejects HTTP Basic Authentication globally with a consistent message.
    This ensures endpoints that override DRF authentication classes still reject Basic.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if isinstance(auth_header, str) and auth_header.startswith("Basic "):
            return JsonResponse(
                {
                    "error": "Basic authentication is disabled",
                    "detail": "Use Bearer token (JWT) in the Authorization header.",
                },
                status=401,
            )
        return self.get_response(request)
