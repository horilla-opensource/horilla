"""GHSA-97wm-28fj-g4pj, write side: the manager check must name its target.

Finding 1 of that advisory was fixed on the read side only -- commit 9972a699
scoped the detail-by-ID `GET` handlers and left every write handler on
`manager_permission_required`, which asks whether anybody at all reports to the
caller and never which employee the record belongs to. Confirmed live against
released 2.1.2, as an employee managing one unrelated person and holding no
leave permission:

    PUT /api/v1/leave/approve/<pk>/
      own request       -> HTTP 200, status 'approved'
      another's request -> HTTP 200, status 'approved'

The bulk endpoint takes its ids from the body rather than the URL, so it needs
the same rule applied per record; scoping only the by-pk route would leave the
bulk route as its unscoped twin.

As in the other scoping tests, the allow cases carry as much weight as the deny
ones -- the victim's real manager, and the approvers a multiple-approval
condition nominates, must all still get through.
"""

import datetime

from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from employee.models import EmployeeWorkInformation
from horilla.testkit import make_company, make_employee, make_user
from leave.models import (
    AvailableLeave,
    LeaveRequest,
    LeaveRequestConditionApproval,
    LeaveType,
)

APPROVE = "/api/v1/leave/approve/{}/"
REJECT = "/api/v1/leave/reject/{}/"
BULK = "/api/v1/leave/request-bulk-action/"


def _manage(employee, manager):
    EmployeeWorkInformation.objects.filter(employee_id=employee).update(
        reporting_manager_id=manager
    )


class LeaveWriteScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = make_company("Leave Scope Co")

        self.attacker_user = make_user("lv_attacker", password="secret123")
        self.attacker = make_employee(
            company=company,
            email="lv_attacker@test.horilla",
            user=self.attacker_user,
            phone="2000001",
        )
        self.victim_user = make_user("lv_victim", password="secret123")
        self.victim = make_employee(
            company=company,
            email="lv_victim@test.horilla",
            user=self.victim_user,
            phone="2000002",
        )
        # The attacker manages somebody -- just not the victim.
        self.subordinate = make_employee(
            company=company, email="lv_sub@test.horilla", phone="2000003"
        )
        _manage(self.subordinate, self.attacker)

        self.boss_user = make_user("lv_boss", password="secret123")
        self.boss = make_employee(
            company=company,
            email="lv_boss@test.horilla",
            user=self.boss_user,
            phone="2000004",
        )
        _manage(self.victim, self.boss)

        self.leave_type = LeaveType.objects.create(
            name="Annual", payment="paid", total_days=10, company_id=company
        )
        for employee in (self.attacker, self.victim, self.subordinate):
            AvailableLeave.objects.get_or_create(
                employee_id=employee,
                leave_type_id=self.leave_type,
                defaults={"available_days": 10},
            )

    def _request_for(self, employee):
        return LeaveRequest.objects.create(
            employee_id=employee,
            leave_type_id=self.leave_type,
            start_date=datetime.date(2026, 8, 3),
            end_date=datetime.date(2026, 8, 4),
            requested_days=2,
            description="test",
            status="requested",
        )

    def _as(self, user):
        self.client.force_authenticate(user=user)

    def _status_of(self, leave_request):
        return LeaveRequest.objects.get(pk=leave_request.pk).status

    # --- deny -------------------------------------------------------------

    def test_cannot_approve_own_request(self):
        own = self._request_for(self.attacker)
        self._as(self.attacker_user)
        response = self.client.put(
            APPROVE.format(own.pk), {"available_leave": 1}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._status_of(own), "requested")

    def test_cannot_approve_a_stranger_request(self):
        theirs = self._request_for(self.victim)
        self._as(self.attacker_user)
        response = self.client.put(
            APPROVE.format(theirs.pk), {"available_leave": 1}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._status_of(theirs), "requested")

    def test_cannot_reject_a_stranger_request(self):
        theirs = self._request_for(self.victim)
        self._as(self.attacker_user)
        response = self.client.put(REJECT.format(theirs.pk), {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._status_of(theirs), "requested")

    def test_cannot_read_or_delete_a_stranger_request(self):
        theirs = self._request_for(self.victim)
        self._as(self.attacker_user)
        self.assertEqual(
            self.client.get(f"/api/v1/leave/request/{theirs.pk}/").status_code, 403
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/leave/request/{theirs.pk}/").status_code, 403
        )
        self.assertTrue(LeaveRequest.objects.filter(pk=theirs.pk).exists())

    def test_bulk_approve_skips_records_out_of_scope(self):
        """The bulk route must not be the unscoped version of the single one."""
        own = self._request_for(self.attacker)
        theirs = self._request_for(self.victim)
        mine_to_approve = self._request_for(self.subordinate)
        self._as(self.attacker_user)

        self.client.put(
            BULK,
            {"leave_request_id": [own.pk, theirs.pk, mine_to_approve.pk]},
            format="multipart",
        )

        self.assertEqual(self._status_of(own), "requested", "self-approved in bulk")
        self.assertEqual(self._status_of(theirs), "requested", "stranger approved")
        self.assertEqual(
            self._status_of(mine_to_approve),
            "approved",
            "a real subordinate's request should still go through",
        )

    # --- allow ------------------------------------------------------------

    def test_the_real_manager_can_approve(self):
        theirs = self._request_for(self.victim)
        self._as(self.boss_user)
        response = self.client.put(
            APPROVE.format(theirs.pk), {"available_leave": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self._status_of(theirs), "approved")

    def test_a_permission_holder_can_approve(self):
        theirs = self._request_for(self.victim)
        self.attacker_user.user_permissions.add(
            Permission.objects.get(codename="change_leaverequest")
        )
        self._as(type(self.attacker_user).objects.get(pk=self.attacker_user.pk))
        response = self.client.put(
            APPROVE.format(theirs.pk), {"available_leave": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_the_owner_can_still_read_and_delete_their_own_request(self):
        own = self._request_for(self.victim)
        self._as(self.victim_user)
        self.assertEqual(
            self.client.get(f"/api/v1/leave/request/{own.pk}/").status_code, 200
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/leave/request/{own.pk}/").status_code, 200
        )

    def test_a_nominated_condition_approver_is_not_locked_out(self):
        """
        A multiple-approval condition names its own approvers, who are often
        neither the reporting manager nor permission holders. Scoping the
        manager test would shut them out of the chain they exist to serve.
        """
        theirs = self._request_for(self.victim)
        LeaveRequestConditionApproval.objects.create(
            manager_id=self.attacker, sequence=1, leave_request_id=theirs
        )
        self._as(self.attacker_user)
        response = self.client.put(
            APPROVE.format(theirs.pk), {"available_leave": 1}, format="json"
        )
        self.assertNotEqual(
            response.status_code, 403, "the nominated approver was locked out"
        )

    def test_a_nominated_approver_still_cannot_approve_their_own(self):
        own = self._request_for(self.attacker)
        LeaveRequestConditionApproval.objects.create(
            manager_id=self.attacker, sequence=1, leave_request_id=own
        )
        self._as(self.attacker_user)
        response = self.client.put(
            APPROVE.format(own.pk), {"available_leave": 1}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._status_of(own), "requested")
