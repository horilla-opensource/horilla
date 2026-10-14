"""
horilla_middlewares.py

This module is used to register horilla's middlewares without affecting the horilla/settings.py
"""

import threading
from contextvars import ContextVar

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django.utils.datastructures import MultiValueDictKeyError

from horilla.config import logger
from horilla.http.response import HorillaRedirect

_request_var = ContextVar("request", default=None)
current_company_id = ContextVar("current_company_id", default=None)
_thread_local_state = ContextVar("thread_local_state", default={})


class _ThreadLocalProxy:
    def __getattr__(self, name):
        if name == "request":
            return _request_var.get()
        state = _thread_local_state.get()
        if name in state:
            return state[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "request":
            _request_var.set(value)
        else:
            state = dict(_thread_local_state.get())
            state[name] = value
            _thread_local_state.set(state)


_thread_locals = _ThreadLocalProxy()


class ThreadLocalMiddleware:
    """
    ThreadLocalMiddleWare
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            # Clear on the way out. Threads are reused -- by a worker for the
            # next request, and by the test runner for the next test -- so a
            # request left here outlives the one it belongs to. Anything that
            # reads it later (HorillaModel.save() stamps created_by/modified_by
            # from request.user) then attributes work to a stale user. In tests
            # that surfaces as an IntegrityError at teardown: modified_by_id
            # points at a user whose transaction has already rolled back.
            _thread_locals.request = None


class DefaultLanguageMiddleware:
    """
    Runs before django.middleware.locale.LocaleMiddleware to stop it from
    picking a language via the browser's Accept-Language header. Django's
    set_language view (used by the navbar language switcher) only persists
    an explicit choice in the LANGUAGE_COOKIE_NAME cookie, so that cookie
    is the sole signal that should override settings.LANGUAGE_CODE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            request.META.pop("HTTP_ACCEPT_LANGUAGE", None)
        return self.get_response(request)


class MethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            return render(request, "405.html", status=405)
        return response


class SVGSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Apply security headers to SVG files
        if request.path.endswith(".svg") and response.status_code == 200:
            response["Content-Security-Policy"] = (
                "default-src 'none'; style-src 'unsafe-inline';"
            )
            response["X-Content-Type-Options"] = "nosniff"

        return response


class MissingParameterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, KeyError):
            missing_key = str(exception).strip("'")
            message = f"Required parameter '{missing_key}' is missing from the request."

            logger.error(message)

            return HorillaRedirect(request, message=message)

        elif isinstance(exception, ObjectDoesNotExist):
            logger.error(f"{exception.__class__.__name__}: {exception}")

            return HorillaRedirect(
                request, message="The requested item could not be found."
            )

        return None


def set_selected_company(company_id):
    current_company_id.set(company_id)


def get_selected_company():
    return current_company_id.get()


class BulkDeleteSummaryMiddleware:
    """
    Drops the toast messages of a bulk delete the browser is already reporting.

    static/index/index.js wraps every bulk-delete call: progress dialog, then a
    Total / Deleted / Failed result dialog worked out from which ids still
    exist. It marks those requests with X-Hlv-Bulk-Delete. The views still queue
    a toast per record ("You cannot delete X"), which would show up on top of
    that dialog (or, after a page reload, long after it), so they're discarded
    here instead of being edited out of every view. Bulk approve / reject views
    do the same by returning X-Hlv-Bulk-Result
    (horilla.http.response.with_bulk_result).

    Must sit after MessageMiddleware in MIDDLEWARE: responses unwind in reverse,
    so this runs before the messages are written back to the session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.headers.get("X-Hlv-Bulk-Delete") or response.has_header(
            "X-Hlv-Bulk-Result"
        ):
            storage = getattr(request, "_messages", None)
            if storage is not None:
                # Iterating marks every queued message as used.
                list(storage)
        return response
