"""Tests for AvailableLeave carryforward / pre_save_processing."""

from django.test import TestCase


class AvailableLeaveCarryforwardTests(TestCase):
    def setUp(self):
        from horilla.testkit import make_company, make_employee
        from leave.models import AvailableLeave, LeaveType

        company = make_company("Leave Carry Co")
        self.employee = make_employee(company=company, email="carry@test.horilla")
        self.LeaveType = LeaveType
        self.AvailableLeave = AvailableLeave

    def test_carryforward_capped_at_max(self):
        lt = self.LeaveType.objects.create(
            name="Annual Carry Cap",
            total_days=12,
            carryforward_type="carryforward",
            carryforward_max=5,
        )
        avail = self.AvailableLeave.objects.create(
            employee_id=self.employee,
            leave_type_id=lt,
            available_days=10,
            carryforward_days=0,
            total_leave_days=10,
        )
        # Ensure total reflects pre-reset balance used by update_carryforward().
        avail.total_leave_days = 10
        avail.update_carryforward()
        self.assertEqual(avail.carryforward_days, 5)
        self.assertEqual(avail.available_days, 12)

    def test_no_carryforward_resets_available_only(self):
        lt = self.LeaveType.objects.create(
            name="Sick No Carry",
            total_days=8,
            carryforward_type="no carryforward",
            carryforward_max=5,
        )
        avail = self.AvailableLeave.objects.create(
            employee_id=self.employee,
            leave_type_id=lt,
            available_days=2,
            carryforward_days=4,
            total_leave_days=6,
        )
        avail.update_carryforward()
        self.assertEqual(avail.carryforward_days, 4)
        self.assertEqual(avail.available_days, 8)

    def test_pre_save_processing_totals(self):
        lt = self.LeaveType.objects.create(
            name="Casual PreSave",
            total_days=10,
            carryforward_type="no carryforward",
            reset=False,
        )
        avail = self.AvailableLeave(
            employee_id=self.employee,
            leave_type_id=lt,
            available_days=10,
            carryforward_days=-2,
        )
        avail.pre_save_processing()
        self.assertEqual(avail.total_leave_days, 8.0)
        self.assertEqual(avail.carryforward_days, 0.0)
