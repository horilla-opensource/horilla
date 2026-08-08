"""Accessibility middleware and check_is_accessible smoke tests."""

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accessibility.methods import check_is_accessible
from accessibility.middlewares import AccessibilityMiddleware
from accessibility.models import DefaultAccessibility
from horilla.testkit import make_company, make_employee, make_user


class CheckIsAccessibleTests(TestCase):
    def test_no_employee_returns_false(self):
        self.assertFalse(check_is_accessible("dummy", "cache-key", None))

    def test_no_feature_config_returns_true(self):
        company = make_company("Access Co")
        emp = make_employee(company=company, email="acc@test.horilla")
        self.assertTrue(check_is_accessible("missing_feature", "ck", emp))

    def test_exclude_all_returns_false(self):
        company = make_company("Access Exclude")
        emp = make_employee(company=company, email="ex@test.horilla")
        DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=True,
            is_enabled=True,
        )
        self.assertFalse(check_is_accessible("employee_view", "ck-ex", emp))


class AccessibilityMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _with_session(self, request):
        middleware = SessionMiddleware(lambda r: HttpResponse("ok"))
        middleware.process_request(request)
        request.session.save()
        return request

    def test_anonymous_request_passes_through(self):
        request = self._with_session(self.factory.get("/health/"))
        request.user = AnonymousUser()

        def get_response(req):
            return HttpResponse("anon-ok")

        mw = AccessibilityMiddleware(get_response)
        response = mw(request)
        self.assertEqual(response.content, b"anon-ok")

    def test_authenticated_employee_request_passes_through(self):
        company = make_company("Access Mw")
        user = make_user("acc_mw", password="pass")
        make_employee(
            company=company,
            email="acc_mw@test.horilla",
            user=user,
        )

        request = self._with_session(self.factory.get("/employee/"))
        request.user = user

        def get_response(req):
            return HttpResponse("auth-ok")

        mw = AccessibilityMiddleware(get_response)
        response = mw(request)
        self.assertEqual(response.content, b"auth-ok")
