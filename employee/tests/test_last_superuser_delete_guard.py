"""Deleting an employee must not be able to remove the org's last admin.

employee_archive / employee_bulk_archive already refuse to archive the last
active superuser. employee_delete / employee_bulk_delete had no equivalent
check at all -- a lone admin could delete their own account (or someone else
could delete it for them) with nothing to stop it, permanently, with no
undo the way archiving has. A customer hit exactly this: deleted their own
employee profile, which cascaded into deleting their own login, and was
locked out with no admin account left on the instance.

These tests pin the same protection on the delete path.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from employee.models import Employee
from horilla.testkit import make_company, make_employee, make_user
from payroll.models.models import Contract

User = get_user_model()


class LastSuperuserDeleteGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company("Guard Co")

    def _superuser_employee(self, username, email=None):
        user = make_user(username, is_superuser=True, email=email)
        employee = make_employee(
            company=self.company,
            email=email or f"{username}@test.horilla",
            first_name=username,
            user=user,
        )
        # make_employee()'s EmployeeWorkInformation save auto-creates an
        # *active* Contract (payroll/signals.py). employee_delete never
        # touches active contracts -- deliberately, it's the one thing it
        # already refuses to cascade-delete -- so it would raise
        # ProtectedError before the guard under test ever runs. Deactivating
        # it here isolates the last-superuser check from that unrelated,
        # pre-existing behavior.
        Contract.objects.filter(employee_id=employee).update(contract_status="expired")
        return employee

    def _client_as(self, employee):
        client = Client()
        client.force_login(employee.employee_user_id)
        return client

    def test_cannot_delete_the_last_superuser(self):
        admin = self._superuser_employee("only-admin")
        client = self._client_as(admin)

        client.post(
            reverse("employee-delete", args=[admin.pk]),
            {"view": ""},
        )

        self.assertTrue(
            Employee.objects.filter(pk=admin.pk).exists(),
            "the last superuser's employee record must survive the delete attempt",
        )
        self.assertTrue(
            User.objects.filter(pk=admin.employee_user_id.pk).exists(),
            "the last superuser's login must survive the delete attempt",
        )

    def test_can_delete_a_superuser_when_another_remains(self):
        admin_a = self._superuser_employee("admin-a")
        admin_b = self._superuser_employee("admin-b")
        client = self._client_as(admin_a)

        client.post(
            reverse("employee-delete", args=[admin_b.pk]),
            {"view": ""},
        )

        self.assertFalse(
            Employee.objects.filter(pk=admin_b.pk).exists(),
            "deleting a superuser is fine as long as another one remains",
        )
        self.assertTrue(Employee.objects.filter(pk=admin_a.pk).exists())

    def test_can_still_delete_an_ordinary_employee(self):
        admin = self._superuser_employee("admin-c")
        staffer = make_employee(
            company=self.company, email="staffer@test.horilla", first_name="Staffer"
        )
        Contract.objects.filter(employee_id=staffer).update(contract_status="expired")
        client = self._client_as(admin)

        client.post(
            reverse("employee-delete", args=[staffer.pk]),
            {"view": ""},
        )

        self.assertFalse(
            Employee.objects.filter(pk=staffer.pk).exists(),
            "non-superuser deletes must be unaffected by the new guard",
        )

    def test_bulk_delete_refuses_the_last_superuser(self):
        admin = self._superuser_employee("bulk-only-admin")
        client = self._client_as(admin)

        client.post(
            reverse("employee-bulk-delete"),
            {"ids": f"[{admin.pk}]"},
        )

        self.assertTrue(Employee.objects.filter(pk=admin.pk).exists())
        self.assertTrue(User.objects.filter(pk=admin.employee_user_id.pk).exists())

    def test_bulk_delete_allows_one_superuser_to_survive(self):
        admin_a = self._superuser_employee("bulk-admin-a")
        admin_b = self._superuser_employee("bulk-admin-b")
        # A separate, non-superuser requester with just the one permission --
        # deliberately not one of the two being deleted. Making the acting
        # user also a deletion target is an unrelated edge case (it collides
        # with django-auditlog's actor FK, a pre-existing, separate concern)
        # and isn't what this test is about: whether the guard stops bulk
        # delete short of removing every superuser.
        # A middleware force-logs-out any authenticated user with no linked
        # Employee ("An employee related to this user's credentials does not
        # exist"), so the requester needs one too, not just the permission.
        requester_user = make_user("bulk-requester")
        requester_user.user_permissions.add(
            Permission.objects.get(
                codename="delete_employee", content_type__app_label="employee"
            )
        )
        requester = make_employee(
            company=self.company,
            email="requester@test.horilla",
            first_name="Requester",
            user=requester_user,
        )
        Contract.objects.filter(employee_id=requester).update(contract_status="expired")
        client = Client()
        client.force_login(requester_user)

        client.post(
            reverse("employee-bulk-delete"),
            {"ids": f"[{admin_a.pk}, {admin_b.pk}]"},
        )

        # Whichever order the queryset iterates in, exactly one must remain.
        remaining = Employee.objects.filter(pk__in=[admin_a.pk, admin_b.pk])
        self.assertEqual(
            remaining.count(),
            1,
            "bulk delete must stop short of removing every superuser",
        )

    def test_bulk_delete_skips_own_employee_but_deletes_others(self):
        admin_a = self._superuser_employee("self-admin-a")
        admin_b = self._superuser_employee("self-admin-b")
        staffer = make_employee(
            company=self.company, email="self-staffer@test.horilla", first_name="S"
        )
        Contract.objects.filter(employee_id=staffer).update(contract_status="expired")
        client = self._client_as(admin_a)

        client.post(
            reverse("employee-bulk-delete"),
            {"ids": f"[{admin_a.pk}, {staffer.pk}, {admin_b.pk}]"},
        )

        self.assertTrue(Employee.objects.filter(pk=admin_a.pk).exists())
        self.assertTrue(User.objects.filter(pk=admin_a.employee_user_id.pk).exists())
        self.assertFalse(Employee.objects.filter(pk=staffer.pk).exists())
        self.assertFalse(Employee.objects.filter(pk=admin_b.pk).exists())

    def test_bulk_archive_skips_own_employee_but_archives_others(self):
        admin_a = self._superuser_employee("arch-admin-a")
        self._superuser_employee("arch-admin-b")
        staffer = make_employee(
            company=self.company, email="arch-staffer@test.horilla", first_name="A"
        )
        client = self._client_as(admin_a)

        client.post(
            reverse("employee-bulk-archive"),
            {"ids": f"[{admin_a.pk}, {staffer.pk}]"},
        )

        admin_a.refresh_from_db()
        staffer.refresh_from_db()
        self.assertTrue(admin_a.is_active)
        self.assertFalse(staffer.is_active)

    def test_bulk_delete_reports_blocked_employees_in_the_summary(self):
        admin = self._superuser_employee("sum-admin")
        blocked = make_employee(
            company=self.company, email="sum-blocked@test.horilla", first_name="Blocked"
        )  # keeps the active contract make_employee() creates -> PROTECT
        client = self._client_as(admin)

        response = client.post(
            reverse("employee-bulk-delete"),
            {"ids": f"[{admin.pk}, {blocked.pk}]"},
        )
        data = response.json()

        self.assertTrue(Employee.objects.filter(pk=blocked.pk).exists())
        self.assertEqual(data["deleted"], 0)
        # Own employee + the blocked one: total = deleted + failed = selected.
        self.assertEqual(data["failed"], 2)

    def test_bulk_delete_removes_many_and_reports_counts(self):
        admin = self._superuser_employee("many-admin")
        free = []
        for i in range(5):
            e = make_employee(
                company=self.company, email=f"many{i}@test.horilla", first_name=f"M{i}"
            )
            Contract.objects.filter(employee_id=e).update(contract_status="expired")
            free.append(e.pk)
        blocked = make_employee(
            company=self.company, email="many-blocked@test.horilla", first_name="B"
        )  # active contract -> PROTECT
        client = self._client_as(admin)

        response = client.post(
            reverse("employee-bulk-delete"),
            {"ids": json.dumps(free + [blocked.pk, admin.pk])},
        )
        data = response.json()

        self.assertEqual(data["deleted"], 5)
        self.assertEqual(data["failed"], 2)  # the blocked one + own employee
        self.assertFalse(Employee.objects.filter(pk__in=free).exists())
        self.assertTrue(Employee.objects.filter(pk=blocked.pk).exists())
        self.assertTrue(Employee.objects.filter(pk=admin.pk).exists())

    def test_employee_without_a_user_does_not_raise(self):
        """employee_user_id is nullable -- the guard must tolerate None."""
        self._superuser_employee("solo-admin")  # keeps count() >= 1 either way
        orphan = make_employee(
            company=self.company, email="orphan@test.horilla", first_name="Orphan"
        )
        Contract.objects.filter(employee_id=orphan).update(contract_status="expired")
        # .update() bypasses Employee.save(), which would otherwise
        # auto-create a fresh HorillaUser the moment the FK goes null.
        Employee.objects.filter(pk=orphan.pk).update(employee_user_id=None)

        client = Client()
        client.force_login(User.objects.get(username="solo-admin"))
        client.post(
            reverse("employee-delete", args=[orphan.pk]),
            {"view": ""},
        )

        self.assertFalse(
            Employee.objects.filter(pk=orphan.pk).exists(),
            "an employee with no linked login must still be deletable",
        )
