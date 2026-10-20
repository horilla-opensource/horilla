"""Main dashboard: employees without a shift aren't expected to clock in."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from attendance.filters import get_expected_to_check_in
from attendance.models import Attendance
from base.models import EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule
from employee.models import Employee
from horilla.testkit.factories import make_company, make_employee, make_user


class TestDashboardWithoutShift(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Dashboard Shift Ltd")
        shift = EmployeeShift.objects.create(employee_shift="Day")
        shift.company_id.add(company)
        EmployeeShiftSchedule.objects.create(
            shift_id=shift,
            day=EmployeeShiftDay.objects.get(day=date.today().strftime("%A").lower()),
            start_time=time(8, 0),
            end_time=time(16, 0),
            minimum_working_hour="08:00",
        )
        cls.worker = make_employee(
            company=company, email="worker@dash.test", first_name="Worker", shift=shift
        )
        cls.salaried = make_employee(
            company=company, email="salaried@dash.test", first_name="Salaried"
        )
        cls.boss = make_user("boss", is_superuser=True)
        make_employee(company=company, email="boss@dash.test", user=cls.boss)

    def kpi(self):
        self.client.force_login(self.boss)
        return self.client.get(reverse("dashboard-kpi-data")).json()

    def test_kpis_count_only_employees_with_a_shift(self):
        data = self.kpi()
        self.assertEqual(data["total_employees"], 3)  # headcount: everyone
        self.assertEqual((data["expected_today"], data["absent_today"]), (1, 1))
        self.assertEqual(data["attendance_rate"], 0)

        Attendance.objects.create(
            employee_id=self.worker,
            attendance_date=date.today(),
            attendance_clock_in_date=date.today(),
            attendance_clock_in=time(8, 0),
            attendance_worked_hour="00:00",
            minimum_hour="08:00",
        )
        data = self.kpi()
        self.assertEqual((data["absent_today"], data["attendance_rate"]), (0, 100.0))

    def test_the_expected_to_check_in_list_matches(self):
        expected = get_expected_to_check_in(Employee.objects.all(), None, date.today())
        self.assertEqual(list(expected), [self.worker])

    def test_the_attendance_trend_uses_employees_with_a_shift(self):
        Attendance.objects.create(
            employee_id=self.worker,
            attendance_date=date.today(),
            attendance_clock_in_date=date.today(),
            attendance_clock_in=time(8, 0),
            attendance_worked_hour="00:00",
            minimum_hour="08:00",
        )
        self.client.force_login(self.boss)
        weeks = self.client.get(reverse("dashboard-attendance-trend")).json()["weeks"]
        current = next(w for w in weeks if "(now)" in w["week"])
        self.assertEqual(current["rate"], 100.0)
