"""Deepen: hourly_computation and compute_salary_on_period hourly branch."""

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

    @patch("payroll.methods.methods.get_holiday_dates", return_value=[])
    @patch("payroll.methods.methods.get_working_days")
    @patch("payroll.methods.methods.get_attendance")
    def test_hourly_working_day_regular_pay(self, mock_att, mock_wd, _mock_h):
        mock_wd.return_value = {"working_days_on": [self.workday]}
        mock_att.return_value = {
            "attendances_on_period": [
                self._att(self.workday, at_work=28800, overtime=3600)
            ],
            "present_on": [self.workday],
            "conflict_dates": [],
        }
        data = hourly_computation(self.employee, 100.0, self.start, self.end)
        self.assertEqual(data["regular_seconds"], 25200)
        self.assertEqual(data["ot_regular_seconds"], 3600)
        self.assertEqual(data["ot_seconds"], 3600)
        self.assertEqual(data["basic_pay"], 700.0)
        self.assertEqual(data["loss_of_pay"], 0)

    @patch("payroll.methods.methods.get_holiday_dates", return_value=[])
    @patch(
        "payroll.methods.methods.get_working_days",
        return_value={"working_days_on": []},
    )
    @patch("payroll.methods.methods.get_attendance")
    def test_hourly_week_off_all_ot(self, mock_att, _mock_wd, _mock_h):
        off_day = date(2024, 1, 7)  # Sunday
        mock_att.return_value = {
            "attendances_on_period": [self._att(off_day, at_work=14400, overtime=0)],
            "present_on": [off_day],
            "conflict_dates": [],
        }
        data = hourly_computation(self.employee, 100.0, self.start, self.end)
        self.assertEqual(data["regular_seconds"], 0)
        self.assertEqual(data["ot_week_off_seconds"], 14400)
        self.assertEqual(data["basic_pay"], 0.0)

    @patch("payroll.methods.methods.get_holiday_dates")
    @patch(
        "payroll.methods.methods.get_working_days",
        return_value={"working_days_on": []},
    )
    @patch("payroll.methods.methods.get_attendance")
    def test_hourly_holiday_all_ot(self, mock_att, _mock_wd, mock_h):
        holiday = date(2024, 1, 15)
        mock_h.return_value = [holiday]
        mock_att.return_value = {
            "attendances_on_period": [self._att(holiday, at_work=18000, overtime=0)],
            "present_on": [holiday],
            "conflict_dates": [],
        }
        data = hourly_computation(self.employee, 50.0, self.start, self.end)
        self.assertEqual(data["ot_holiday_seconds"], 18000)
        self.assertEqual(data["regular_seconds"], 0)
        self.assertEqual(data["basic_pay"], 0.0)

    @patch("payroll.methods.methods.months_between_range", return_value=[])
    @patch("payroll.methods.methods.get_holiday_dates", return_value=[])
    @patch("payroll.methods.methods.get_working_days")
    @patch("payroll.methods.methods.get_attendance")
    def test_compute_salary_on_period_hourly(self, mock_att, mock_wd, _h, _m):
        Contract.objects.create(
            contract_name="Hourly Active",
            employee_id=self.employee,
            contract_start_date=date(2024, 1, 1),
            wage_type="hourly",
            wage=100.0,
            contract_status="active",
        )
        mock_wd.return_value = {"working_days_on": [self.workday]}
        mock_att.return_value = {
            "attendances_on_period": [
                self._att(self.workday, at_work=28800, overtime=3600)
            ],
            "present_on": [self.workday],
            "conflict_dates": [],
        }
        summary = {
            "present": 10,
            "paid_leave": 1,
            "week_off": 2,
            "holiday": 1,
            "unpaid_leave": 1,
            "absent": 0,
        }
        data = compute_salary_on_period(
            self.employee, self.start, self.end, month_summary=summary
        )
        self.assertEqual(data["paid_days"], 14)
        self.assertEqual(data["unpaid_days"], 1)
        self.assertEqual(data["regular_seconds"], 25200)
        self.assertEqual(data["ot_regular_seconds"], 3600)
        self.assertEqual(data["basic_pay"], 700.0)
        self.assertEqual(data["contract_wage"], 100.0)
