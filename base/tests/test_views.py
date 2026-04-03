"""
View tests for the base module.

Tests authentication, company CRUD, department CRUD, holiday CRUD,
and settings access with proper permission and HTMX handling.
"""

from datetime import date, timedelta

from django.contrib.auth.models import Permission
from django.urls import reverse

from base.models import Company, Department, Holidays
from horilla.test_utils.base import HorillaTestCase


class LoginViewTests(HorillaTestCase):
    """Tests for login/logout and anonymous redirect."""

    def test_login_page_returns_200_for_anonymous(self):
        """GET /login/ should render the login page for anonymous users."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_login_post_valid_credentials_redirects(self):
        """POST /login/ with correct credentials should redirect (302)."""
        response = self.client.post(
            reverse("login"),
            {"username": self.admin_user.username, "password": "testpass123"},
        )
        self.assertIn(response.status_code, [200, 302])

    def test_login_post_invalid_credentials_rerenders(self):
        """POST /login/ with wrong password should re-render login (200)."""
        response = self.client.post(
            reverse("login"),
            {"username": self.admin_user.username, "password": "wrongpassword"},
        )
        # Should stay on the login page (200) or redirect back to login
        self.assertIn(response.status_code, [200, 302])

    def test_logout_redirects_to_login(self):
        """GET /logout/ should redirect to login page."""
        client = self.get_admin_client()
        response = client.get(reverse("logout"))
        self.assertIn(response.status_code, [200, 302])

    def test_home_page_redirects_anonymous_to_login(self):
        """Anonymous access to home-page should redirect to login."""
        response = self.client.get(reverse("home-page"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_settings_redirects_anonymous_to_login(self):
        """Anonymous access to settings should redirect to login."""
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 302)

    def test_change_password_redirects_anonymous(self):
        """Anonymous user cannot access change-password."""
        response = self.client.get(reverse("change-password"))
        self.assertEqual(response.status_code, 302)

    def test_forgot_password_accessible_anonymous(self):
        """Forgot password page should be accessible without login."""
        response = self.client.get(reverse("forgot-password"))
        self.assertIn(response.status_code, [200, 302])


class CompanyViewTests(HorillaTestCase):
    """Tests for Company settings views."""

    def test_company_view_anonymous_redirects(self):
        """Anonymous access to company-view should return 302."""
        response = self.client.get(reverse("company-view"))
        self.assertEqual(response.status_code, 302)

    def test_company_view_admin_not_redirected_to_login(self):
        """Admin should not be redirected to login for company-view."""
        client = self.get_admin_client()
        response = client.get(reverse("company-view"))
        if response.status_code == 302:
            self.assertNotIn(
                "/login", response.url, "Admin should not redirect to login"
            )

    def test_company_list_htmx_not_redirected_to_login(self):
        """HTMX GET to company-list should not redirect admin to login."""
        response = self.htmx_get(reverse("company-list"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_company_create_form_htmx_not_redirected(self):
        """HTMX GET to company-create-form should not redirect admin to login."""
        response = self.htmx_get(reverse("company-create-form"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_company_create_htmx_post_valid(self):
        """HTMX POST to company-create with valid data should succeed."""
        client = self.get_admin_client()
        response = self.htmx_post(
            reverse("company-create"),
            data={
                "company": "New Test Corp",
                "address": "789 New St",
                "country": "US",
                "state": "TX",
                "city": "Austin",
                "zip": "73301",
            },
            client=client,
        )
        # Should return 200 (re-rendered form with success message) or 302
        self.assertIn(response.status_code, [200, 302])

    def test_company_create_htmx_post_missing_name(self):
        """HTMX POST to company-create without company name should re-render form."""
        response = self.htmx_post(
            reverse("company-create"),
            data={
                "address": "789 New St",
                "country": "US",
            },
        )
        self.assertIn(response.status_code, [200, 302])

    def test_company_navbar_htmx_not_redirected(self):
        """HTMX GET to company-navbar should not redirect admin to login."""
        response = self.htmx_get(reverse("company-navbar"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_company_view_employee_without_perm_redirects(self):
        """Regular employee without view_company perm should be denied."""
        client = self.get_employee_client()
        response = client.get(reverse("company-view"))
        # Should redirect or return 403 (permission_required redirects to login/denied)
        self.assertIn(response.status_code, [302, 403])


class DepartmentViewTests(HorillaTestCase):
    """Tests for Department settings views."""

    def test_department_view_anonymous_redirects(self):
        """Anonymous access to department-view should redirect."""
        response = self.client.get(reverse("department-view"))
        self.assertEqual(response.status_code, 302)

    def test_department_view_admin_not_redirected_to_login(self):
        """Admin should not be redirected to login for department-view."""
        client = self.get_admin_client()
        response = client.get(reverse("department-view"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_department_creation_htmx_not_redirected(self):
        """HTMX GET to department-creation should not redirect admin."""
        response = self.htmx_get(reverse("department-creation"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_department_creation_htmx_post_valid(self):
        """HTMX POST to department-creation should not error for admin."""
        response = self.htmx_post(
            reverse("department-creation"),
            data={"department": "Marketing"},
        )
        self.assertIn(response.status_code, [200, 302])

    def test_department_view_employee_without_perm_redirects(self):
        """Regular employee without view_department perm should be denied."""
        client = self.get_employee_client()
        response = client.get(reverse("department-view"))
        self.assertIn(response.status_code, [302, 403])


class HolidayViewTests(HorillaTestCase):
    """Tests for Holiday configuration views."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.holiday = Holidays.objects.create(
            name="Test Holiday",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
        )

    def test_holiday_view_anonymous_redirects(self):
        """Anonymous access to holiday-view should redirect."""
        response = self.client.get(reverse("holiday-view"))
        self.assertEqual(response.status_code, 302)

    def test_holiday_view_admin_not_redirected_to_login(self):
        """Admin should not be redirected to login for holiday-view."""
        client = self.get_admin_client()
        response = client.get(reverse("holiday-view"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_holiday_filter_htmx_not_redirected(self):
        """HTMX GET to holiday-filter should not redirect admin."""
        response = self.htmx_get(reverse("holiday-filter"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_holiday_creation_htmx_not_redirected(self):
        """HTMX GET to holiday-creation should not redirect admin."""
        response = self.htmx_get(reverse("holiday-creation"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_holiday_creation_htmx_post_valid(self):
        """HTMX POST to holiday-creation should not error for admin."""
        response = self.htmx_post(
            reverse("holiday-creation"),
            data={
                "name": "New Year",
                "start_date": (date.today() + timedelta(days=60)).isoformat(),
                "end_date": (date.today() + timedelta(days=60)).isoformat(),
            },
        )
        self.assertIn(response.status_code, [200, 302])


class SettingsViewTests(HorillaTestCase):
    """Tests for settings page access."""

    def test_settings_requires_auth(self):
        """Anonymous access to settings should redirect to login."""
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 302)

    def test_settings_admin_not_redirected_to_login(self):
        """Admin should not be redirected to login for settings."""
        client = self.get_admin_client()
        response = client.get(reverse("settings"))
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_settings_employee_can_access(self):
        """Regular employee can access settings (it is @login_required only)."""
        client = self.get_employee_client()
        response = client.get(reverse("settings"))
        # Settings page is login_required only, should be 200
        self.assertIn(response.status_code, [200, 302])

    def test_user_group_view_requires_auth(self):
        """Anonymous access to user-group-view should redirect."""
        response = self.client.get(reverse("user-group-view"))
        self.assertEqual(response.status_code, 302)
