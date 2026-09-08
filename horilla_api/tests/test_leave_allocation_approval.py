"""Approving a leave allocation must take a second person who manages you.

GHSA-gc35-jfv9-r3cm reported that the allocation approval endpoint credits
``requested_days`` straight onto the requester's balance behind
``manager_permission_required``, which asks only whether anybody at all reports
to the caller. Any employee who managed one person could file an allocation for
themselves with an arbitrary day count, approve it, and inflate their own leave
balance.

Two separate defects, so two separate guards:

  - the manager test did not name the requester, so a manager of one unrelated
    person passed for every employee in the company
  - nothing required the approver to differ from the requester

Scoping the manager test alone would not have been enough. An employee can be
recorded as their own reporting manager, and in a small company a manager may
legitimately manage everyone -- in both cases a scoped check still passes them
for their own request. The self-approval refusal is therefore independent.

The reject and edit cases are not in the report and were reachable the same way:
rejecting an approved allocation subtracts the days again, and the edit endpoint
accepts ``requested_days``.
"""

from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from employee.models import EmployeeWorkInformation
from horilla.testkit import make_company, make_employee, make_user
from leave.models import AvailableLeave, LeaveAllocationRequest, LeaveType

APPROVE = "/api/v1/leave/allocation-approve/{}/"
REJECT = "/api/v1/leave/allocation-reject/{}/"
DETAIL = "/api/v1/leave/allocation-request/{}/"

REQUESTED_DAYS = 500


def _set_reporting_manager(employee, manager):
    EmployeeWorkInformation.objects.filter(employee_id=employee).update(
        reporting_manager_id=manager
    )


class LeaveAllocationApprovalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = make_company("Alloc Co")

        self.attacker_user = make_user("alloc_attacker", password="secret123")
        self.attacker = make_employee(
            company=company,
            email="alloc_attacker@test.horilla",
            user=self.attacker_user,
            phone="3000001",
        )
        self.victim_user = make_user("alloc_victim", password="secret123")
        self.victim = make_employee(
            company=company,
            email="alloc_victim@test.horilla",
            user=self.victim_user,
            phone="3000002",
        )
        # The attacker manages someone -- just not the victim, and not
        # themselves. This single row is what the old check accepted.
        self.subordinate = make_employee(
            company=company,
            email="alloc_subordinate@test.horilla",
            phone="3000003",
        )
        _set_reporting_manager(self.subordinate, self.attacker)

        self.leave_type = LeaveType.objects.create(
            name="Annual", payment="paid", total_days=10, company_id=company
        )

    def _request(self, employee):
        return LeaveAllocationRequest.objects.create(
            employee_id=employee,
            leave_type_id=self.leave_type,
            requested_days=REQUESTED_DAYS,
            description="allocation",
            status="requested",
        )

    def _auth(self, user):
        self.client.force_authenticate(user=type(user).objects.get(pk=user.pk))

    def _balance(self, employee):
        row = AvailableLeave.objects.filter(
            employee_id=employee, leave_type_id=self.leave_type
        ).first()
        return row.available_days if row else 0

    def test_manager_cannot_approve_their_own_allocation(self):
        """The reported attack: self-approval inflating your own balance."""
        own = self._request(self.attacker)
        self._auth(self.attacker_user)
        response = self.client.put(APPROVE.format(own.pk))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            LeaveAllocationRequest.objects.get(pk=own.pk).status, "requested"
        )
        self.assertEqual(self._balance(self.attacker), 0)

    def test_manager_of_someone_else_cannot_approve_a_strangers_allocation(self):
        """The broader variant: approving for an employee you do not manage."""
        theirs = self._request(self.victim)
        self._auth(self.attacker_user)
        response = self.client.put(APPROVE.format(theirs.pk))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._balance(self.victim), 0)

    def test_manager_of_someone_else_cannot_reject_a_strangers_allocation(self):
        """Not in the report: rejecting an approved one subtracts the days."""
        theirs = self._request(self.victim)
        self._auth(self.attacker_user)
        response = self.client.put(REJECT.format(theirs.pk))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            LeaveAllocationRequest.objects.get(pk=theirs.pk).status, "requested"
        )

    def test_manager_of_someone_else_cannot_read_or_edit_a_strangers_allocation(self):
        """Not in the report: the edit endpoint accepts requested_days."""
        theirs = self._request(self.victim)
        self._auth(self.attacker_user)
        self.assertEqual(self.client.get(DETAIL.format(theirs.pk)).status_code, 403)
        response = self.client.put(
            DETAIL.format(theirs.pk),
            {
                "employee_id": self.victim.id,
                "leave_type_id": self.leave_type.id,
                "requested_days": 9999,
                "description": "tampered",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            LeaveAllocationRequest.objects.get(pk=theirs.pk).requested_days,
            REQUESTED_DAYS,
        )

    def test_the_requesters_own_manager_can_approve(self):
        """Scoping must still admit the manager it is meant to admit."""
        _set_reporting_manager(self.victim, self.attacker)
        theirs = self._request(self.victim)
        self._auth(self.attacker_user)
        response = self.client.put(APPROVE.format(theirs.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._balance(self.victim), REQUESTED_DAYS)

    def test_a_permission_holder_can_approve(self):
        theirs = self._request(self.victim)
        self.attacker_user.user_permissions.add(
            Permission.objects.get(codename="change_leaveallocationrequest")
        )
        self._auth(self.attacker_user)
        response = self.client.put(APPROVE.format(theirs.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._balance(self.victim), REQUESTED_DAYS)

    def test_a_permission_holder_still_cannot_approve_their_own(self):
        """
        The self-approval refusal is not a side effect of the manager check --
        holding the permission does not buy you your own approval either.
        """
        own = self._request(self.attacker)
        self.attacker_user.user_permissions.add(
            Permission.objects.get(codename="change_leaveallocationrequest")
        )
        self._auth(self.attacker_user)
        response = self.client.put(APPROVE.format(own.pk))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._balance(self.attacker), 0)

    def test_the_owner_can_still_read_their_own_request(self):
        own = self._request(self.victim)
        self._auth(self.victim_user)
        self.assertEqual(self.client.get(DETAIL.format(own.pk)).status_code, 200)
