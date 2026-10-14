"""Bulk approve / reject of shift and work type requests.

A rejected request is a decision: bulk approve must skip it rather than flip it
back to approved. Both bulk views also report how many they changed
(X-Hlv-Bulk-Result) so the browser can show a result dialog.
"""

import datetime
import json

from django.test import Client, TestCase
from django.urls import reverse

from base.models import (
    EmployeeShift,
    RotatingShift,
    RotatingShiftAssign,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    ShiftRequest,
    WorkType,
    WorkTypeRequest,
)
from horilla.testkit import make_company, make_employee, make_user


class BulkApproveRejectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Bulk Co")
        cls.user = make_user("bulk-approver", is_superuser=True)
        cls.admin = make_employee(
            company=company, email="bulk-approver@test.horilla", user=cls.user
        )
        cls.staff = make_employee(company=company, email="bulk-staff@test.horilla")
        cls.day = EmployeeShift.objects.create(employee_shift="Day")
        cls.night = EmployeeShift.objects.create(employee_shift="Night")
        cls.office = WorkType.objects.create(work_type="Office")
        cls.remote = WorkType.objects.create(work_type="Remote")
        cls.today = datetime.date.today()

    def _shift(self, **flags):
        return ShiftRequest.objects.create(
            employee_id=self.staff,
            shift_id=self.night,
            previous_shift_id=self.day,
            requested_date=self.today,
            requested_till=self.today + datetime.timedelta(days=5),
            description="x",
            **flags,
        )

    def _work_type(self, **flags):
        return WorkTypeRequest.objects.create(
            employee_id=self.staff,
            work_type_id=self.remote,
            previous_work_type_id=self.office,
            requested_date=self.today,
            requested_till=self.today + datetime.timedelta(days=5),
            description="x",
            **flags,
        )

    def _post(self, url_name, ids):
        client = Client()
        client.force_login(self.user)
        response = client.post(reverse(url_name), {"ids": json.dumps(ids)})
        self.assertEqual(response.status_code, 200)
        return response, json.loads(response["X-Hlv-Bulk-Result"])

    def test_bulk_approve_skips_rejected_shift_requests(self):
        pending, rejected = self._shift(), self._shift(canceled=True)

        _, result = self._post("shift-request-bulk-approve", [pending.pk, rejected.pk])

        pending.refresh_from_db()
        rejected.refresh_from_db()
        self.assertTrue(pending.approved)
        self.assertFalse(rejected.approved, "a rejected shift must stay rejected")
        self.assertTrue(rejected.canceled)
        self.assertEqual(result, {"done": 1, "failed": 1})

    def test_bulk_approve_skips_rejected_work_type_requests(self):
        pending, rejected = self._work_type(), self._work_type(canceled=True)

        _, result = self._post(
            "work-type-request-bulk-approve", [pending.pk, rejected.pk]
        )

        pending.refresh_from_db()
        rejected.refresh_from_db()
        self.assertTrue(pending.approved)
        self.assertFalse(rejected.approved)
        self.assertEqual(result, {"done": 1, "failed": 1})

    def test_bulk_reject_reports_what_it_rejected(self):
        pending, already = self._shift(), self._shift(canceled=True)

        _, result = self._post("shift-request-bulk-cancel", [pending.pk, already.pk])

        pending.refresh_from_db()
        self.assertTrue(pending.canceled)
        self.assertEqual(result, {"done": 1, "failed": 1})

    def test_unknown_ids_count_as_failed_instead_of_crashing(self):
        _, result = self._post("shift-request-bulk-approve", [999999])
        self.assertEqual(result, {"done": 0, "failed": 1})


class BulkArchiveRotatingShiftAssignTests(TestCase):
    """Bulk archive / un-archive reports its counts like bulk approve / reject."""

    @classmethod
    def setUpTestData(cls):
        company = make_company("Archive Co")
        cls.user = make_user("archive-admin", is_superuser=True)
        make_employee(
            company=company, email="archive-admin@test.horilla", user=cls.user
        )
        cls.staff = make_employee(company=company, email="archive-staff@test.horilla")
        cls.other = make_employee(company=company, email="archive-other@test.horilla")
        day = EmployeeShift.objects.create(employee_shift="Day")
        night = EmployeeShift.objects.create(employee_shift="Night")
        cls.rotation = RotatingShift.objects.create(
            name="Day to Night", shift1=day, shift2=night
        )

    def _assign(self, employee, is_active=True):
        return RotatingShiftAssign.objects.create(
            employee_id=employee,
            rotating_shift_id=self.rotation,
            based_on="after",
            start_date=datetime.date.today(),
            next_change_date=datetime.date.today(),
            is_active=is_active,
        )

    def _post(self, is_active, ids):
        client = Client()
        client.force_login(self.user)
        response = client.post(
            reverse("rotating-shift-assign-bulk-archive") + f"?is_active={is_active}",
            {"ids": json.dumps(ids)},
        )
        self.assertEqual(response.status_code, 200)
        return json.loads(response["X-Hlv-Bulk-Result"])

    def test_archive_reports_each_record_and_unknown_ids_fail(self):
        first, second = self._assign(self.staff), self._assign(self.other)

        result = self._post(False, [first.pk, second.pk, 999999])

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_active or second.is_active)
        self.assertEqual(result, {"done": 2, "failed": 1})

    def test_unarchive_skips_employee_that_already_has_an_active_record(self):
        archived = self._assign(self.staff, is_active=False)
        self._assign(self.staff)  # the employee's current active assign
        free = self._assign(self.other, is_active=False)

        result = self._post(True, [archived.pk, free.pk])

        archived.refresh_from_db()
        free.refresh_from_db()
        self.assertFalse(archived.is_active)
        self.assertTrue(free.is_active)
        self.assertEqual(result, {"done": 1, "failed": 1})


class BulkArchiveRotatingWorkTypeAssignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("WT Archive Co")
        cls.user = make_user("wt-archive-admin", is_superuser=True)
        make_employee(
            company=company, email="wt-archive-admin@test.horilla", user=cls.user
        )
        cls.staff = make_employee(
            company=company, email="wt-archive-staff@test.horilla"
        )
        cls.office = WorkType.objects.create(work_type="Office")
        cls.remote = WorkType.objects.create(work_type="Remote")
        cls.rotation = RotatingWorkType.objects.create(
            name="Office or Remote", work_type1=cls.office, work_type2=cls.remote
        )

    def _assign(self, is_active=True):
        return RotatingWorkTypeAssign.objects.create(
            employee_id=self.staff,
            rotating_work_type_id=self.rotation,
            based_on="after",
            start_date=datetime.date.today(),
            next_change_date=datetime.date.today(),
            is_active=is_active,
        )

    def _post(self, is_active, ids):
        client = Client()
        client.force_login(self.user)
        response = client.post(
            reverse("rotating-shift-work-type-bulk-archive")
            + f"?is_active={is_active}",
            {"ids": json.dumps(ids)},
        )
        self.assertEqual(response.status_code, 200)
        return json.loads(response["X-Hlv-Bulk-Result"])

    def test_archive_counts_done_and_missing(self):
        assign = self._assign()
        result = self._post(False, [assign.pk, 999999])
        assign.refresh_from_db()
        self.assertFalse(assign.is_active)
        self.assertEqual(result, {"done": 1, "failed": 1})

    def test_unarchive_fails_when_employee_already_has_an_active_record(self):
        archived = self._assign(is_active=False)
        self._assign()
        result = self._post(True, [archived.pk])
        archived.refresh_from_db()
        self.assertFalse(archived.is_active)
        self.assertEqual(result, {"done": 0, "failed": 1})
