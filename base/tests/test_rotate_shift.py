"""The rotate_shift job, with and without rotating shift assignments."""

from datetime import date, timedelta

from django.test import TestCase

from base.models import EmployeeShift, RotatingShift, RotatingShiftAssign
from base.scheduler import rotate_shift
from horilla.testkit.factories import make_company, make_employee


class TestRotateShift(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Rotation Test Ltd")
        cls.early = EmployeeShift.objects.create(employee_shift="Early")
        cls.late = EmployeeShift.objects.create(employee_shift="Late")
        cls.rotation = RotatingShift.objects.create(
            name="Early/Late", shift1=cls.early, shift2=cls.late
        )
        cls.employee = make_employee(
            company=company, email="worker@rotate.test", shift=cls.early
        )

    def assign(self, start, next_change):
        return RotatingShiftAssign.objects.create(
            employee_id=self.employee,
            rotating_shift_id=self.rotation,
            start_date=start,
            next_change_date=next_change,
            current_shift=self.early,
            next_shift=self.late,
            based_on="after",
            rotate_after_day=7,
            additional_data={"next_shift_index": 0},
        )

    def test_runs_when_no_assignment_has_started(self):
        rotate_shift()  # none at all: used to raise TypeError

        next_week = date.today() + timedelta(days=7)
        upcoming = self.assign(start=next_week, next_change=next_week)
        rotate_shift()  # one that hasn't started yet: used to raise TypeError
        upcoming.refresh_from_db()
        self.assertTrue(upcoming.is_active)
        self.assertEqual(upcoming.current_shift, self.early)

    def test_an_assignment_due_today_still_rotates(self):
        today = date.today()
        due = self.assign(start=today - timedelta(days=7), next_change=today)
        rotate_shift()
        due.refresh_from_db()
        self.assertEqual(
            (due.current_shift, due.next_change_date),
            (self.late, today + timedelta(days=7)),
        )
        self.employee.employee_work_info.refresh_from_db()
        self.assertEqual(self.employee.employee_work_info.shift_id, self.late)
