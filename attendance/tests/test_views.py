"""
View tests for the attendance module.

Tests authentication enforcement, admin access, clock in/out, overtime views,
attendance request views, and permission enforcement.
"""

from django.contrib.auth.models import Permission
from django.urls import reverse

from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# Authentication Enforcement Tests
# ---------------------------------------------------------------------------
class AttendanceAuthEnforcementTests(HorillaTestCase):
    """Tests that attendance views require authentication."""

    def test_attendance_view_anonymous_redirects(self):
        """Anonymous access to attendance-view should redirect to login."""
        response = self.client.get(reverse("attendance-view"))
        self.assertEqual(response.status_code, 302)

    def test_attendance_activity_view_anonymous_redirects(self):
        """Anonymous access to attendance-activity-view should redirect."""
        response = self.client.get(reverse("attendance-activity-view"))
        self.assertEqual(response.status_code, 302)

    def test_attendance_overtime_view_anonymous_redirects(self):
        """Anonymous access to attendance-overtime-view should redirect."""
        response = self.client.get(reverse("attendance-overtime-view"))
        self.assertEqual(response.status_code, 302)

    def test_clock_in_anonymous_redirects(self):
        """Anonymous access to clock-in should redirect."""
        response = self.client.get(reverse("clock-in"))
        self.assertEqual(response.status_code, 302)

    def test_clock_out_anonymous_redirects(self):
        """Anonymous access to clock-out should redirect."""
        response = self.client.get(reverse("clock-out"))
        self.assertEqual(response.status_code, 302)

    def test_attendance_dashboard_anonymous_redirects(self):
        """Anonymous access to attendance-dashboard should redirect."""
        response = self.client.get(reverse("attendance-dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_late_come_early_out_view_anonymous_redirects(self):
        """Anonymous access to late-come-early-out-view should redirect."""
        response = self.client.get(reverse("late-come-early-out-view"))
        self.assertEqual(response.status_code, 302)

    def test_view_my_attendance_anonymous_redirects(self):
        """Anonymous access to view-my-attendance should redirect."""
        response = self.client.get(reverse("view-my-attendance"))
        self.assertEqual(response.status_code, 302)

    def test_request_attendance_view_anonymous_redirects(self):
        """Anonymous access to request-attendance-view should redirect."""
        response = self.client.get(reverse("request-attendance-view"))
        self.assertEqual(response.status_code, 302)

    def test_work_records_anonymous_redirects(self):
        """Anonymous access to work-records should redirect."""
        response = self.client.get(reverse("work-records"))
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Admin Access Tests (should NOT redirect to login)
# ---------------------------------------------------------------------------
class AttendanceAdminAccessTests(HorillaTestCase):
    """Tests that admin can access attendance views."""

    def test_attendance_view_admin_returns_200(self):
        """Admin should access attendance-view."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_attendance_activity_view_admin(self):
        """Admin should access attendance-activity-view."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-activity-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_attendance_overtime_view_admin(self):
        """Admin should access attendance-overtime-view."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-overtime-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_attendance_dashboard_admin(self):
        """Admin should access attendance-dashboard."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-dashboard"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_late_come_early_out_view_admin(self):
        """Admin should access late-come-early-out-view."""
        client = self.get_admin_client()
        response = client.get(reverse("late-come-early-out-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_view_my_attendance_admin(self):
        """Admin should access view-my-attendance."""
        client = self.get_admin_client()
        response = client.get(reverse("view-my-attendance"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_request_attendance_view_admin(self):
        """Admin should access request-attendance-view."""
        client = self.get_admin_client()
        response = client.get(reverse("request-attendance-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_attendance_settings_view_admin(self):
        """Admin should access attendance-settings-view."""
        client = self.get_admin_client()
        response = client.get(reverse("attendance-settings-view"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)


# ---------------------------------------------------------------------------
# Clock In/Out View Tests
# ---------------------------------------------------------------------------
class ClockInOutViewTests(HorillaTestCase):
    """Tests for clock-in and clock-out views."""

    def test_clock_in_htmx_returns_response(self):
        """HTMX POST to clock-in should return a response (not redirect to login)."""
        response = self.htmx_post(reverse("clock-in"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)

    def test_clock_out_htmx_returns_response(self):
        """HTMX POST to clock-out should return a response."""
        response = self.htmx_post(reverse("clock-out"))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/login", response.url)


# ---------------------------------------------------------------------------
# Permission Enforcement Tests
# ---------------------------------------------------------------------------
class AttendancePermissionTests(HorillaTestCase):
    """Tests that regular employees cannot access manager-only views."""

    def test_attendance_delete_requires_permission(self):
        """Regular employee without delete permission should be denied."""
        client = self.get_employee_client()
        response = client.post(reverse("attendance-delete", kwargs={"obj_id": 9999}))
        # Should redirect (302 to login or forbidden) or return 403
        self.assertIn(response.status_code, [302, 403])

    def test_approve_overtime_requires_permission(self):
        """Regular employee without change perm should be denied approve-overtime."""
        client = self.get_employee_client()
        response = client.post(reverse("approve-overtime", kwargs={"obj_id": 9999}))
        self.assertIn(response.status_code, [302, 403])

    def test_validate_attendance_requires_permission(self):
        """Regular employee should be denied validate-this-attendance."""
        client = self.get_employee_client()
        response = client.post(
            reverse("validate-this-attendance", kwargs={"obj_id": 9999})
        )
        self.assertIn(response.status_code, [302, 403])

    def test_attendance_overtime_delete_requires_permission(self):
        """Regular employee should be denied attendance-overtime-delete."""
        client = self.get_employee_client()
        response = client.post(
            reverse("attendance-overtime-delete", kwargs={"obj_id": 9999})
        )
        self.assertIn(response.status_code, [302, 403])
