"""Deepen: compute_salary_on_period with Contract + stubbed leave helpers."""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from horilla.testkit import make_company, make_employee
from payroll.methods.methods import compute_salary_on_period
from payroll.models.models import Contract

EMPTY_LEAVES = {
    "paid_leave": 0,
    "unpaid_leaves": 0,
    "partial_pay_days": 0,
    "total_leaves": 0,
    "paid_leave_dates": [],
    "unpaid_leave_dates": [],
    "custom_leave_dates": [],
    "custom_leave_breakdown": [],
    "leave_dates": [],
}


class ComputeSalaryOnPeriodTests(TestCase):
    def setUp(self):
        company = make_company("Salary Co")
        self.employee = make_employee(company=company, email="salary@test.horilla")
        # Employee create may auto-seed a zero-wage active contract.
        Contract.objects.filter(employee_id=self.employee).delete()
        self.start = date(2024, 1, 1)
        self.end = date(2024, 1, 31)

    def _activate(self, **kw):
        defaults = dict(
            contract_name="Active Monthly",
            employee_id=self.employee,
            contract_start_date=date(2024, 1, 1),
            wage_type="monthly",
            wage=30000.0,
            contract_status="active",
            deduct_leave_from_basic_pay=True,
            calculate_daily_leave_amount=True,
            deduction_for_one_leave_amount=0,
        )
        defaults.update(kw)
        return Contract.objects.create(**defaults)

    def test_no_active_contract_returns_none(self):
        self.assertIsNone(compute_salary_on_period(self.employee, self.start, self.end))

    def test_draft_contract_ignored(self):
        self._activate(contract_status="draft", wage=25000.0)
        self.assertIsNone(compute_salary_on_period(self.employee, self.start, self.end))

    @patch("payroll.methods.methods.months_between_range", return_value=[])
    @patch(
        "payroll.methods.methods.get_daily_salary",
        return_value={"day_wage": 1000.0},
    )
    @patch("payroll.methods.methods.get_leaves", return_value=EMPTY_LEAVES)
    def test_monthly_with_summary_deducts_unpaid(self, *_mocks):
        self._activate(wage=31000.0)
        summary = {
            "present": 20,
            "paid_leave": 2,
            "unpaid_leave": 1,
            "absent": 1,
            "week_off": 4,
            "holiday": 2,
        }
        data = compute_salary_on_period(
            self.employee, self.start, self.end, month_summary=summary
        )
        self.assertIsNotNone(data)
        self.assertEqual(data["unpaid_days"], 2)
        self.assertEqual(data["paid_days"], 28.0)
        self.assertEqual(data["contract_wage"], 31000.0)
        per_day = 31000.0 / 30
        self.assertAlmostEqual(data["loss_of_pay"], 2 * per_day)
        self.assertAlmostEqual(data["basic_pay"], 31000.0 - (2 * per_day))

    @patch("payroll.methods.methods.months_between_range", return_value=[])
    @patch(
        "payroll.methods.methods.get_daily_salary",
        return_value={"day_wage": 1000.0},
    )
    @patch("payroll.methods.methods.get_leaves", return_value=EMPTY_LEAVES)
    def test_monthly_unresolved_conflicts_marks_all_unpaid(self, *_mocks):
        self._activate(wage=31000.0)
        summary = {
            "present": 20,
            "paid_leave": 2,
            "unpaid_leave": 1,
            "absent": 1,
            "week_off": 4,
            "holiday": 2,
            "unresolved_conflicts": 1,
        }
        data = compute_salary_on_period(
            self.employee, self.start, self.end, month_summary=summary
        )
        self.assertEqual(data["unpaid_days"], 30)
        self.assertEqual(data["paid_days"], 0.0)

    @patch("payroll.methods.methods.months_between_range", return_value=[])
    @patch("payroll.methods.methods.get_leaves", return_value=EMPTY_LEAVES)
    def test_daily_wage_uses_summary_counts(self, *_mocks):
        self._activate(wage_type="daily", wage=500.0)
        summary = {
            "present": 18,
            "paid_leave": 2,
            "unpaid_leave": 1,
            "absent": 0,
            "week_off": 4,
            "holiday": 2,
        }
        data = compute_salary_on_period(
            self.employee, self.start, self.end, month_summary=summary
        )
        self.assertEqual(data["paid_days"], 26.0)
        self.assertEqual(data["unpaid_days"], 1)
        self.assertEqual(data["basic_pay"], 26 * 500.0 - 1 * 500.0)
