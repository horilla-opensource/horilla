"""
The generic history view and the payroll dashboard data endpoints checked only
that the user was logged in.

- history (generic-history / history-revert): any employee could read any
  record's change history by ?model=app.Model, across companies, and revert
  any snapshot -- e.g. undo a deduction from a colleague's leave balance.
- payroll dashboard charts/details/export returned every employee's net pay.

Each denial is paired with the legitimate user doing the same thing, so a fix
that refuses everyone fails.
"""

from datetime import date

from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from employee.models import EmployeeWorkInformation
from horilla.horilla_middlewares import set_selected_company
from horilla.testkit import make_company, make_employee, make_user
from horilla.testkit.factories import make_available_leave, make_leave_type

HX = {"HTTP_HX_REQUEST": "true", "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class HistoryAndPayrollDashboardAuthzTests(TestCase):
    def setUp(self):
        set_selected_company(None)
        company = make_company("Authz Co")

        def person(name):
            user = make_user(name, password="secret123")
            emp = make_employee(
                company=company, email=f"{name}@test.horilla", user=user
            )
            return user, emp

        self.owner_user, self.owner = person("hist_owner")
        self.manager_user, self.manager = person("hist_manager")
        self.stranger_user, self.stranger = person("hist_stranger")
        self.hr_user, self.hr = person("hist_hr")
        EmployeeWorkInformation.objects.filter(employee_id=self.owner).update(
            reporting_manager_id=self.manager
        )
        self.hr_user.user_permissions.add(
            Permission.objects.get(codename="change_availableleave"),
            Permission.objects.get(codename="view_payslip"),
        )

        self.balance = make_available_leave(
            employee=self.owner, leave_type=make_leave_type("Authz Leave"), available=10
        )
        self.old_snapshot = self.balance.history.order_by("history_date").first()
        self.balance.available_days = 7  # a deduction, recorded in history
        self.balance.save()

    def tearDown(self):
        set_selected_company(None)

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def history_url(self):
        return (
            reverse("generic-history", kwargs={"pk": self.balance.pk})
            + "?model=leave.availableleave"
        )

    def revert_url(self, pk=None):
        return (
            reverse(
                "history-revert",
                kwargs={
                    "pk": pk or self.balance.pk,
                    "history_id": self.old_snapshot.history_id,
                },
            )
            + "?model=leave.availableleave"
        )

    def current_balance(self):
        return type(self.balance).objects.get(pk=self.balance.pk).available_days

    # -- viewing history ---------------------------------------------------

    def test_stranger_cannot_view_history(self):
        response = self.client_for(self.stranger_user).get(self.history_url(), **HX)
        self.assertNotContains(response, "genericActivityHistory")

    def test_owner_and_manager_can_view_history(self):
        for user in (self.owner_user, self.manager_user):
            response = self.client_for(user).get(self.history_url(), **HX)
            self.assertContains(response, "genericActivityHistory")

    # -- reverting ---------------------------------------------------------

    def test_stranger_cannot_revert(self):
        self.client_for(self.stranger_user).post(self.revert_url(), **HX)
        self.assertEqual(self.current_balance(), 7)

    def test_owner_cannot_revert_their_own_deduction(self):
        """Seeing a record's history is not permission to rewrite it."""
        self.client_for(self.owner_user).post(self.revert_url(), **HX)
        self.assertEqual(self.current_balance(), 7)

    def test_change_permission_holder_can_revert(self):
        self.client_for(self.hr_user).post(self.revert_url(), **HX)
        self.assertEqual(self.current_balance(), 10)

    def test_snapshot_must_belong_to_the_record_in_the_url(self):
        other = make_available_leave(
            employee=self.stranger,
            leave_type=make_leave_type("Other Leave"),
            available=3,
        )
        self.client_for(self.hr_user).post(self.revert_url(pk=other.pk), **HX)
        self.assertEqual(self.current_balance(), 7)
        self.assertEqual(type(other).objects.get(pk=other.pk).available_days, 3)

    # -- payroll dashboard data ------------------------------------------------

    def make_payslip(self):
        from payroll.models.models import Payslip

        Payslip(
            employee_id=self.owner,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            net_pay=98765.43,
            gross_pay=100000,
            deduction=1234.57,
            status="paid",
            pay_head_data={},
        ).save()

    def test_payroll_dashboard_data_needs_view_payslip(self):
        self.make_payslip()
        for name in (
            "dashboard-employee-chart",
            "dashboard-payslip-details",
            "dashboard-department-chart",
        ):
            url = reverse(name) + "?period=2026-09"
            denied = self.client_for(self.stranger_user).get(url, **HX)
            self.assertNotIn(b"98765.43", denied.content, name)
            allowed = self.client_for(self.hr_user).get(url, **HX)
            self.assertEqual(allowed.status_code, 200, name)

    def test_payroll_dashboard_export_needs_view_payslip(self):
        self.make_payslip()
        response = self.client_for(self.stranger_user).post(
            reverse("dashboard-export"),
            {"start_date": "2026-09-01", "end_date": "2026-09-30"},
        )
        self.assertNotIn("spreadsheet", response.get("Content-Type", ""))
