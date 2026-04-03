"""
Tests for horilla/horilla_middlewares.py

Covers:
- ThreadLocalMiddleware — stores request in _thread_locals.request
- MethodNotAllowedMiddleware — renders 405.html for HttpResponseNotAllowed
- SVGSecurityMiddleware — adds CSP + nosniff headers for SVG files
- MissingParameterMiddleware — catches KeyError, renders went_wrong.html (400)
"""

import threading
from unittest.mock import patch

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound
from django.test import RequestFactory, SimpleTestCase, override_settings

from horilla.horilla_middlewares import (
    MethodNotAllowedMiddleware,
    MissingParameterMiddleware,
    SVGSecurityMiddleware,
    ThreadLocalMiddleware,
    _thread_locals,
)


# ---------------------------------------------------------------------------
# Helper: simple views and get_response callables
# ---------------------------------------------------------------------------
def _ok_response(request):
    """Simulate a view that returns 200 OK."""
    return HttpResponse("OK", status=200)


def _not_allowed_response(request):
    """Simulate a view that returns 405 Method Not Allowed."""
    return HttpResponseNotAllowed(["POST"])


def _not_found_response(request):
    """Simulate a view that returns 404 Not Found."""
    return HttpResponseNotFound("Not Found")


def _raise_key_error(request):
    """Simulate a view that raises KeyError (missing parameter)."""
    raise KeyError("employee_id")


def _raise_value_error(request):
    """Simulate a view that raises ValueError (non-KeyError)."""
    raise ValueError("something went wrong")


# ---------------------------------------------------------------------------
# ThreadLocalMiddleware
# ---------------------------------------------------------------------------
class ThreadLocalMiddlewareTests(SimpleTestCase):
    """Tests for ThreadLocalMiddleware — stores request in thread-local."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ThreadLocalMiddleware(_ok_response)

    def test_sets_thread_local_request(self):
        """After __call__, _thread_locals.request should be set to the request."""
        request = self.factory.get("/test/")
        self.middleware(request)
        self.assertIs(_thread_locals.request, request)

    def test_request_accessible_after_middleware(self):
        """The stored request object is the same Python object passed in."""
        request = self.factory.post("/submit/")
        self.middleware(request)
        self.assertEqual(_thread_locals.request.method, "POST")
        self.assertEqual(_thread_locals.request.path, "/submit/")

    def test_returns_response_from_get_response(self):
        """Middleware should pass through the response from the downstream view."""
        request = self.factory.get("/test/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_different_requests_overwrite_thread_local(self):
        """Each call replaces _thread_locals.request with the new request."""
        request_a = self.factory.get("/page-a/")
        request_b = self.factory.get("/page-b/")

        self.middleware(request_a)
        self.assertIs(_thread_locals.request, request_a)

        self.middleware(request_b)
        self.assertIs(_thread_locals.request, request_b)
        self.assertIsNot(_thread_locals.request, request_a)

    def test_thread_isolation(self):
        """Each thread should have its own _thread_locals.request."""
        request_main = self.factory.get("/main/")
        self.middleware(request_main)

        other_thread_request = [None]

        def worker():
            req = self.factory.get("/worker/")
            mw = ThreadLocalMiddleware(_ok_response)
            mw(req)
            other_thread_request[0] = getattr(_thread_locals, "request", None)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # Main thread still has its own request
        self.assertIs(_thread_locals.request, request_main)
        # Worker thread had a different request
        self.assertIsNotNone(other_thread_request[0])
        self.assertEqual(other_thread_request[0].path, "/worker/")


# ---------------------------------------------------------------------------
# MethodNotAllowedMiddleware
# ---------------------------------------------------------------------------
class MethodNotAllowedMiddlewareTests(SimpleTestCase):
    """Tests for MethodNotAllowedMiddleware — renders 405.html on 405 responses."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch("horilla.horilla_middlewares.render")
    def test_renders_405_for_not_allowed_response(self, mock_render):
        """HttpResponseNotAllowed triggers render of 405.html with status 405."""
        mock_render.return_value = HttpResponse("Method Not Allowed", status=405)
        middleware = MethodNotAllowedMiddleware(_not_allowed_response)
        request = self.factory.get("/test/")

        response = middleware(request)

        mock_render.assert_called_once_with(request, "405.html", status=405)
        self.assertEqual(response.status_code, 405)

    def test_passes_through_200_response(self):
        """Normal 200 responses should pass through unchanged."""
        middleware = MethodNotAllowedMiddleware(_ok_response)
        request = self.factory.get("/test/")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_passes_through_404_response(self):
        """404 responses should pass through unchanged (not 405)."""
        middleware = MethodNotAllowedMiddleware(_not_found_response)
        request = self.factory.get("/test/")

        response = middleware(request)

        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# SVGSecurityMiddleware
# ---------------------------------------------------------------------------
class SVGSecurityMiddlewareTests(SimpleTestCase):
    """Tests for SVGSecurityMiddleware — adds CSP + nosniff for SVG files."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SVGSecurityMiddleware(_ok_response)

    def test_adds_csp_header_for_svg(self):
        """SVG requests with 200 status get Content-Security-Policy header."""
        request = self.factory.get("/static/icons/logo.svg")
        response = self.middleware(request)

        self.assertEqual(
            response["Content-Security-Policy"],
            "default-src 'none'; style-src 'unsafe-inline';",
        )

    def test_adds_nosniff_header_for_svg(self):
        """SVG requests with 200 status get X-Content-Type-Options: nosniff."""
        request = self.factory.get("/media/uploads/image.svg")
        response = self.middleware(request)

        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_no_headers_for_non_svg(self):
        """Non-SVG requests should NOT get SVG security headers."""
        request = self.factory.get("/static/style.css")
        response = self.middleware(request)

        self.assertNotIn("Content-Security-Policy", response)
        self.assertNotIn("X-Content-Type-Options", response)

    def test_no_headers_for_svg_with_non_200_status(self):
        """SVG requests with non-200 status should NOT get security headers."""
        middleware = SVGSecurityMiddleware(_not_found_response)
        request = self.factory.get("/missing/icon.svg")
        response = middleware(request)

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Content-Security-Policy", response)
        self.assertNotIn("X-Content-Type-Options", response)


# ---------------------------------------------------------------------------
# MissingParameterMiddleware
# ---------------------------------------------------------------------------
class MissingParameterMiddlewareTests(SimpleTestCase):
    """Tests for MissingParameterMiddleware — catches KeyError, returns 400."""

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(DEBUG=False)
    @patch("horilla.horilla_middlewares.render")
    @patch("horilla.horilla_middlewares.messages")
    def test_catches_key_error_in_production(self, mock_messages, mock_render):
        """KeyError triggers went_wrong.html render with 400 status in production."""
        mock_render.return_value = HttpResponse("Bad Request", status=400)
        middleware = MissingParameterMiddleware(_ok_response)
        request = self.factory.get("/test/")

        exception = KeyError("employee_id")
        response = middleware.process_exception(request, exception)

        mock_messages.error.assert_called_once()
        call_args = mock_messages.error.call_args
        self.assertIn("employee_id", call_args[0][1])
        mock_render.assert_called_once_with(request, "went_wrong.html", status=400)
        self.assertEqual(response.status_code, 400)

    @override_settings(DEBUG=True)
    def test_returns_none_for_key_error_in_debug(self):
        """In DEBUG mode, KeyError should propagate (return None)."""
        middleware = MissingParameterMiddleware(_ok_response)
        request = self.factory.get("/test/")

        exception = KeyError("missing_param")
        response = middleware.process_exception(request, exception)

        self.assertIsNone(response)

    def test_returns_none_for_non_key_error(self):
        """Non-KeyError exceptions should return None (not handled)."""
        middleware = MissingParameterMiddleware(_ok_response)
        request = self.factory.get("/test/")

        exception = ValueError("something else")
        response = middleware.process_exception(request, exception)

        self.assertIsNone(response)

    def test_call_passes_through_normal_response(self):
        """The __call__ method simply delegates to get_response."""
        middleware = MissingParameterMiddleware(_ok_response)
        request = self.factory.get("/test/")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")
