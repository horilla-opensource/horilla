"""Tests for LeaveType payment type / percentage helpers."""

from decimal import Decimal

from django.test import TestCase

from leave.models import PAYMENT_TYPE
from leave.tests.helpers import _make_leave_type


class PaymentTypeChoicesTest(TestCase):
    def test_payment_type_choices_exist(self):
        keys = [k for k, _ in PAYMENT_TYPE]
        self.assertIn("paid", keys)
        self.assertIn("unpaid", keys)
        self.assertIn("custom", keys)


class LeaveTypeGetPaymentPercentageTest(TestCase):
    def _lt(self, **kw):
        return _make_leave_type(**kw)

    def test_paid_returns_100(self):
        lt = self._lt(payment_type="paid")
        self.assertEqual(lt.get_payment_percentage(), 100.0)

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
    def test_paid_display(self):
        lt = _make_leave_type(payment_type="paid")
        self.assertIn("100", lt.payment_type_display())

    def test_unpaid_display(self):
        lt = _make_leave_type(payment_type="unpaid")
        self.assertIn("0", lt.payment_type_display())

    def test_custom_display(self):
        lt = _make_leave_type(payment_type="custom", payment_percentage=Decimal("33"))
        self.assertIn("33", lt.payment_type_display())
