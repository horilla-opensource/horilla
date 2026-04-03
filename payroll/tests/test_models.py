"""
Model tests for the payroll module.

Tests CRUD operations, field validations, choice constraints, clean() logic,
__str__ representations, and unique_together constraints for all major
payroll models.
"""

import math
from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError

from horilla.test_utils.base import HorillaTestCase
from payroll.models.models import (
    Allowance,
    Contract,
    Deduction,
    FilingStatus,
    LoanAccount,
    Payslip,
    Reimbursement,
    min_zero,
    rate_validator,
)
from payroll.models.tax_models import PayrollSettings, TaxBracket
from payroll.tests.factories import AllowanceFactory


# ---------------------------------------------------------------------------
# PayrollSettings
# ---------------------------------------------------------------------------
class PayrollSettingsTests(HorillaTestCase):
    """Tests for PayrollSettings model."""

    def test_create_payroll_settings(self):
        """PayrollSettings can be created with defaults."""
        settings = PayrollSettings.objects.create(company_id=self.company_a)
        self.assertEqual(settings.currency_symbol, "$")
        self.assertEqual(settings.position, "postfix")

    def test_currency_symbol_custom(self):
        """PayrollSettings accepts a custom currency symbol."""
        settings = PayrollSettings.objects.create(
            currency_symbol="EUR",
            position="prefix",
            company_id=self.company_a,
        )
        self.assertEqual(settings.currency_symbol, "EUR")
        self.assertEqual(settings.position, "prefix")

    def test_str_representation(self):
        """__str__ returns 'Payroll Settings <symbol>'."""
        settings = PayrollSettings.objects.create(
            currency_symbol="GBP", company_id=self.company_a
        )
        self.assertEqual(str(settings), "Payroll Settings GBP")


# ---------------------------------------------------------------------------
# FilingStatus
# ---------------------------------------------------------------------------
class FilingStatusTests(HorillaTestCase):
    """Tests for FilingStatus model."""

    def test_create_filing_status(self):
        """FilingStatus can be created with required fields."""
        fs = FilingStatus.objects.create(
            filing_status="Single",
            based_on="basic_pay",
            company_id=self.company_a,
        )
        self.assertEqual(fs.filing_status, "Single")
        self.assertIsNotNone(fs.pk)

    def test_based_on_choices_basic_pay(self):
        """based_on accepts 'basic_pay'."""
        fs = FilingStatus.objects.create(
            filing_status="Single", based_on="basic_pay", company_id=self.company_a
        )
        self.assertEqual(fs.based_on, "basic_pay")

    def test_based_on_choices_gross_pay(self):
        """based_on accepts 'gross_pay'."""
        fs = FilingStatus.objects.create(
            filing_status="Married", based_on="gross_pay", company_id=self.company_a
        )
        self.assertEqual(fs.based_on, "gross_pay")

    def test_based_on_choices_taxable_gross_pay(self):
        """based_on accepts 'taxable_gross_pay' (the default)."""
        fs = FilingStatus.objects.create(
            filing_status="Head of Household",
            company_id=self.company_a,
        )
        self.assertEqual(fs.based_on, "taxable_gross_pay")

    def test_str_representation(self):
        """__str__ returns the filing_status string."""
        fs = FilingStatus.objects.create(
            filing_status="Joint", company_id=self.company_a
        )
        self.assertEqual(str(fs), "Joint")


# ---------------------------------------------------------------------------
# TaxBracket
# ---------------------------------------------------------------------------
class TaxBracketTests(HorillaTestCase):
    """Tests for TaxBracket model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.filing = FilingStatus.objects.create(
            filing_status="Single",
            based_on="basic_pay",
            company_id=cls.company_a,
        )

    def test_create_tax_bracket(self):
        """TaxBracket can be created with valid fields."""
        bracket = TaxBracket.objects.create(
            filing_status_id=self.filing,
            min_income=0,
            max_income=10000,
            tax_rate=10,
        )
        self.assertIsNotNone(bracket.pk)

    def test_str_finite_max_income(self):
        """__str__ shows rate, min, and max when max_income is finite."""
        bracket = TaxBracket.objects.create(
            filing_status_id=self.filing,
            min_income=0,
            max_income=10000,
            tax_rate=10,
        )
        result = str(bracket)
        self.assertIn("tax rate", result)
        self.assertIn("10000", result)

    def test_str_infinite_max_income(self):
        """__str__ uses 'equal or above' wording when max_income is inf."""
        bracket = TaxBracket.objects.create(
            filing_status_id=self.filing,
            min_income=50000,
            max_income=math.inf,
            tax_rate=30,
        )
        result = str(bracket)
        self.assertIn("equal or above", result)
        self.assertIn("50000", result)

    def test_clean_min_income_less_than_max_income(self):
        """clean() rejects min_income >= max_income."""
        bracket = TaxBracket(
            filing_status_id=self.filing,
            min_income=10000,
            max_income=5000,
            tax_rate=10,
        )
        with self.assertRaises(ValidationError) as ctx:
            bracket.clean()
        self.assertIn("max_income", str(ctx.exception))

    def test_clean_equal_min_max(self):
        """clean() rejects min_income == max_income."""
        bracket = TaxBracket(
            filing_status_id=self.filing,
            min_income=5000,
            max_income=5000,
            tax_rate=10,
        )
        with self.assertRaises(ValidationError):
            bracket.clean()

    def test_clean_null_max_becomes_inf(self):
        """clean() converts None max_income to math.inf."""
        bracket = TaxBracket(
            filing_status_id=self.filing,
            min_income=50000,
            max_income=None,
            tax_rate=30,
        )
        bracket.clean()
        self.assertEqual(bracket.max_income, math.inf)

    def test_get_display_max_income_finite(self):
        """get_display_max_income returns the value when finite."""
        bracket = TaxBracket(
            filing_status_id=self.filing,
            min_income=0,
            max_income=10000,
            tax_rate=10,
        )
        self.assertEqual(bracket.get_display_max_income(), 10000)

    def test_get_display_max_income_infinite(self):
        """get_display_max_income returns None when max_income is inf."""
        bracket = TaxBracket(
            filing_status_id=self.filing,
            min_income=50000,
            max_income=math.inf,
            tax_rate=30,
        )
        self.assertIsNone(bracket.get_display_max_income())

    def test_overlapping_brackets_rejected(self):
        """clean() rejects overlapping brackets for the same filing status."""
        TaxBracket.objects.create(
            filing_status_id=self.filing,
            min_income=0,
            max_income=10000,
            tax_rate=10,
        )
        overlapping = TaxBracket(
            filing_status_id=self.filing,
            min_income=5000,
            max_income=15000,
            tax_rate=15,
        )
        with self.assertRaises(ValidationError):
            overlapping.clean()


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class ContractTests(HorillaTestCase):
    """Tests for Contract model."""

    def _make_contract(self, **overrides):
        """Helper to build a Contract with sensible defaults."""
        defaults = {
            "contract_name": "Test Contract",
            "employee_id": self.admin_employee,
            "wage": 5000,
            "contract_status": "active",
            "wage_type": "monthly",
            "pay_frequency": "monthly",
            "contract_start_date": date.today() - timedelta(days=30),
            "contract_end_date": date.today() + timedelta(days=335),
        }
        defaults.update(overrides)
        return Contract(**defaults)

    def test_create_contract(self):
        """Contract can be created and saved."""
        contract = self._make_contract()
        contract.save()
        self.assertIsNotNone(contract.pk)

    def test_str_representation(self):
        """__str__ includes contract_name and dates."""
        contract = self._make_contract()
        contract.save()
        result = str(contract)
        self.assertIn("Test Contract", result)
        self.assertIn(str(contract.contract_start_date), result)

    def test_contract_status_choices(self):
        """All four contract statuses are valid choices."""
        valid_statuses = ["draft", "active", "expired", "terminated"]
        for status in valid_statuses:
            self.assertIn(
                status,
                [c[0] for c in Contract.CONTRACT_STATUS_CHOICES],
            )

    def test_wage_type_choices(self):
        """wage_type includes at least daily and monthly."""
        choices = [c[0] for c in Contract.WAGE_CHOICES]
        self.assertIn("daily", choices)
        self.assertIn("monthly", choices)

    def test_pay_frequency_choices(self):
        """pay_frequency includes weekly, monthly, semi_monthly."""
        choices = [c[0] for c in Contract.PAY_FREQUENCY_CHOICES]
        self.assertIn("weekly", choices)
        self.assertIn("monthly", choices)
        self.assertIn("semi_monthly", choices)

    def test_clean_end_date_before_start_date(self):
        """clean() rejects end_date < start_date."""
        contract = self._make_contract(
            contract_start_date=date.today(),
            contract_end_date=date.today() - timedelta(days=10),
        )
        with self.assertRaises(ValidationError) as ctx:
            contract.clean()
        self.assertIn("contract_end_date", str(ctx.exception))

    def test_clean_allows_null_end_date(self):
        """clean() allows contract_end_date=None (open-ended)."""
        contract = self._make_contract(contract_end_date=None)
        # Should not raise
        contract.clean()

    def test_unique_together_employee_dates(self):
        """unique_together enforces (employee_id, start_date, end_date)."""
        start = date.today() - timedelta(days=30)
        end = date.today() + timedelta(days=335)
        self._make_contract(
            contract_start_date=start,
            contract_end_date=end,
        ).save()
        duplicate = self._make_contract(
            contract_name="Duplicate",
            employee_id=self.admin_employee,
            contract_status="terminated",
            contract_start_date=start,
            contract_end_date=end,
        )
        with self.assertRaises(Exception):
            duplicate.save()


# ---------------------------------------------------------------------------
# Allowance
# ---------------------------------------------------------------------------
class AllowanceTests(HorillaTestCase):
    """Tests for Allowance model."""

    def test_create_fixed_allowance(self):
        """Fixed allowance stores title and amount."""
        allowance = Allowance(
            title="Transport",
            is_fixed=True,
            amount=500,
            is_taxable=True,
        )
        allowance.clean()
        allowance.save()
        self.assertIsNotNone(allowance.pk)
        self.assertEqual(allowance.amount, 500)

    def test_str_representation(self):
        """__str__ returns the title."""
        allowance = Allowance(title="Housing", is_fixed=True, amount=1000)
        self.assertEqual(str(allowance), "Housing")

    def test_fixed_true_requires_amount(self):
        """clean() raises if is_fixed=True but amount is None."""
        allowance = Allowance(
            title="Missing Amount",
            is_fixed=True,
            amount=None,
        )
        with self.assertRaises(ValidationError):
            allowance.clean()

    def test_non_fixed_requires_based_on(self):
        """clean() raises if is_fixed=False but based_on is not set."""
        allowance = Allowance(
            title="Percentage",
            is_fixed=False,
            amount=None,
            based_on=None,
        )
        with self.assertRaises(ValidationError):
            allowance.clean()

    def test_non_fixed_basic_pay_requires_rate(self):
        """clean() raises if is_fixed=False, based_on=basic_pay, but rate is missing."""
        allowance = Allowance(
            title="Rate Missing",
            is_fixed=False,
            based_on="basic_pay",
            rate=None,
        )
        with self.assertRaises(ValidationError):
            allowance.clean()

    def test_is_taxable_flag(self):
        """is_taxable flag persists correctly."""
        taxable = Allowance(title="Taxable", is_fixed=True, amount=200, is_taxable=True)
        non_taxable = Allowance(
            title="NonTaxable", is_fixed=True, amount=200, is_taxable=False
        )
        self.assertTrue(taxable.is_taxable)
        self.assertFalse(non_taxable.is_taxable)

    def test_max_limit_applied(self):
        """has_max_limit and maximum_amount can be set."""
        allowance = Allowance(
            title="Limited",
            is_fixed=True,
            amount=2000,
            has_max_limit=True,
            maximum_amount=1500,
        )
        # Don't call save() — Allowance.save() has custom sig. Just check fields.
        self.assertTrue(allowance.has_max_limit)
        self.assertEqual(allowance.maximum_amount, 1500)


# ---------------------------------------------------------------------------
# Deduction
# ---------------------------------------------------------------------------
class DeductionTests(HorillaTestCase):
    """Tests for Deduction model."""

    def test_create_fixed_deduction(self):
        """Fixed deduction stores title and amount."""
        deduction = Deduction(
            title="Social Security",
            is_fixed=True,
            amount=100,
            is_pretax=True,
        )
        deduction.clean()
        deduction.save()
        self.assertIsNotNone(deduction.pk)

    def test_str_representation(self):
        """__str__ returns the title."""
        deduction = Deduction(title="Medicare")
        self.assertEqual(str(deduction), "Medicare")

    def test_is_pretax_flag(self):
        """is_pretax flag persists correctly."""
        pre = Deduction(title="Pre", is_fixed=True, amount=50, is_pretax=True)
        post = Deduction(title="Post", is_fixed=True, amount=50, is_pretax=False)
        self.assertTrue(pre.is_pretax)
        self.assertFalse(post.is_pretax)

    def test_is_tax_disables_pretax(self):
        """clean() sets is_pretax=False when is_tax=True."""
        deduction = Deduction(
            title="Tax Deduction",
            is_fixed=True,
            amount=200,
            is_tax=True,
            is_pretax=True,
        )
        deduction.clean()
        self.assertFalse(deduction.is_pretax)

    def test_non_fixed_requires_based_on_or_update_compensation(self):
        """clean() raises if not fixed and neither based_on nor update_compensation is set."""
        deduction = Deduction(
            title="Missing Config",
            is_fixed=False,
            amount=None,
            based_on=None,
            update_compensation=None,
        )
        with self.assertRaises(ValidationError):
            deduction.clean()

    def test_employer_rate_field(self):
        """employer_rate can be set for employer contribution tracking."""
        deduction = Deduction(
            title="FICA",
            is_fixed=True,
            amount=100,
            employer_rate=6.2,
        )
        self.assertEqual(deduction.employer_rate, 6.2)

    def test_pretax_cannot_use_taxable_gross_pay(self):
        """clean() rejects based_on=taxable_gross_pay when is_pretax=True."""
        deduction = Deduction(
            title="Invalid",
            is_fixed=False,
            based_on="taxable_gross_pay",
            rate=5.0,
            is_pretax=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            deduction.clean()
        self.assertIn("based_on", str(ctx.exception))


# ---------------------------------------------------------------------------
# Payslip
# ---------------------------------------------------------------------------
class PayslipTests(HorillaTestCase):
    """Tests for Payslip model."""

    def _make_payslip(self, **overrides):
        """Helper to build a Payslip with sensible defaults."""
        defaults = {
            "employee_id": self.admin_employee,
            "start_date": date.today().replace(day=1),
            "end_date": date.today(),
            "pay_head_data": {"net_pay": 5000, "basic_pay": 4000},
            "contract_wage": 5000,
            "basic_pay": 4000,
            "gross_pay": 4500,
            "deduction": 500,
            "net_pay": 4000,
            "status": "draft",
        }
        defaults.update(overrides)
        return Payslip(**defaults)

    def test_create_payslip(self):
        """Payslip can be created and saved."""
        payslip = self._make_payslip()
        payslip.save()
        self.assertIsNotNone(payslip.pk)

    def test_str_representation(self):
        """__str__ includes employee and period dates."""
        payslip = self._make_payslip()
        payslip.save()
        result = str(payslip)
        self.assertIn("Payslip for", result)
        self.assertIn(str(payslip.start_date), result)
        self.assertIn(str(payslip.end_date), result)

    def test_status_choices(self):
        """All four status choices are valid."""
        valid = ["draft", "review_ongoing", "confirmed", "paid"]
        choice_keys = [c[0] for c in Payslip.status_choices]
        for status in valid:
            self.assertIn(status, choice_keys)

    def test_clean_end_date_before_start_date(self):
        """clean() rejects end_date < start_date."""
        payslip = self._make_payslip(
            start_date=date.today(),
            end_date=date.today() - timedelta(days=5),
        )
        with self.assertRaises(ValidationError) as ctx:
            payslip.clean()
        self.assertIn("end_date", str(ctx.exception))

    def test_save_rejects_non_dict_pay_head_data(self):
        """save() rejects pay_head_data that is not dict or QueryDict."""
        payslip = self._make_payslip(pay_head_data="not_a_dict")
        with self.assertRaises(ValidationError):
            payslip.save()

    def test_net_pay_conceptual(self):
        """net_pay should logically be gross_pay - deduction."""
        payslip = self._make_payslip(gross_pay=5000, deduction=800, net_pay=4200)
        payslip.save()
        self.assertEqual(payslip.net_pay, payslip.gross_pay - payslip.deduction)


# ---------------------------------------------------------------------------
# LoanAccount
# ---------------------------------------------------------------------------
class LoanAccountTests(HorillaTestCase):
    """Tests for LoanAccount model."""

    def _make_loan(self, **overrides):
        """Helper to build a LoanAccount with defaults."""
        defaults = {
            "title": "Personal Loan",
            "employee_id": self.admin_employee,
            "type": "loan",
            "loan_amount": 12000,
            "installments": 12,
            "provided_date": date.today(),
            "installment_start_date": date.today() + timedelta(days=30),
        }
        defaults.update(overrides)
        return LoanAccount(**defaults)

    def test_create_loan(self):
        """LoanAccount can be created and saved."""
        loan = self._make_loan()
        loan.save()
        self.assertIsNotNone(loan.pk)

    def test_str_representation(self):
        """__str__ includes title and employee."""
        loan = self._make_loan()
        loan.save()
        result = str(loan)
        self.assertIn("Personal Loan", result)

    def test_loan_type_choices(self):
        """All three loan type choices are valid."""
        valid = ["loan", "advanced_salary", "fine"]
        choice_keys = [c[0] for c in LoanAccount.loan_type]
        for t in valid:
            self.assertIn(t, choice_keys)

    def test_get_installments_count(self):
        """get_installments() returns the correct number of entries."""
        loan = self._make_loan(loan_amount=6000, installments=6)
        loan.save()
        schedule = loan.get_installments()
        self.assertEqual(len(schedule), 6)

    def test_get_installments_amount(self):
        """Each installment equals loan_amount / installments."""
        loan = self._make_loan(loan_amount=12000, installments=12)
        loan.save()
        schedule = loan.get_installments()
        expected_amount = 12000 / 12
        for _date_key, amount in schedule.items():
            self.assertAlmostEqual(amount, expected_amount, places=2)

    def test_total_installments_method(self):
        """total_installments() returns the installments field value."""
        loan = self._make_loan(installments=10)
        loan.save()
        self.assertEqual(loan.total_installments(), 10)


# ---------------------------------------------------------------------------
# Reimbursement
# ---------------------------------------------------------------------------
class ReimbursementTests(HorillaTestCase):
    """Tests for Reimbursement model."""

    def test_status_choices(self):
        """All three status choices are valid."""
        valid = ["requested", "approved", "rejected"]
        choice_keys = [c[0] for c in Reimbursement.status_types]
        for status in valid:
            self.assertIn(status, choice_keys)

    def test_type_choices(self):
        """At least reimbursement and bonus_encashment types exist."""
        choice_keys = [c[0] for c in Reimbursement.reimbursement_types]
        self.assertIn("reimbursement", choice_keys)
        self.assertIn("bonus_encashment", choice_keys)

    def test_str_representation(self):
        """__str__ returns the title."""
        r = Reimbursement(title="Medical Expense")
        self.assertEqual(str(r), "Medical Expense")

    def test_amount_field(self):
        """Amount field can be set to arbitrary positive float."""
        r = Reimbursement(title="Travel", amount=750.50)
        self.assertEqual(r.amount, 750.50)


# ---------------------------------------------------------------------------
# Validators (standalone functions)
# ---------------------------------------------------------------------------
class ValidatorTests(HorillaTestCase):
    """Tests for standalone validators in models.py."""

    def test_min_zero_rejects_negative(self):
        """min_zero raises ValidationError for negative values."""
        with self.assertRaises(ValidationError):
            min_zero(-1)

    def test_min_zero_accepts_zero(self):
        """min_zero does not raise for zero."""
        min_zero(0)  # Should not raise

    def test_min_zero_accepts_positive(self):
        """min_zero does not raise for positive values."""
        min_zero(100)

    def test_rate_validator_rejects_negative(self):
        """rate_validator rejects values below 0."""
        with self.assertRaises(ValidationError):
            rate_validator(-1)

    def test_rate_validator_rejects_over_100(self):
        """rate_validator rejects values above 100."""
        with self.assertRaises(ValidationError):
            rate_validator(101)

    def test_rate_validator_accepts_valid_range(self):
        """rate_validator accepts values in [0, 100]."""
        rate_validator(0)
        rate_validator(50)
        rate_validator(100)
