"""
Tests for horilla/decorators.py

Covers:
- login_required — requires authenticated user with active Employee
- hx_request_required — requires HTMX header
- permission_required — requires specific Django permission
- manager_can_enter — permission OR reporting manager
"""

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory

from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# Helper: simple view for decorating
# ---------------------------------------------------------------------------
def simple_view(request, *args, **kwargs):
    """A trivial view that returns 200 OK."""
    return HttpResponse("OK", status=200)


def _add_messages_support(request):
    """Attach Django messages storage to a RequestFactory request.

    RequestFactory doesn't run middleware, so ``messages.info(request, ...)``
    fails unless we manually attach the storage backend.
    """
    setattr(request, "session", getattr(request, "session", SessionStore()))
    if not hasattr(request, "_messages"):
        setattr(request, "_messages", FallbackStorage(request))
    return request


# ---------------------------------------------------------------------------
# login_required
# ---------------------------------------------------------------------------
class LoginRequiredTests(HorillaTestCase):
    """Tests for the login_required decorator."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.decorated_view = login_required(simple_view)

    def _make_request(self, path="/test/", htmx=False):
        """Build a GET request with session and optional HTMX header."""
        kwargs = {}
        if htmx:
            kwargs["HTTP_HX_REQUEST"] = "true"
        request = self.factory.get(path, **kwargs)
        request.session = SessionStore()
        request.session.create()
        _add_messages_support(request)
        return request

    def test_anonymous_user_redirects(self):
        """Anonymous user gets 302 redirect to login."""
        request = self._make_request()
        request.user = AnonymousUser()
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_anonymous_user_htmx_returns_204(self):
        """Anonymous user with HTMX header gets 204 with HX-Refresh."""
        request = self._make_request(htmx=True)
        request.user = AnonymousUser()
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers.get("HX-Refresh"), "true")

    def test_authenticated_without_employee_redirects(self):
        """Authenticated user without employee_get attribute gets redirected."""
        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.employee_get = None  # No linked Employee
        request = self._make_request()
        request.user = mock_user
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_with_inactive_employee_redirects(self):
        """Authenticated user whose employee is_active=False gets redirected."""
        # Deactivate the employee
        self.regular_employee.is_active = False
        self.regular_employee.save()
        try:
            request = self._make_request()
            request.user = self.regular_user
            response = self.decorated_view(request)
            self.assertEqual(response.status_code, 302)
        finally:
            self.regular_employee.is_active = True
            self.regular_employee.save()

    def test_authenticated_with_active_employee_passes(self):
        """Authenticated user with active Employee gets 200."""
        request = self._make_request()
        request.user = self.admin_user
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_inactive_django_user_redirects(self):
        """User with is_active=False on the Django User gets redirected."""
        self.regular_user.is_active = False
        self.regular_user.save()
        try:
            request = self._make_request()
            request.user = self.regular_user
            response = self.decorated_view(request)
            self.assertEqual(response.status_code, 302)
        finally:
            self.regular_user.is_active = True
            self.regular_user.save()

    def test_sets_session_title_from_path(self):
        """The decorator extracts a title from the URL path and stores it in session."""
        request = self._make_request(path="/leave/requests/")
        request.user = self.admin_user
        self.decorated_view(request)
        self.assertEqual(request.session.get("title"), "LEAVE")

    def test_root_path_sets_dashboard_title(self):
        """Root path (/) sets title to 'DASHBOARD'."""
        request = self._make_request(path="/")
        request.user = self.admin_user
        self.decorated_view(request)
        self.assertEqual(request.session.get("title"), "DASHBOARD")

    def test_pms_path_maps_to_performance(self):
        """The /pms/ path gets mapped to 'Performance'."""
        request = self._make_request(path="/pms/goals/")
        request.user = self.admin_user
        self.decorated_view(request)
        self.assertEqual(request.session.get("title"), "Performance")


# ---------------------------------------------------------------------------
# hx_request_required
# ---------------------------------------------------------------------------
class HxRequestRequiredTests(HorillaTestCase):
    """Tests for the hx_request_required decorator."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.decorated_view = hx_request_required(simple_view)

    def test_without_htmx_header_returns_405(self):
        """Request without HTTP_HX_REQUEST header gets 405."""
        from unittest.mock import patch

        request = self.factory.get("/test/")
        request.user = self.admin_user
        _add_messages_support(request)
        # The 405.html template uses context processors that require full
        # middleware (not available via RequestFactory). Mock render to
        # verify the decorator calls it with status=405.
        mock_response = HttpResponse("Method Not Allowed", status=405)
        with patch("horilla.decorators.render", return_value=mock_response) as m:
            response = self.decorated_view(request)
            self.assertEqual(response.status_code, 405)
            m.assert_called_once_with(request, "405.html", status=405)

    def test_with_htmx_header_passes(self):
        """Request with HTTP_HX_REQUEST header passes through."""
        request = self.factory.get("/test/", HTTP_HX_REQUEST="true")
        request.user = self.admin_user
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_post_with_htmx_header_passes(self):
        """POST request with HTMX header also passes through."""
        request = self.factory.post("/test/", HTTP_HX_REQUEST="true")
        request.user = self.admin_user
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_preserves_function_name(self):
        """The decorator preserves the wrapped function's name."""
        self.assertEqual(self.decorated_view.__name__, "simple_view")


# ---------------------------------------------------------------------------
# permission_required
# ---------------------------------------------------------------------------
class PermissionRequiredTests(HorillaTestCase):
    """Tests for the permission_required decorator."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.decorated_view = permission_required("base.view_tags")(simple_view)

    def _make_request(self, user, htmx=False):
        kwargs = {}
        if htmx:
            kwargs["HTTP_HX_REQUEST"] = "true"
        request = self.factory.get("/test/", **kwargs)
        request.user = user
        request.session = SessionStore()
        request.session.create()
        _add_messages_support(request)
        request.META.setdefault("HTTP_REFERER", "/")
        return request

    def test_superuser_passes(self):
        """Superuser has all permissions implicitly."""
        request = self._make_request(self.admin_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_user_without_perm_denied(self):
        """User without the required permission gets redirected."""
        request = self._make_request(self.regular_user)
        response = self.decorated_view(request)
        # handle_no_permission redirects (302) for non-HTMX
        self.assertEqual(response.status_code, 302)

    def test_user_without_perm_htmx_renders_decorator_404(self):
        """HTMX request without permission renders decorator_404 template."""
        request = self._make_request(self.regular_user, htmx=True)
        response = self.decorated_view(request)
        # handle_no_permission renders decorator_404.html for HTMX requests
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, b"OK")

    def test_user_with_specific_perm_passes(self):
        """User with the exact required permission passes."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get(app_label="base", model="tags")
        perm = Permission.objects.get(content_type=ct, codename="view_tags")
        self.regular_user.user_permissions.add(perm)
        # Clear cached permissions
        self.regular_user = type(self.regular_user).objects.get(pk=self.regular_user.pk)

        request = self._make_request(self.regular_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# manager_can_enter
# ---------------------------------------------------------------------------
class ManagerCanEnterTests(HorillaTestCase):
    """Tests for the manager_can_enter decorator."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.decorated_view = manager_can_enter("base.view_tags")(simple_view)

    def _make_request(self, user, htmx=False):
        kwargs = {}
        if htmx:
            kwargs["HTTP_HX_REQUEST"] = "true"
        request = self.factory.get("/test/", **kwargs)
        request.user = user
        request.session = SessionStore()
        request.session.create()
        _add_messages_support(request)
        request.META.setdefault("HTTP_REFERER", "/")
        return request

    def test_user_with_perm_passes(self):
        """User with the required permission passes regardless of manager status."""
        request = self._make_request(self.admin_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_reporting_manager_without_perm_passes(self):
        """A reporting manager passes even without the specific permission.

        The manager_employee is set as reporting_manager_id for regular_employee
        in setUpTestData, so EmployeeWorkInformation.objects.filter(
            reporting_manager_id=manager_employee) returns a result.
        """
        request = self._make_request(self.manager_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_regular_employee_without_perm_denied(self):
        """Regular employee without perm and not a manager gets denied."""
        request = self._make_request(self.regular_user)
        response = self.decorated_view(request)
        # handle_no_permission: 302 redirect for non-HTMX, 200 template for HTMX
        self.assertEqual(response.status_code, 302)

    def test_regular_employee_with_perm_passes(self):
        """Regular employee with the required permission passes."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get(app_label="base", model="tags")
        perm = Permission.objects.get(content_type=ct, codename="view_tags")
        self.regular_user.user_permissions.add(perm)
        self.regular_user = type(self.regular_user).objects.get(pk=self.regular_user.pk)

        request = self._make_request(self.regular_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 200)

    def test_preserves_function_name(self):
        """manager_can_enter preserves the wrapped function name via @wraps."""
        self.assertEqual(self.decorated_view.__name__, "simple_view")

    def test_htmx_denied_renders_template(self):
        """HTMX request from non-manager without perm renders decorator_404."""
        request = self._make_request(self.regular_user, htmx=True)
        response = self.decorated_view(request)
        # handle_no_permission renders decorator_404.html for HTMX
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, b"OK")
