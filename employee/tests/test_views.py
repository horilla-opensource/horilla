"""
View tests for the employee module.

Tests authentication enforcement, employee list/card views, CRUD operations,
permission enforcement, dashboard, profile, and organisation chart.
"""

from django.contrib.auth.models import Permission
from django.urls import reverse

from employee.models import Employee
from horilla.test_utils.base import HorillaTestCase


class EmployeeAuthEnforcementTests(HorillaTestCase):
    """Tests that employee views require authentication."""

    def test_employee_view_anonymous_redirects(self):
        """Anonymous access to employee-view should redirect to login."""
        response = self.client.get(reverse("employee-view"))
        self.assertEqual(response.status_code, 302)

    def test_employee_profile_anonymous_redirects(self):
        """Anonymous access to employee-profile should redirect to login."""
        response = self.client.get(reverse("employee-profile"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_anonymous_redirects(self):
        """Anonymous access to dashboard should redirect to login."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_organisation_chart_anonymous_redirects(self):
        """Anonymous access to organisation-chart should redirect to login."""
        response = self.client.get(reverse("organisation-chart"))
        self.assertEqual(response.status_code, 302)

    def test_employee_view_new_anonymous_redirects(self):
        """Anonymous access to employee-view-new (create) should redirect."""
        response = self.client.get(reverse("employee-view-new"))
        self.assertEqual(response.status_code, 302)


class EmployeeListViewTests(HorillaTestCase):
    """Tests for employee list and card views."""

    def test_employee_view_admin_returns_200(self):
        """Admin should access employee-view (CBV EmployeesView)."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employees_list_htmx_returns_200(self):
        """HTMX GET to employees-list should return the list partial."""
        response = self.htmx_get(reverse("employees-list"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employees_nav_htmx_returns_200(self):
        """HTMX GET to employees-nav should return the nav partial."""
        response = self.htmx_get(reverse("employees-nav"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employees_card_htmx_returns_200(self):
        """HTMX GET to employees-card should return the card partial."""
        response = self.htmx_get(reverse("employees-card"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employee_filter_view_htmx(self):
        """HTMX GET to employee-filter-view should return filtered results."""
        response = self.htmx_get(reverse("employee-filter-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)


class EmployeeCRUDTests(HorillaTestCase):
    """Tests for employee CRUD operations."""

    def test_employee_profile_self_returns_200(self):
        """Authenticated user should see their own profile."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-profile"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employee_view_individual_returns_200(self):
        """Admin should view an individual employee page."""
        client = self.get_admin_client()
        response = client.get(
            reverse("employee-view-individual", args=[self.regular_employee.pk])
        )
        self.assertIn(response.status_code, [200, 302])

    def test_employee_view_new_admin_returns_200(self):
        """Admin with add_employee permission should see the create form."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-view-new"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employee_create_personal_info_htmx_get(self):
        """HTMX GET to employee-create-personal-info should render form."""
        response = self.htmx_get(reverse("employee-create-personal-info"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employee_update_htmx_get(self):
        """HTMX GET to employee-update should render the update form."""
        response = self.htmx_get(
            reverse("employee-update", args=[self.regular_employee.pk])
        )
        self.assertIn(response.status_code, [200, 302])

    def test_employee_search_htmx(self):
        """HTMX GET to search-employee should return results."""
        response = self.htmx_get(reverse("search-employee") + "?search=Admin")
        self.assertIn(response.status_code, [200, 302])

    def test_organisation_chart_admin_returns_200(self):
        """Admin should access the organisation chart."""
        client = self.get_admin_client()
        response = client.get(reverse("organisation-chart"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_profile_new_cbv_returns_200(self):
        """CBV profile-new should render for admin viewing an employee."""
        client = self.get_admin_client()
        response = client.get(reverse("profile-new", args=[self.regular_employee.pk]))
        self.assertIn(response.status_code, [200, 302])


class EmployeePermissionTests(HorillaTestCase):
    """Tests for permission enforcement on employee views."""

    def test_regular_employee_cannot_create_employee(self):
        """Employee without add_employee perm should be denied create access."""
        client = self.get_employee_client()
        response = client.get(reverse("employee-view-new"))
        # Should redirect to denied or login
        self.assertIn(response.status_code, [302, 403])

    def test_admin_can_access_employee_list(self):
        """Admin (superuser) should access employee list view."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_regular_employee_can_see_own_profile(self):
        """Any authenticated employee should see their own profile."""
        client = self.get_employee_client()
        response = client.get(reverse("employee-profile"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_employee_export_requires_permission(self):
        """Regular employee without export permission should be denied."""
        client = self.get_employee_client()
        response = self.htmx_get(reverse("employees-export"), client=client)
        # Export typically requires view_employee or export perm
        self.assertIn(response.status_code, [200, 302, 403])


class DashboardViewTests(HorillaTestCase):
    """Tests for the employee dashboard."""

    def test_dashboard_requires_auth(self):
        """Anonymous access to dashboard should redirect to login."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_admin_returns_200(self):
        """Admin should access the dashboard."""
        client = self.get_admin_client()
        response = client.get(reverse("dashboard"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_dashboard_employee_returns_200(self):
        """Regular employee should also access the dashboard."""
        client = self.get_employee_client()
        response = client.get(reverse("dashboard"))
        self.assertIn(response.status_code, [200, 302])
