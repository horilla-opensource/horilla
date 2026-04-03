"""
Shared test base classes for Horilla HRMS.

Provides HorillaTestCase with helpers for:
- _thread_locals mock (created_by/modified_by)
- Company middleware simulation
- HTMX request helpers
- Authenticated client helpers
- Multi-tenant test fixtures
"""

from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TestCase

from horilla.horilla_middlewares import _thread_locals


class _MockRequest:
    """
    Lightweight request mock that does NOT auto-create nested attributes
    like MagicMock does. This prevents Employee.save() from getting
    MagicMock objects where it expects real model instances.
    """

    def __init__(self, user=None):
        self.user = user
        self.session = {}
        self.GET = {}
        self.POST = {}
        self.META = {}
        self.path = "/test/"
        self.method = "GET"
        self.COOKIES = {}
        # Django messages framework needs this attribute
        from django.contrib.messages.storage.fallback import FallbackStorage

        self._messages = FallbackStorage(self)


class HorillaTestCase(TestCase):
    """
    Base test class for all Horilla tests.

    Provides:
    - Shared Company A + Company B fixtures for multi-tenant testing
    - Admin/Manager/Employee user+employee combos
    - _thread_locals request mock
    - HTMX request helpers
    """

    @classmethod
    def setUpTestData(cls):
        # Set _thread_locals.request early so HorillaCompanyManager.get_queryset()
        # can access request.session during model creation (e.g., LeaveType, Allowance).
        # Uses AnonymousUser since no real user exists yet at this point.
        from django.contrib.auth.models import AnonymousUser

        from base.models import Company, Department, EmployeeShift, JobPosition
        from employee.models import Employee
        from horilla_auth.models import HorillaUser

        _thread_locals.request = _MockRequest(user=AnonymousUser())

        cls.company_a = Company.objects.create(
            company="Test Company A",
            address="123 Test St",
            country="US",
            state="CA",
            city="San Francisco",
            zip="94105",
            hq=True,
        )
        cls.company_b = Company.objects.create(
            company="Test Company B",
            address="456 Other St",
            country="US",
            state="NY",
            city="New York",
            zip="10001",
        )
        cls.department = Department.objects.create(department="Engineering")
        cls.department.company_id.add(cls.company_a)

        # Admin employee (superuser)
        cls.admin_employee = Employee.objects.create(
            employee_first_name="Admin",
            employee_last_name="User",
            email="admin@testcompany.com",
            phone="5550000001",
            gender="male",
        )
        cls.admin_user = cls.admin_employee.employee_user_id
        cls.admin_user.is_superuser = True
        cls.admin_user.is_staff = True
        cls.admin_user.set_password("testpass123")
        cls.admin_user.save()

        # Manager employee
        cls.manager_employee = Employee.objects.create(
            employee_first_name="Manager",
            employee_last_name="User",
            email="manager@testcompany.com",
            phone="5550000002",
            gender="male",
        )
        cls.manager_user = cls.manager_employee.employee_user_id
        cls.manager_user.set_password("testpass123")
        cls.manager_user.save()

        # Regular employee
        cls.regular_employee = Employee.objects.create(
            employee_first_name="Regular",
            employee_last_name="Employee",
            email="employee@testcompany.com",
            phone="5550000003",
            gender="female",
        )
        cls.regular_user = cls.regular_employee.employee_user_id
        cls.regular_user.set_password("testpass123")
        cls.regular_user.save()

        # Wire work info
        for emp in [cls.admin_employee, cls.manager_employee, cls.regular_employee]:
            work_info = emp.employee_work_info
            work_info.company_id = cls.company_a
            work_info.department_id = cls.department
            work_info.save()

        # Set reporting manager
        cls.regular_employee.employee_work_info.reporting_manager_id = (
            cls.manager_employee
        )
        cls.regular_employee.employee_work_info.save()

    def setUp(self):
        self.set_request_user(self.admin_user)

    def tearDown(self):
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request

    def set_request_user(self, user):
        """Set _thread_locals.request to simulate an authenticated request."""
        mock_request = _MockRequest(user=user)
        session = SessionStore()
        session.create()
        mock_request.session = session
        _thread_locals.request = mock_request

    def set_company_session(self, company):
        """Set selected_company in session for HorillaCompanyManager filtering."""
        request = getattr(_thread_locals, "request", None)
        if request:
            request.session["selected_company"] = str(company.pk) if company else "all"

    def get_authenticated_client(self, user):
        """Return a Django test Client logged in as the given user."""
        client = Client()
        success = client.login(username=user.username, password="testpass123")
        if not success:
            # Fallback: force login without password check
            client.force_login(user)
        return client

    def get_admin_client(self):
        return self.get_authenticated_client(self.admin_user)

    def get_manager_client(self):
        return self.get_authenticated_client(self.manager_user)

    def get_employee_client(self):
        return self.get_authenticated_client(self.regular_user)

    def htmx_get(self, url, client=None, **kwargs):
        """Send GET request with HTMX header."""
        c = client or self.get_admin_client()
        return c.get(url, HTTP_HX_REQUEST="true", **kwargs)

    def htmx_post(self, url, data=None, client=None, **kwargs):
        """Send POST request with HTMX header."""
        c = client or self.get_admin_client()
        return c.post(url, data=data or {}, HTTP_HX_REQUEST="true", **kwargs)
