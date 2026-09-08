"""GHSA-97wm-28fj-g4pj, write side: the rest of the record-specific handlers.

The leave endpoints get their own module; these are the other handlers that
`manager_permission_required` guarded, which asks whether anybody at all
reports to the caller and never which employee the record belongs to.

The attacker throughout is an employee who manages one unrelated person and
holds no permission on the app in question -- an ordinary line manager, which
is what made the class severe rather than theoretical. Overtime approval feeds
payroll, so approving your own is refused independently of the manager test,
the same rule GHSA-gc35-jfv9-r3cm established for leave allocations.
"""

import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from attendance.models import Attendance
from base.models import RotatingWorkType, RotatingWorkTypeAssign, WorkType
from employee.models import EmployeeWorkInformation
from horilla.testkit import make_company, make_employee, make_user
from horilla.testkit.factories import make_attendance
from horilla_documents.models import Document

VALIDATE = "/api/v1/attendance/attendance-validate/{}"
OVERTIME_APPROVE = "/api/v1/attendance/overtime-approve/{}"
REQUEST_APPROVE = "/api/v1/attendance/attendance-request-approve/{}"
ROTATING_ASSIGN = "/api/v1/base/rotating-worktype-assigns/{}/"
DOC_APPROVE = "/api/v1/employee/document-request-approve-reject/{}/{}/"
DOC_BULK = "/api/v1/employee/document-bulk-approve-reject/"


def _manage(employee, manager):
    EmployeeWorkInformation.objects.filter(employee_id=employee).update(
        reporting_manager_id=manager
    )


class WriteTargetScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = make_company("Write Scope Co")

        self.attacker_user = make_user("ws_attacker", password="secret123")
        self.attacker = make_employee(
            company=self.company,
            email="ws_attacker@test.horilla",
            user=self.attacker_user,
            phone="3000001",
        )
        self.victim = make_employee(
            company=self.company, email="ws_victim@test.horilla", phone="3000002"
        )
        self.subordinate = make_employee(
            company=self.company, email="ws_sub@test.horilla", phone="3000003"
        )
        _manage(self.subordinate, self.attacker)

        self.boss_user = make_user("ws_boss", password="secret123")
        self.boss = make_employee(
            company=self.company,
            email="ws_boss@test.horilla",
            user=self.boss_user,
            phone="3000004",
        )
        _manage(self.victim, self.boss)
        self.client.force_authenticate(user=self.attacker_user)

    def _rotating_assignment(self, employee, name):
        rotating = RotatingWorkType.objects.create(
            name=name,
            work_type1=WorkType.objects.create(work_type=f"{name} A"),
            work_type2=WorkType.objects.create(work_type=f"{name} B"),
        )
        return RotatingWorkTypeAssign.objects.create(
            employee_id=employee, rotating_work_type_id=rotating
        )

    def _attendance(self, employee, validated=False, overtime=3600):
        return make_attendance(
            employee=employee,
            attendance_date=datetime.date(2026, 8, 3),
            overtime_second=overtime,
            validated=validated,
        )

    # --- attendance -------------------------------------------------------

    def test_cannot_validate_a_stranger_attendance(self):
        record = self._attendance(self.victim)
        response = self.client.put(VALIDATE.format(record.pk))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attendance.objects.get(pk=record.pk).attendance_validated)

    def test_cannot_approve_own_overtime(self):
        """Overtime feeds payroll; self-approval is the GHSA-gc35 rule."""
        record = self._attendance(self.attacker)
        Attendance.objects.filter(pk=record.pk).update(
            attendance_overtime_approve=False
        )
        response = self.client.put(OVERTIME_APPROVE.format(record.pk))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Attendance.objects.get(pk=record.pk).attendance_overtime_approve
        )

    def test_cannot_approve_a_stranger_overtime(self):
        record = self._attendance(self.victim)
        Attendance.objects.filter(pk=record.pk).update(
            attendance_overtime_approve=False
        )
        response = self.client.put(OVERTIME_APPROVE.format(record.pk))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Attendance.objects.get(pk=record.pk).attendance_overtime_approve
        )

    def test_cannot_approve_a_stranger_attendance_request(self):
        record = self._attendance(self.victim)
        response = self.client.put(REQUEST_APPROVE.format(record.pk))
        self.assertEqual(response.status_code, 403)

    def test_a_real_subordinate_can_still_be_validated(self):
        record = self._attendance(self.subordinate)
        response = self.client.put(VALIDATE.format(record.pk))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(Attendance.objects.get(pk=record.pk).attendance_validated)

    # --- rotating work type assignment ------------------------------------

    def test_cannot_read_or_delete_a_stranger_rotating_assignment(self):
        assignment = self._rotating_assignment(self.victim, "Rotate A")
        self.assertEqual(
            self.client.get(ROTATING_ASSIGN.format(assignment.pk)).status_code, 403
        )
        self.assertEqual(
            self.client.delete(ROTATING_ASSIGN.format(assignment.pk)).status_code, 403
        )
        self.assertTrue(
            RotatingWorkTypeAssign.objects.filter(pk=assignment.pk).exists()
        )

    def test_own_rotating_assignment_is_still_readable(self):
        """
        This view already carried an owner-or-manager-or-permission helper that
        was never wired to a handler. The decorator applies that same rule, so
        the owner must still get through.
        """
        assignment = self._rotating_assignment(self.attacker, "Rotate B")
        self.assertEqual(
            self.client.get(ROTATING_ASSIGN.format(assignment.pk)).status_code, 200
        )

    # --- documents --------------------------------------------------------

    def _document(self, employee):
        return Document.objects.create(title="Passport", employee_id=employee)

    def test_cannot_approve_a_stranger_document(self):
        document = self._document(self.victim)
        response = self.client.post(DOC_APPROVE.format(document.pk, "approved"))
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(Document.objects.get(pk=document.pk).status, "approved")

    def test_cannot_approve_own_document(self):
        document = self._document(self.attacker)
        response = self.client.post(DOC_APPROVE.format(document.pk, "approved"))
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(Document.objects.get(pk=document.pk).status, "approved")

    def test_a_subordinate_document_can_still_be_approved(self):
        document = self._document(self.subordinate)
        response = self.client.post(DOC_APPROVE.format(document.pk, "approved"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Document.objects.get(pk=document.pk).status, "approved")

    def test_bulk_document_approval_skips_records_out_of_scope(self):
        """Scoping the by-id route alone would leave this as its unscoped twin."""
        theirs = self._document(self.victim)
        own = self._document(self.attacker)
        self.client.put(
            DOC_BULK, {"ids": [theirs.pk, own.pk], "status": "approved"}, format="json"
        )
        self.assertNotEqual(Document.objects.get(pk=theirs.pk).status, "approved")
        self.assertNotEqual(Document.objects.get(pk=own.pk).status, "approved")
