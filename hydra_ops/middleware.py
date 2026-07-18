import re
import time
import uuid

from django.conf import settings
from django.http import HttpResponseNotFound

from hydra_ops.logging import request_id_context


SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class RequestIdMiddleware:
    """Attach one safe correlation id without recording request secrets."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if SAFE_REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        request.hydra_request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            elapsed_ms = (time.perf_counter() - started) * 1000
            response["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
            return response
        finally:
            request_id_context.reset(token)


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
