"""A manager check must name the employee it is about.

GHSA-39gq-9wwx-p8hx reported that ``PUT /api/employee/employee-bank-details/<pk>/``
let any employee who managed at least one person overwrite the bank account of
any other employee in the company. The cause was not in the view: the shared
``manager_or_owner_permission_required`` decorator delegated to
``ManagerPermission``, which asks only whether anybody reports to the caller.
"Is a manager" was accepted as "is this employee's manager".

The attacker here is deliberately ordinary -- a line manager with one unrelated
subordinate, holding no bank-details permission and owning no part of the
victim's record. That is a common privilege in any real org chart, which is what
made the original report severe: it redirects salary.

The three allow cases matter as much as the deny ones. Scoping a permission check
is only correct if it still admits the people who legitimately held it, and the
fix would be worse than the bug if it locked out the victim's real manager.
"""

from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from employee.models import EmployeeBankDetails, EmployeeWorkInformation
from horilla.testkit import make_company, make_employee, make_user

ENDPOINT = "/api/employee/employee-bank-details/{}/"

VICTIM_ACCOUNT = "VICTIM-ACCT-0001"
ATTACKER_ACCOUNT = "ATTACKER-OWNED-1"


def _set_reporting_manager(employee, manager):
    EmployeeWorkInformation.objects.filter(employee_id=employee).update(
        reporting_manager_id=manager
    )


class BankDetailsManagerScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = make_company("Scope Co")

        self.attacker_user = make_user("scope_attacker", password="secret123")
        self.attacker = make_employee(
            company=self.company,
            email="scope_attacker@test.horilla",
            user=self.attacker_user,
            phone="1000001",
        )
        self.victim = make_employee(
            company=self.company,
            email="scope_victim@test.horilla",
            phone="1000002",
        )
        # The attacker manages someone -- just not the victim. This is the whole
        # point of the report: the old check passed on the mere existence of
        # this row.
        self.subordinate = make_employee(
            company=self.company,
            email="scope_subordinate@test.horilla",
            phone="1000003",
        )
        _set_reporting_manager(self.subordinate, self.attacker)

        self.bank = EmployeeBankDetails.objects.create(
            employee_id=self.victim,
            bank_name="VictimBank",
            account_number=VICTIM_ACCOUNT,
            branch="B",
            country="C",
            any_other_code1="X",
        )

    def _payload(self, account=ATTACKER_ACCOUNT):
        return {
            "employee_id": self.victim.id,
            "account_number": account,
            "bank_name": "Hacked",
            "branch": "X",
            "country": "X",
            "any_other_code1": "X",
        }

    def _auth(self, user):
        self.client.force_authenticate(user=type(user).objects.get(pk=user.pk))

    def _account_number(self):
        return EmployeeBankDetails.objects.get(pk=self.bank.pk).account_number

    def test_manager_of_someone_else_cannot_rewrite_bank_details(self):
        """The reported attack: 403, and the account is untouched."""
        self._auth(self.attacker_user)
        response = self.client.put(
            ENDPOINT.format(self.bank.pk), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._account_number(), VICTIM_ACCOUNT)

    def test_manager_of_someone_else_cannot_delete_bank_details(self):
        """DELETE had no owner path at all, so it was reachable the same way."""
        self._auth(self.attacker_user)
        response = self.client.delete(ENDPOINT.format(self.bank.pk))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(EmployeeBankDetails.objects.filter(pk=self.bank.pk).exists())

    def test_the_victims_own_manager_is_still_allowed(self):
        """Scoping the check must not lock out the manager it is meant to admit."""
        _set_reporting_manager(self.victim, self.attacker)
        self._auth(self.attacker_user)
        response = self.client.put(
            ENDPOINT.format(self.bank.pk), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._account_number(), ATTACKER_ACCOUNT)

    def test_the_owner_is_still_allowed(self):
        owner_user = make_user("scope_owner", password="secret123")
        self.bank.employee_id.employee_user_id = owner_user
        self.bank.employee_id.save()
        self._auth(owner_user)
        response = self.client.put(
            ENDPOINT.format(self.bank.pk), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_a_holder_of_the_permission_is_still_allowed(self):
        # PUT is gated by add_employeebankdetails, not change_. That is odd but
        # predates this fix, and the permission strings are left alone
        # deliberately: changing them would alter who can reach the endpoint on
        # installs that have already granted one and not the other.
        self.attacker_user.user_permissions.add(
            Permission.objects.get(codename="add_employeebankdetails")
        )
        self._auth(self.attacker_user)
        response = self.client.put(
            ENDPOINT.format(self.bank.pk), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, 200)
