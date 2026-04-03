"""
Permission matrix tests for Horilla HRMS.

Systematically verifies that every protected view:
  - Redirects anonymous users to login (302 with /login in url)
  - Denies regular employees without permissions (302/403)
  - Allows admin users (200 or non-login-redirect 302)

Covers: base, employee, leave, payroll, recruitment, attendance modules.
"""

from django.contrib.auth.models import Permission
from django.urls import reverse

from horilla.test_utils.base import HorillaTestCase


def _is_login_redirect(response):
    """Return True if the response is a 302 redirect to the login page."""
    return response.status_code == 302 and (
        "/login" in response.url or "/accounts/login" in response.url
    )


def _is_access_denied(response):
    """
    Return True if the response denies access.

    Horilla's handle_no_permission() redirects to HTTP_REFERER (defaults to "/")
    rather than to /login/ or /denied/. So we simply verify the view did NOT
    return a successful 200 response.
    """
    return response.status_code != 200


def _is_accessible(response):
    """Return True if the response is accessible (200 or non-login-redirect)."""
    if response.status_code == 200:
        return True
    if response.status_code == 302 and "/login" not in response.url:
        return True
    return False


# ---------------------------------------------------------------------------
# Base module
# ---------------------------------------------------------------------------


class BaseViewPermissionMatrixTests(HorillaTestCase):
    """Permission matrix for base module views."""

    # --- company-view ---

    def test_company_view_anonymous_redirects_to_login(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("company-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_company_view_employee_without_perm_denied(self):
        """Employee without view_company perm → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("company-view"))
        self.assertTrue(_is_access_denied(response))

    def test_company_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("company-view"))
        self.assertTrue(_is_accessible(response))

    # --- department-view ---

    def test_department_view_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("department-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_department_view_employee_without_perm_denied(self):
        """Employee without view_department → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("department-view"))
        self.assertTrue(_is_access_denied(response))

    def test_department_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("department-view"))
        self.assertTrue(_is_accessible(response))

    # --- holiday-view ---

    def test_holiday_view_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("holiday-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_holiday_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("holiday-view"))
        self.assertTrue(_is_accessible(response))

    # --- settings ---

    def test_settings_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("settings"))
        self.assertTrue(_is_login_redirect(response))

    def test_settings_authenticated_accessible(self):
        """Any authenticated user can reach settings (login_required only)."""
        client = self.get_employee_client()
        response = client.get(reverse("settings"))
        self.assertTrue(_is_accessible(response))


# ---------------------------------------------------------------------------
# Employee module
# ---------------------------------------------------------------------------


class EmployeeViewPermissionMatrixTests(HorillaTestCase):
    """Permission matrix for employee module views."""

    def test_employee_list_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("employee-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_employee_list_employee_without_perm_denied(self):
        """Regular employee without view_employee → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("employee-view"))
        self.assertTrue(_is_access_denied(response))

    def test_employee_list_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-view"))
        self.assertTrue(_is_accessible(response))

    def test_employee_new_view_anonymous_redirects(self):
        """Anonymous → redirect to login for new employee view."""
        response = self.client.get(reverse("employee-view-new"))
        self.assertTrue(_is_login_redirect(response))

    def test_employee_new_view_admin_accessible(self):
        """Admin → accessible for new employee view."""
        client = self.get_admin_client()
        response = client.get(reverse("employee-view-new"))
        self.assertTrue(_is_accessible(response))

    def test_employee_manager_with_perm_accessible(self):
        """Manager with view_employee perm → accessible."""
        perm = Permission.objects.get(codename="view_employee")
        self.manager_user.user_permissions.add(perm)
        client = self.get_manager_client()
        response = client.get(reverse("employee-view"))
        self.assertTrue(_is_accessible(response))


# ---------------------------------------------------------------------------
# Leave module
# ---------------------------------------------------------------------------


class LeaveViewPermissionMatrixTests(HorillaTestCase):
    """Permission matrix for leave module views."""

    def test_leave_type_view_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("type-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_leave_type_view_employee_without_perm_denied(self):
        """Regular employee without view_leavetype → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("type-view"))
        self.assertTrue(_is_access_denied(response))

    def test_leave_type_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("type-view"))
        self.assertTrue(_is_accessible(response))

    def test_leave_request_view_anonymous_redirects(self):
        """Anonymous → redirect to login for leave requests."""
        response = self.client.get(reverse("request-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_leave_request_view_admin_accessible(self):
        """Admin → accessible for leave requests view."""
        client = self.get_admin_client()
        response = client.get(reverse("request-view"))
        self.assertTrue(_is_accessible(response))

    def test_my_leave_request_view_anonymous_redirects(self):
        """Anonymous → redirect to login for user's own requests."""
        response = self.client.get(reverse("user-request-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_my_leave_request_view_employee_accessible(self):
        """Regular employee → can access their own leave requests."""
        client = self.get_employee_client()
        response = client.get(reverse("user-request-view"))
        self.assertTrue(_is_accessible(response))


# ---------------------------------------------------------------------------
# Recruitment module
# ---------------------------------------------------------------------------


class RecruitmentViewPermissionMatrixTests(HorillaTestCase):
    """Permission matrix for recruitment module views."""

    def test_recruitment_view_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("recruitment-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_recruitment_view_employee_without_perm_denied(self):
        """Regular employee without recruitment perm → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("recruitment-view"))
        self.assertTrue(_is_access_denied(response))

    def test_recruitment_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("recruitment-view"))
        self.assertTrue(_is_accessible(response))


# ---------------------------------------------------------------------------
# Attendance module
# ---------------------------------------------------------------------------


class AttendanceViewPermissionMatrixTests(HorillaTestCase):
    """Permission matrix for attendance module views."""

    def test_attendance_view_anonymous_redirects(self):
        """Anonymous → redirect to login."""
        response = self.client.get(reverse("attendance-view"))
        self.assertTrue(_is_login_redirect(response))

    def test_attendance_view_employee_without_perm_denied(self):
        """Regular employee without view_attendance → denied."""
        client = self.get_employee_client()
        response = client.get(reverse("attendance-view"))
        self.assertTrue(_is_access_denied(response))

    def test_attendance_view_admin_accessible(self):
        """Admin → accessible."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-view"))
        self.assertTrue(_is_accessible(response))


# ---------------------------------------------------------------------------
# Cross-module: Login redirect consistency
# ---------------------------------------------------------------------------


class LoginRedirectConsistencyTests(HorillaTestCase):
    """
    All protected views must redirect anonymous users to login.
    This test batch validates the login redirect contract across modules.
    """

    PROTECTED_URLS = [
        "company-view",
        "department-view",
        "holiday-view",
        "settings",
        "employee-view",
        "employee-view-new",
        "type-view",
        "request-view",
        "user-request-view",
        "recruitment-view",
        "attendance-view",
        "home-page",
    ]

    def test_all_protected_urls_redirect_anonymous(self):
        """Every URL in PROTECTED_URLS must return 302 for anonymous users."""
        for url_name in self.PROTECTED_URLS:
            with self.subTest(url=url_name):
                try:
                    response = self.client.get(reverse(url_name))
                    self.assertEqual(
                        response.status_code,
                        302,
                        f"{url_name} should redirect anonymous users (got {response.status_code})",
                    )
                except Exception as e:
                    self.fail(f"URL '{url_name}' raised exception: {e}")
