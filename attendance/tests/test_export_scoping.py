"""Exports are limited to the requester's scope, whichever ids the request names.

Covers the employee export and the attendance export, which share the scoping in
`export_data`.
"""

import io
import json
from datetime import date, timedelta

import pandas as pd
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from attendance.models import Attendance
from horilla.testkit import make_company, make_employee, make_user
from horilla.testkit.factories import make_attendance


class ExportScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Export Co")
        cls.users = {}
        cls.people = {}
        for key in ("alice", "bravo", "charlie", "boss"):
            user = make_user(f"exp_{key}", password="secret123")
            cls.users[key] = user
            cls.people[key] = make_employee(
                company=company,
                email=f"{key}@export.test",
                first_name=key.title(),
                last_name="Exportson",
                user=user,
            )
        # Bravo reports to the boss; Alice and Charlie report to nobody.
        work_info = cls.people["bravo"].employee_work_info
        work_info.reporting_manager_id = cls.people["boss"]
        work_info.save()
        cls.rows = {}
        for offset, key in enumerate(("alice", "bravo", "charlie"), start=1):
            cls.rows[key] = make_attendance(
                employee=cls.people[key],
                attendance_date=date.today() - timedelta(days=offset),
            )

    def _export(self, user, route, ids):
        client = Client()
        client.force_login(type(user).objects.get(pk=user.pk))
        return client.get(reverse(route), {"ids": json.dumps(ids)})

    @staticmethod
    def _text(response):
        """Everything in the spreadsheet, as one string."""
        frame = pd.read_excel(io.BytesIO(response.content), sheet_name=0)
        return " ".join(str(v) for v in frame.to_numpy().ravel())

    def _all_attendance_ids(self):
        return list(Attendance.objects.values_list("id", flat=True))

    def _all_employee_ids(self):
        return [p.pk for p in self.people.values()]

    # -- attendance export ---------------------------------------------------

    def test_plain_employee_gets_only_their_own_attendance_by_id(self):
        response = self._export(
            self.users["alice"], "attendance-info-export", self._all_attendance_ids()
        )
        self.assertEqual(response.status_code, 200)
        text = self._text(response)
        self.assertIn("Alice", text)
        self.assertNotIn("Bravo", text)
        self.assertNotIn("Charlie", text)

    def test_manager_gets_their_team_but_not_everyone(self):
        response = self._export(
            self.users["boss"], "attendance-info-export", self._all_attendance_ids()
        )
        text = self._text(response)
        self.assertIn("Bravo", text)
        self.assertNotIn("Alice", text)
        self.assertNotIn("Charlie", text)

    def test_permission_holder_still_exports_everything(self):
        """HR must keep working."""
        self.users["alice"].user_permissions.add(
            Permission.objects.get(codename="view_attendance")
        )
        response = self._export(
            self.users["alice"], "attendance-info-export", self._all_attendance_ids()
        )
        text = self._text(response)
        for name in ("Alice", "Bravo", "Charlie"):
            self.assertIn(name, text)

    # -- employee export -----------------------------------------------------

    def test_manager_of_one_person_cannot_export_everyone_by_id(self):
        response = self._export(
            self.users["boss"], "work-info-export", self._all_employee_ids()
        )
        self.assertEqual(response.status_code, 200)
        text = self._text(response)
        self.assertIn("bravo@export.test", text)
        self.assertNotIn("alice@export.test", text)
        self.assertNotIn("charlie@export.test", text)

    def test_employee_permission_holder_still_exports_everyone(self):
        self.users["boss"].user_permissions.add(
            Permission.objects.get(codename="view_employee")
        )
        response = self._export(
            self.users["boss"], "work-info-export", self._all_employee_ids()
        )
        text = self._text(response)
        for email in ("alice", "bravo", "charlie"):
            self.assertIn(f"{email}@export.test", text)
