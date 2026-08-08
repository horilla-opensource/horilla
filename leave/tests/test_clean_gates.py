"""Tests for LeaveRequest.clean validation gates."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase


class LeaveRequestCleanGateTests(TestCase):
    def setUp(self):
        from horilla.testkit import make_company, make_employee
        from leave.models import LeaveType

        company = make_company("Leave Clean Co")
        self.employee = make_employee(company=company, email="clean@test.horilla")
        self.leave_type = LeaveType.objects.create(
            name="Casual Clean Gate",
            total_days=10,
        )

    def test_unassigned_leave_type_rejected(self):
        from leave.models import LeaveRequest

        today = date.today()
        req = LeaveRequest(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=1),
            start_date_breakdown="full_day",
            end_date_breakdown="full_day",
            description="not assigned",
        )
        with self.assertRaises(ValidationError) as ctx:
            req.clean()
        self.assertIn("not assigned", str(ctx.exception).lower())

    def test_end_before_start_rejected(self):
        from leave.models import AvailableLeave, LeaveRequest

        AvailableLeave.objects.create(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            available_days=20,
            carryforward_days=0,
            total_leave_days=20,
        )
        today = date.today()
        req = LeaveRequest(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=1),
            start_date_breakdown="full_day",
            end_date_breakdown="full_day",
            description="bad dates",
        )
        with self.assertRaises(ValidationError) as ctx:
            req.clean()
        self.assertIn("end date", str(ctx.exception).lower())
