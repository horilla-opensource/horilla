"""
Tests for LeaveType payment type handling, conditions, and assignment validation.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from leave.models import PAYMENT_TYPE, LeaveType, LeaveTypeCondition
from leave.services import evaluate_leave_type_conditions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_leave_type(**kwargs):
    lt = LeaveType.__new__(LeaveType)
    lt.pk = 1
    lt.id = 1
    lt.name = kwargs.get("name", "Test Leave")
    lt.payment = kwargs.get("payment", "paid")
    lt.payment_type = kwargs.get("payment_type", "fully_paid")
    lt.payment_percentage = kwargs.get("payment_percentage", None)
    # Stub conditions as empty queryset by default
    lt.conditions = MagicMock()
    lt.conditions.all.return_value = []
    return lt


def _make_employee(**kwargs):
    emp = MagicMock()
    emp.id = kwargs.get("id", 1)
    emp.gender = kwargs.get("gender", "male")
    emp.marital_status = kwargs.get("marital_status", "single")
    emp.country = kwargs.get("country", "")
    emp.get_full_name.return_value = kwargs.get("name", "Test Employee")
    return emp


# ---------------------------------------------------------------------------
# Payment type / percentage tests
# ---------------------------------------------------------------------------


class PaymentTypeChoicesTest(TestCase):
    def test_payment_type_choices_exist(self):
        keys = [k for k, _ in PAYMENT_TYPE]
        self.assertIn("fully_paid", keys)
        self.assertIn("half_paid", keys)
        self.assertIn("unpaid", keys)
        self.assertIn("custom", keys)


class LeaveTypeGetPaymentPercentageTest(TestCase):
    def _lt(self, **kw):
        return _make_leave_type(**kw)

    def test_fully_paid_returns_100(self):
        lt = self._lt(payment_type="fully_paid")
        self.assertEqual(lt.get_payment_percentage(), 100.0)

    def test_half_paid_returns_50(self):
        lt = self._lt(payment_type="half_paid")
        self.assertEqual(lt.get_payment_percentage(), 50.0)

    def test_unpaid_returns_0(self):
        lt = self._lt(payment_type="unpaid")
        self.assertEqual(lt.get_payment_percentage(), 0.0)

    def test_custom_uses_payment_percentage(self):
        lt = self._lt(payment_type="custom", payment_percentage=Decimal("75.00"))
        self.assertEqual(lt.get_payment_percentage(), 75.0)

    def test_custom_with_none_percentage_returns_0(self):
        lt = self._lt(payment_type="custom", payment_percentage=None)
        self.assertEqual(lt.get_payment_percentage(), 0.0)

    def test_backward_compat_paid(self):
        lt = self._lt(payment_type=None, payment="paid")
        self.assertEqual(lt.get_payment_percentage(), 100.0)

    def test_backward_compat_unpaid(self):
        lt = self._lt(payment_type=None, payment="unpaid")
        self.assertEqual(lt.get_payment_percentage(), 0.0)


class LeaveTypePaymentTypeDisplayTest(TestCase):
    def test_fully_paid_display(self):
        lt = _make_leave_type(payment_type="fully_paid")
        self.assertIn("100", lt.payment_type_display())

    def test_half_paid_display(self):
        lt = _make_leave_type(payment_type="half_paid")
        self.assertIn("50", lt.payment_type_display())

    def test_custom_display(self):
        lt = _make_leave_type(payment_type="custom", payment_percentage=Decimal("33"))
        self.assertIn("33", lt.payment_type_display())


# ---------------------------------------------------------------------------
# LeaveTypeCondition model tests
# ---------------------------------------------------------------------------


class LeaveTypeConditionModelTest(TestCase):
    def test_str_with_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.condition_type = "gender"
        cond.value = "female"
        self.assertIn("female", str(cond))
        self.assertIn("Gender", str(cond))

    def test_str_without_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.condition_type = "once_per_employment"
        cond.value = None
        self.assertIn("Once Per Employment", str(cond))

    def test_clean_raises_when_value_missing_for_gender(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.pk = None
        cond.condition_type = "gender"
        cond.value = ""
        with self.assertRaises(ValidationError):
            cond.clean()

    def test_clean_passes_for_once_per_employment_without_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.pk = None
        cond.condition_type = "once_per_employment"
        cond.value = None
        # Should not raise
        cond.clean()


# ---------------------------------------------------------------------------
# evaluate_leave_type_conditions service tests
# ---------------------------------------------------------------------------


class GenderConditionTest(TestCase):
    def _gender_condition(self, value):
        cond = MagicMock()
        cond.condition_type = "gender"
        cond.value = value
        return cond

    def test_matching_gender_passes(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("female")]
        employee = _make_employee(gender="female")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)
        self.assertIsNone(msg)

    def test_wrong_gender_fails(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("female")]
        employee = _make_employee(gender="male")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        self.assertIn("female", str(msg))

    def test_case_insensitive_gender_match(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("Female")]
        employee = _make_employee(gender="female")
        is_eligible, _ = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    def test_maternity_female_only(self):
        lt = _make_leave_type(name="Maternity Leave")
        lt.conditions.all.return_value = [self._gender_condition("female")]
        male = _make_employee(gender="male")
        is_eligible, msg = evaluate_leave_type_conditions(lt, male)
        self.assertFalse(is_eligible)

    def test_paternity_male_only(self):
        lt = _make_leave_type(name="Paternity Leave")
        lt.conditions.all.return_value = [self._gender_condition("male")]
        female = _make_employee(gender="female")
        is_eligible, msg = evaluate_leave_type_conditions(lt, female)
        self.assertFalse(is_eligible)


class OncePerEmploymentConditionTest(TestCase):
    def _once_condition(self):
        cond = MagicMock()
        cond.condition_type = "once_per_employment"
        cond.value = None
        return cond

    @patch("leave.services.AvailableLeave")
    def test_not_yet_assigned_passes(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._once_condition()]
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    @patch("leave.services.AvailableLeave")
    def test_already_assigned_blocks(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = True
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._once_condition()]
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        self.assertIn("once", str(msg).lower())


class MaritalStatusConditionTest(TestCase):
    def _marital_condition(self, value):
        cond = MagicMock()
        cond.condition_type = "marital_status"
        cond.value = value
        return cond

    def test_matching_marital_passes(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._marital_condition("married")]
        employee = _make_employee(marital_status="married")
        is_eligible, _ = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    def test_wrong_marital_fails(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._marital_condition("married")]
        employee = _make_employee(marital_status="single")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)


class NoConditionsTest(TestCase):
    def test_no_conditions_always_eligible(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = []
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)
        self.assertIsNone(msg)


class MultipleConditionsTest(TestCase):
    """When multiple conditions are set, all must pass."""

    @patch("leave.services.AvailableLeave")
    def test_all_pass(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False

        gender_cond = MagicMock()
        gender_cond.condition_type = "gender"
        gender_cond.value = "female"

        once_cond = MagicMock()
        once_cond.condition_type = "once_per_employment"
        once_cond.value = None

        lt = _make_leave_type()
        lt.conditions.all.return_value = [gender_cond, once_cond]
        employee = _make_employee(gender="female")

        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    @patch("leave.services.AvailableLeave")
    def test_first_fails_short_circuits(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False

        gender_cond = MagicMock()
        gender_cond.condition_type = "gender"
        gender_cond.value = "female"

        once_cond = MagicMock()
        once_cond.condition_type = "once_per_employment"
        once_cond.value = None

        lt = _make_leave_type()
        lt.conditions.all.return_value = [gender_cond, once_cond]
        employee = _make_employee(gender="male")  # fails gender check

        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        # once_per_employment filter should NOT have been called
        MockAL.objects.filter.assert_not_called()
