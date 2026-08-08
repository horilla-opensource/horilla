"""Tests for leave allocation approve + related clean gates."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase


class LeaveAllocationApproveTests(TestCase):
    def setUp(self):
        from horilla.testkit import make_company, make_employee
        from leave.models import LeaveType

        company = make_company("Alloc Co")
        self.employee = make_employee(company=company, email="alloc@test.horilla")
        self.leave_type = LeaveType.objects.create(
            name="Allocation Leave Type",
            total_days=10,
        )

    def test_allocation_approve_increments_available_days(self):
        from leave.forms import LeaveAllocationBulkForm
        from leave.models import AvailableLeave, LeaveAllocationRequest

        AvailableLeave.objects.create(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            available_days=5,
            carryforward_days=0,
            total_leave_days=5,
        )
        req = LeaveAllocationRequest.objects.create(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            requested_days=3,
            description="need more days",
            status="requested",
        )
        LeaveAllocationBulkForm._approve(object(), req)
        avail = AvailableLeave.objects.get(
            employee_id=self.employee, leave_type_id=self.leave_type
        )
        self.assertEqual(avail.available_days, 8)
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")

    def test_allocation_approve_creates_available_leave_if_missing(self):
        from leave.forms import LeaveAllocationBulkForm
        from leave.models import AvailableLeave, LeaveAllocationRequest

        req = LeaveAllocationRequest.objects.create(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            requested_days=4,
            description="first allocation",
            status="requested",
        )
        LeaveAllocationBulkForm._approve(object(), req)
        avail = AvailableLeave.objects.get(
            employee_id=self.employee, leave_type_id=self.leave_type
        )
        self.assertEqual(avail.available_days, 4)
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")

    def test_breakdown_mismatch_rejected(self):
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
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=2),
            start_date_breakdown="full_day",
            end_date_breakdown="first_half",
            description="mismatch",
        )
        with self.assertRaises(ValidationError) as ctx:
            req.clean()
        self.assertIn("breakdown", str(ctx.exception).lower())
