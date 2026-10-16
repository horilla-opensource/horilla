"""Employees without a shift are not time-tracked: not counted as absent."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from base.models import EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule
from horilla.testkit.factories import make_company, make_employee, make_user

MONDAY, FRIDAY = date(2026, 10, 5), date(2026, 10, 9)


class TestEmployeesWithoutAShift(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Shift Test Ltd")
        shift = EmployeeShift.objects.create(employee_shift="Day")
        shift.company_id.add(company)
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            EmployeeShiftSchedule.objects.create(
                shift_id=shift,
                day=EmployeeShiftDay.objects.get(day=day),
                start_time=time(8, 0),
                end_time=time(16, 0),
                minimum_working_hour="08:00",
            )
        cls.worker = make_employee(
            company=company, email="worker@shift.test", first_name="Worker", shift=shift
        )
        cls.manager = make_employee(
            company=company, email="manager@shift.test", first_name="Salaried"
        )
        boss = make_user("boss", is_superuser=True)
        make_employee(company=company, email="boss@shift.test", user=boss)
        cls.boss = boss

    def test_top_absentees_leave_out_employees_without_a_shift(self):
        self.client.force_login(self.boss)
        response = self.client.get(
            reverse("attendance-dashboard-absentees"),
            {"from_date": MONDAY.isoformat(), "to_date": FRIDAY.isoformat()},
        )
        names = [row["name"] for row in response.json()["absentees"]]
        self.assertIn(self.worker.get_full_name(), names)
        self.assertNotIn(self.manager.get_full_name(), names)
