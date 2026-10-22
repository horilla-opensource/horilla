"""A ticket is visible to its owner, their manager, an assignee and permission holders.

`ticket_individual_view` and `ticket_detail` apply the same rule.
"""

from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from helpdesk.models import Ticket, TicketType
from horilla.testkit import make_company, make_employee, make_user


class TicketViewAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Helpdesk Co")
        cls.owner_user = make_user("tk_owner", password="secret123")
        cls.owner = make_employee(
            company=company, email="tk_owner@test.horilla", user=cls.owner_user
        )
        cls.other_user = make_user("tk_other", password="secret123")
        cls.other = make_employee(
            company=company, email="tk_other@test.horilla", user=cls.other_user
        )
        cls.manager_user = make_user("tk_manager", password="secret123")
        cls.manager = make_employee(
            company=company, email="tk_manager@test.horilla", user=cls.manager_user
        )
        work_info = cls.owner.employee_work_info
        work_info.reporting_manager_id = cls.manager
        work_info.save()
        ticket_type = TicketType.objects.create(
            title="Payroll query", type="complaint", prefix="PAY"
        )
        cls.ticket = Ticket.objects.create(
            title="Salary correction",
            employee_id=cls.owner,
            ticket_type=ticket_type,
            description="Confidential payroll complaint",
            priority="high",
            assigning_type="individual",
            raised_on=str(cls.manager.pk),
        )

    def _get(self, user, route="ticket-individual-view"):
        client = Client()
        client.force_login(type(user).objects.get(pk=user.pk))
        return client.get(reverse(route, kwargs={"ticket_id": self.ticket.pk}))

    @staticmethod
    def _denied(response):
        """A refused request is sent away, and nothing of the ticket comes back."""
        return (
            response.status_code == 302 and b"Salary correction" not in response.content
        )

    def _allowed(self, response):
        return (
            response.status_code == 200
            and not self._denied(response)
            and b"Salary correction" in response.content
        )

    def test_unrelated_employee_cannot_open_the_individual_view(self):
        response = self._get(self.other_user)
        self.assertTrue(
            self._denied(response), "the ticket was served to an unrelated employee"
        )

    def test_the_sibling_view_still_denies_too(self):
        """The check both views now share."""
        self.assertTrue(self._denied(self._get(self.other_user, "ticket-detail")))

    def test_owner_still_sees_their_ticket(self):
        """A fix that denies everyone would pass the tests above."""
        self.assertTrue(self._allowed(self._get(self.owner_user)))

    def test_reporting_manager_still_sees_the_ticket(self):
        self.assertTrue(self._allowed(self._get(self.manager_user)))

    def test_permission_holder_still_sees_the_ticket(self):
        self.other_user.user_permissions.add(
            Permission.objects.get(codename="view_ticket")
        )
        self.assertTrue(self._allowed(self._get(self.other_user)))

    def test_assignee_still_sees_the_ticket(self):
        self.ticket.assigned_to.add(self.other)
        self.assertTrue(self._allowed(self._get(self.other_user)))
