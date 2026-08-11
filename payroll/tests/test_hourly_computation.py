"""Hourly salary computation against Main's payroll.methods.hourly_computation."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from horilla.testkit import make_company, make_employee
from payroll.methods.methods import compute_salary_on_period, hourly_computation
from payroll.models.models import Contract


class HourlyComputationTests(TestCase):
    def setUp(self):
        company = make_company("Hourly Co")
        self.employee = make_employee(company=company, email="hourly@test.horilla")
        Contract.objects.filter(employee_id=self.employee).delete()
        self.workday = date(2024, 1, 8)  # Monday
        self.start = date(2024, 1, 1)
        self.end = date(2024, 1, 31)

    def _att(self, day, at_work, overtime=0):
        return SimpleNamespace(
            attendance_date=day,
            at_work_second=at_work,
            overtime_second=overtime,
        )

    @patch("payroll.methods.methods.get_attendance")
    def test_hourly_basic_pay_excludes_overtime_seconds(self, mock_att):
        # Main: paid seconds = at_work_second - overtime_second
        mock_att.return_value = {
            "attendances_on_period": [
                self._att(self.workday, at_work=28800, overtime=3600)
            ],
        }
        data = hourly_computation(self.employee, 100.0, self.start, self.end)
        # 25200s * (100/3600) = 700
        self.assertEqual(data["basic_pay"], 700.0)
        self.assertEqual(data["loss_of_pay"], 0)
        self.assertEqual(data["paid_days"], 1)
        self.assertEqual(data["unpaid_days"], 0)

    @patch("payroll.methods.methods.get_attendance")
    def test_hourly_sums_multiple_attendances(self, mock_att):
        mock_att.return_value = {
            "attendances_on_period": [
                self._att(date(2024, 1, 8), at_work=14400, overtime=0),
                self._att(date(2024, 1, 9), at_work=7200, overtime=0),
            ],
        }
        data = hourly_computation(self.employee, 50.0, self.start, self.end)
        # 21600s * (50/3600) = 300
        self.assertEqual(data["basic_pay"], 300.0)
        self.assertEqual(data["paid_days"], 2)

    @patch("payroll.methods.methods.months_between_range", return_value=[])
    @patch("payroll.methods.methods.get_attendance")
    def test_compute_salary_on_period_hourly(self, mock_att, _months):
        Contract.objects.create(
            contract_name="Hourly Active",
            employee_id=self.employee,
            contract_start_date=date(2024, 1, 1),
            wage_type="hourly",
            wage=100.0,
            contract_status="active",
        )
        mock_att.return_value = {
            "attendances_on_period": [
                self._att(self.workday, at_work=28800, overtime=3600)
            ],
        }
        data = compute_salary_on_period(self.employee, self.start, self.end)
        self.assertIsNotNone(data)
        self.assertEqual(data["basic_pay"], 700.0)
        self.assertEqual(data["contract_wage"], 100.0)
        self.assertEqual(data["paid_days"], 1)
        self.assertIn("month_data", data)
