"""Report sidebar accessibility and export-gate smoke/deepen tests."""

import json
from types import SimpleNamespace

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase

from horilla.testkit import make_user
from report.sidebar import employee_accessibility, menu_accessibility
from report.views import check_export_access


def _call_check_export_access(request):
    """Invoke view body, skipping @login_required wrapper."""
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(request)
    request.session.save()
    view = check_export_access
    while hasattr(view, "__wrapped__"):
        view = view.__wrapped__
    return view(request)


class ReportSidebarAccessibilityTests(SimpleTestCase):
    def test_employee_accessibility_with_perm(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_superuser=False,
                has_perm=lambda p: p == "employee.view_employee",
            )
        )
        self.assertTrue(employee_accessibility(request, None, None))

    def test_employee_accessibility_without_perm(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_superuser=False,
                has_perm=lambda p: False,
            )
        )
        self.assertFalse(employee_accessibility(request, None, None))

    def test_menu_accessibility_superuser(self):
        request = SimpleNamespace(
            user=SimpleNamespace(is_superuser=True, has_perm=lambda p: False)
        )
        self.assertTrue(menu_accessibility(request, None, None))


class ReportExportAccessEndpointTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = make_user("report_export", password="secret123")

    def test_bad_model_not_allowed(self):
        request = self.factory.get(
            "/report/check-export-access/", {"model": "not.a.model"}
        )
        request.user = self.user
        response = _call_check_export_access(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"allowed": False})

    def test_employee_model_allowed_by_default(self):
        request = self.factory.get(
            "/report/check-export-access/", {"model": "employee.Employee"}
        )
        request.user = self.user
        response = _call_check_export_access(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"allowed": True})
