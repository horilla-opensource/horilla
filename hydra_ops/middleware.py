from django.conf import settings
from django.http import HttpResponseNotFound


class DisableDatabaseInitializationMiddleware:
    """Hide upstream unauthenticated database bootstrap routes outside development."""

    blocked_prefixes = (
        "/initialize-",
        "/load-demo-database",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION", True):
            if request.path.startswith(self.blocked_prefixes):
                return HttpResponseNotFound()
        return self.get_response(request)
