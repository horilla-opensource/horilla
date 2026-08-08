"""Shared helpers for leave unit tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from leave.models import LeaveType


def _make_leave_type(**kwargs):
    """
    LeaveType stand-in for unit tests (no DB).

    Real LeaveType instances cannot stub ``conditions`` — Django M2M
    descriptors always intercept attribute access. Bind the real payment
    helpers onto a SimpleNamespace instead.
    """
    conditions = MagicMock()
    conditions.all.return_value = []
    lt = SimpleNamespace(
        pk=1,
        id=1,
        name=kwargs.get("name", "Test Leave"),
        payment=kwargs.get("payment", "paid"),
        payment_type=kwargs.get("payment_type", "paid"),
        payment_percentage=kwargs.get("payment_percentage", None),
        conditions=conditions,
    )
    lt.get_payment_percentage = LeaveType.get_payment_percentage.__get__(lt, LeaveType)
    lt.payment_type_display = LeaveType.payment_type_display.__get__(lt, LeaveType)
    return lt


def _make_employee(**kwargs):
    emp = MagicMock()
    emp.id = kwargs.get("id", 1)
    emp.gender = kwargs.get("gender", "male")
    emp.marital_status = kwargs.get("marital_status", "single")
    emp.country = kwargs.get("country", "")
    emp.get_full_name.return_value = kwargs.get("name", "Test Employee")
    return emp
