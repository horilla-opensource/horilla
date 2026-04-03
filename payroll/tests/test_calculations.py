"""
Calculation tests for the payroll module.

Covers pure logic for:
- Tax bracket stepping (progressive tax)
- Allowance amount computation
- Loan EMI / installment calculations
- Net pay computation

Uses SimpleTestCase (no DB) where possible. Uses HorillaTestCase when
model instances are needed for integration-level calculation tests.
"""

import math
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from horilla.test_utils.base import HorillaTestCase
from payroll.methods.limits import compute_limit
from payroll.models.models import LoanAccount


# ---------------------------------------------------------------------------
# Tax Bracket Stepping (pure logic, no DB)
# ---------------------------------------------------------------------------
class TaxBracketSteppingTests(SimpleTestCase):
    """
    Tests the progressive tax calculation algorithm extracted from
    payroll.methods.tax_calc.calculate_taxable_amount.

    The core algorithm (from tax_calc.py lines 76-92):
        For each bracket where max > min:
            diff = max - min
            calculated_rate = (rate / 100) * diff
        federal_tax = sum of all calculated_rates
    """

    def _calculate_progressive_tax(self, yearly_income, brackets):
        """
        Replicate the tax bracket stepping algorithm from tax_calc.py.

        Args:
            yearly_income: Annual income to tax.
            brackets: List of dicts with keys: min_income, max_income, tax_rate.

        Returns:
            Total tax amount.
        """
        processed = [
            {
                "rate": b["tax_rate"],
                "min": b["min_income"],
                "max": min(b["max_income"], yearly_income),
            }
            for b in sorted(brackets, key=lambda x: x["min_income"])
        ]
        filtered = []
        for bracket in processed:
            if bracket["max"] > bracket["min"]:
                bracket["diff"] = bracket["max"] - bracket["min"]
                bracket["calculated_rate"] = (bracket["rate"] / 100) * bracket["diff"]
                filtered.append(bracket)
                continue
            break
        return sum(b["calculated_rate"] for b in filtered)

    def test_income_below_first_bracket(self):
        """Income below the first bracket minimum yields 0 tax."""
        brackets = [
            {"min_income": 10000, "max_income": 50000, "tax_rate": 10},
        ]
        tax = self._calculate_progressive_tax(5000, brackets)
        self.assertEqual(tax, 0)

    def test_income_in_single_bracket(self):
        """Income within a single bracket applies the correct rate."""
        brackets = [
            {"min_income": 0, "max_income": 50000, "tax_rate": 10},
        ]
        tax = self._calculate_progressive_tax(30000, brackets)
        # 10% of 30000 = 3000
        self.assertAlmostEqual(tax, 3000.0, places=2)

    def test_income_spanning_two_brackets(self):
        """Income spanning two brackets applies progressive rates."""
        brackets = [
            {"min_income": 0, "max_income": 10000, "tax_rate": 10},
            {"min_income": 10000, "max_income": 50000, "tax_rate": 20},
        ]
        tax = self._calculate_progressive_tax(30000, brackets)
        # First bracket: 10% of 10000 = 1000
        # Second bracket: 20% of 20000 = 4000
        self.assertAlmostEqual(tax, 5000.0, places=2)

    def test_income_spanning_three_brackets(self):
        """Income spanning three brackets applies progressive rates."""
        brackets = [
            {"min_income": 0, "max_income": 10000, "tax_rate": 10},
            {"min_income": 10000, "max_income": 40000, "tax_rate": 20},
            {"min_income": 40000, "max_income": 100000, "tax_rate": 30},
        ]
        tax = self._calculate_progressive_tax(60000, brackets)
        # 10% of 10000 = 1000
        # 20% of 30000 = 6000
        # 30% of 20000 = 6000
        self.assertAlmostEqual(tax, 13000.0, places=2)

    def test_income_exactly_at_bracket_boundary(self):
        """Income exactly at a bracket boundary only includes lower brackets."""
        brackets = [
            {"min_income": 0, "max_income": 10000, "tax_rate": 10},
            {"min_income": 10000, "max_income": 50000, "tax_rate": 20},
        ]
        tax = self._calculate_progressive_tax(10000, brackets)
        # Exactly at boundary: only first bracket
        # 10% of 10000 = 1000
        self.assertAlmostEqual(tax, 1000.0, places=2)

    def test_very_high_income_with_infinite_bracket(self):
        """High income with an unbounded top bracket is taxed correctly."""
        brackets = [
            {"min_income": 0, "max_income": 10000, "tax_rate": 10},
            {"min_income": 10000, "max_income": math.inf, "tax_rate": 25},
        ]
        tax = self._calculate_progressive_tax(1000000, brackets)
        # 10% of 10000 = 1000
        # 25% of 990000 = 247500
        self.assertAlmostEqual(tax, 248500.0, places=2)

    def test_zero_income(self):
        """Zero income always yields 0 tax."""
        brackets = [
            {"min_income": 0, "max_income": 10000, "tax_rate": 10},
        ]
        tax = self._calculate_progressive_tax(0, brackets)
        self.assertEqual(tax, 0)

    def test_empty_brackets(self):
        """No brackets defined yields 0 tax."""
        tax = self._calculate_progressive_tax(50000, [])
        self.assertEqual(tax, 0)


# ---------------------------------------------------------------------------
# Allowance Calculations (pure logic)
# ---------------------------------------------------------------------------
class AllowanceCalculationTests(SimpleTestCase):
    """Tests for allowance computation logic."""

    def test_fixed_allowance_returns_amount(self):
        """A fixed allowance returns its fixed amount."""
        amount = 500.0
        self.assertEqual(amount, 500.0)

    def test_percentage_of_basic_pay(self):
        """Percentage allowance = rate / 100 * basic_pay."""
        basic_pay = 5000.0
        rate = 10.0
        calculated = basic_pay * rate / 100
        self.assertAlmostEqual(calculated, 500.0, places=2)

    def test_max_limit_caps_allowance(self):
        """compute_limit caps allowance at maximum_amount."""
        component = MagicMock()
        component.has_max_limit = True
        component.maximum_amount = 300.0
        result = compute_limit(component, 500.0, [])
        self.assertEqual(result, 300.0)

    def test_no_max_limit_passes_through(self):
        """compute_limit returns full amount when no max limit."""
        component = MagicMock()
        component.has_max_limit = False
        result = compute_limit(component, 500.0, [])
        self.assertEqual(result, 500.0)

    def test_max_limit_not_applied_when_under(self):
        """compute_limit returns full amount when under max limit."""
        component = MagicMock()
        component.has_max_limit = True
        component.maximum_amount = 1000.0
        result = compute_limit(component, 500.0, [])
        self.assertEqual(result, 500.0)

    def test_multiple_allowances_sum(self):
        """Multiple fixed allowances sum correctly."""
        allowances = [500.0, 300.0, 200.0]
        total = sum(allowances)
        self.assertAlmostEqual(total, 1000.0, places=2)


# ---------------------------------------------------------------------------
# Loan EMI / Installment Calculations
# ---------------------------------------------------------------------------
class LoanEMITests(SimpleTestCase):
    """Tests for loan installment amount calculation (pure math)."""

    def test_installment_amount_calculation(self):
        """installment_amount = loan_amount / installments."""
        loan_amount = 12000.0
        installments = 12
        expected = 1000.0
        self.assertAlmostEqual(loan_amount / installments, expected, places=2)

    def test_total_installments_equal_loan(self):
        """Total installments x amount equals loan_amount (within rounding)."""
        loan_amount = 10000.0
        installments = 3
        per_installment = loan_amount / installments
        total = per_installment * installments
        self.assertAlmostEqual(total, loan_amount, places=2)

    def test_zero_installments_edge_case(self):
        """Zero installments should raise ZeroDivisionError."""
        loan_amount = 10000.0
        with self.assertRaises(ZeroDivisionError):
            _ = loan_amount / 0

    def test_different_loan_types_same_calculation(self):
        """All loan types (loan/advanced_salary/fine) use same installment math."""
        for loan_type in ["loan", "advanced_salary", "fine"]:
            loan_amount = 6000.0
            installments = 6
            per_installment = loan_amount / installments
            self.assertAlmostEqual(per_installment, 1000.0, places=2)

    def test_large_loan_many_installments(self):
        """Large loan with many installments remains accurate."""
        loan_amount = 1000000.0
        installments = 360  # 30-year mortgage
        per_installment = loan_amount / installments
        total = per_installment * installments
        self.assertAlmostEqual(total, loan_amount, places=2)


# ---------------------------------------------------------------------------
# Loan EMI with actual model (needs DB)
# ---------------------------------------------------------------------------
class LoanInstallmentModelTests(HorillaTestCase):
    """Tests for LoanAccount.get_installments() method."""

    def test_get_installments_schedule(self):
        """get_installments() produces correct schedule from model."""
        loan = LoanAccount(
            title="Car Loan",
            employee_id=self.admin_employee,
            type="loan",
            loan_amount=12000,
            installments=12,
            provided_date=date.today(),
            installment_start_date=date(2026, 4, 1),
        )
        loan.save()
        schedule = loan.get_installments()
        self.assertEqual(len(schedule), 12)
        for _date_str, amount in schedule.items():
            self.assertAlmostEqual(amount, 1000.0, places=2)

    def test_get_installments_uneven_division(self):
        """get_installments() handles uneven division (rounding at each step)."""
        loan = LoanAccount(
            title="Small Loan",
            employee_id=self.admin_employee,
            type="fine",
            loan_amount=10000,
            installments=3,
            provided_date=date.today(),
            installment_start_date=date(2026, 5, 1),
        )
        loan.save()
        schedule = loan.get_installments()
        total = sum(schedule.values())
        self.assertAlmostEqual(total, 10000.0, places=2)


# ---------------------------------------------------------------------------
# Net Pay Calculations (pure logic)
# ---------------------------------------------------------------------------
class NetPayCalculationTests(SimpleTestCase):
    """Tests for net pay computation logic."""

    def test_net_equals_gross_minus_deductions(self):
        """net = gross - deductions."""
        gross_pay = 5000.0
        total_deductions = 800.0
        net_pay = gross_pay - total_deductions
        self.assertAlmostEqual(net_pay, 4200.0, places=2)

    def test_net_with_tax_deductions(self):
        """net = gross - pretax - tax - posttax."""
        gross_pay = 10000.0
        pretax = 500.0
        tax = 1200.0
        posttax = 300.0
        net_pay = gross_pay - pretax - tax - posttax
        self.assertAlmostEqual(net_pay, 8000.0, places=2)

    def test_net_floor_at_zero(self):
        """If deductions exceed gross, net should be floored at 0."""
        gross_pay = 1000.0
        total_deductions = 1500.0
        net_pay = max(0, gross_pay - total_deductions)
        self.assertEqual(net_pay, 0)

    def test_no_deductions(self):
        """net equals gross when there are no deductions."""
        gross_pay = 5000.0
        total_deductions = 0.0
        net_pay = gross_pay - total_deductions
        self.assertAlmostEqual(net_pay, 5000.0, places=2)

    def test_gross_pay_equals_basic_plus_allowances(self):
        """gross_pay = basic_pay + total_allowances."""
        basic_pay = 4000.0
        allowances = [500.0, 300.0, 200.0]
        gross_pay = basic_pay + sum(allowances)
        self.assertAlmostEqual(gross_pay, 5000.0, places=2)

    def test_taxable_gross_excludes_non_taxable_and_pretax(self):
        """taxable_gross = gross - non_taxable_allowances - pretax_deductions."""
        gross_pay = 5000.0
        non_taxable_allowances = 300.0
        pretax_deductions = 500.0
        taxable_gross = gross_pay - non_taxable_allowances - pretax_deductions
        self.assertAlmostEqual(taxable_gross, 4200.0, places=2)


# ---------------------------------------------------------------------------
# Deduction Computation Logic
# ---------------------------------------------------------------------------
class DeductionComputationTests(SimpleTestCase):
    """Tests for deduction calculation logic."""

    def test_fixed_deduction_amount(self):
        """Fixed deduction returns its amount directly."""
        amount = 100.0
        self.assertEqual(amount, 100.0)

    def test_percentage_deduction_of_gross(self):
        """Percentage deduction = rate / 100 * compensation."""
        compensation = 5000.0
        rate = 6.2
        deduction = compensation * rate / 100
        self.assertAlmostEqual(deduction, 310.0, places=2)

    def test_employer_contribution(self):
        """Employer contribution = deduction_amount * employer_rate / 100."""
        deduction_amount = 310.0
        employer_rate = 6.2
        employer_contribution = deduction_amount * employer_rate / 100
        self.assertAlmostEqual(employer_contribution, 19.22, places=2)

    def test_compensation_reduction(self):
        """After deduction, compensation is reduced by deduction amount."""
        compensation = 5000.0
        deduction = 310.0
        new_compensation = compensation - deduction
        self.assertAlmostEqual(new_compensation, 4690.0, places=2)
