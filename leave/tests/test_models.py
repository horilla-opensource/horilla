"""
Tests for leave module models.

Covers LeaveType, AvailableLeave, LeaveRequest, LeaveAllocationRequest,
and RestrictLeave with CRUD, validation, and business logic tests.
"""

from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from horilla.test_utils.base import HorillaTestCase
from leave.models import (
    BREAKDOWN,
    CARRYFORWARD_TYPE,
    LEAVE_ALLOCATION_STATUS,
    LEAVE_STATUS,
    PAYMENT,
    RESET_BASED,
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveRequest,
    LeaveType,
    RestrictLeave,
)
from leave.tests.factories import (
    AvailableLeaveFactory,
    LeaveAllocationRequestFactory,
    LeaveRequestFactory,
    LeaveTypeFactory,
    RestrictLeaveFactory,
)


# ---------------------------------------------------------------------------
# LeaveType Tests (~10)
# ---------------------------------------------------------------------------
class LeaveTypeCreateTest(HorillaTestCase):
    """Basic CRUD for LeaveType."""

    def test_create_leave_type(self):
        lt = LeaveTypeFactory(company_id=self.company_a)
        self.assertIsNotNone(lt.pk)
        self.assertEqual(lt.company_id, self.company_a)

    def test_str_representation(self):
        lt = LeaveTypeFactory(name="Annual Leave", company_id=self.company_a)
        self.assertEqual(str(lt), "Annual Leave")

    def test_name_required(self):
        """LeaveType without name should fail at DB level."""
        with self.assertRaises(Exception):
            LeaveType.objects.create(name=None, company_id=self.company_a)

    def test_payment_choices_paid(self):
        lt = LeaveTypeFactory(payment="paid", company_id=self.company_a)
        self.assertEqual(lt.payment, "paid")

    def test_payment_choices_unpaid(self):
        lt = LeaveTypeFactory(payment="unpaid", company_id=self.company_a)
        self.assertEqual(lt.payment, "unpaid")

    def test_payment_default_is_unpaid(self):
        lt = LeaveType.objects.create(name="Test", company_id=self.company_a)
        self.assertEqual(lt.payment, "unpaid")

    def test_reset_based_choices(self):
        valid_values = [choice[0] for choice in RESET_BASED]
        self.assertIn("yearly", valid_values)
        self.assertIn("monthly", valid_values)
        self.assertIn("weekly", valid_values)

    def test_carryforward_type_choices(self):
        valid_values = [choice[0] for choice in CARRYFORWARD_TYPE]
        self.assertIn("no carryforward", valid_values)
        self.assertIn("carryforward", valid_values)
        self.assertIn("carryforward expire", valid_values)

    def test_only_one_compensatory_leave_type_per_company(self):
        """clean() should raise ValidationError if a second compensatory type exists."""
        LeaveTypeFactory(
            name="Comp Leave 1",
            is_compensatory_leave=True,
            company_id=self.company_a,
        )
        lt2 = LeaveTypeFactory(
            name="Comp Leave 2",
            is_compensatory_leave=False,
            company_id=self.company_a,
        )
        lt2.is_compensatory_leave = True
        with self.assertRaises(ValidationError):
            lt2.clean()

    def test_leave_type_next_reset_date_none_when_no_reset(self):
        lt = LeaveTypeFactory(reset=False, company_id=self.company_a)
        self.assertIsNone(lt.leave_type_next_reset_date())

    def test_leave_type_next_reset_date_monthly(self):
        lt = LeaveTypeFactory(
            reset=True,
            reset_based="monthly",
            reset_day="15",
            company_id=self.company_a,
        )
        result = lt.leave_type_next_reset_date()
        self.assertIsNotNone(result)
        # The reset date should be on the 15th of some month
        self.assertEqual(result.day, 15)


# ---------------------------------------------------------------------------
# AvailableLeave Tests (~10)
# ---------------------------------------------------------------------------
class AvailableLeaveCreateTest(HorillaTestCase):
    """CRUD and constraints for AvailableLeave."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leave_type = LeaveTypeFactory(company_id=cls.company_a)

    def test_create_available_leave(self):
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            available_days=15,
        )
        self.assertIsNotNone(al.pk)
        self.assertEqual(al.available_days, 15)

    def test_str_representation(self):
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        self.assertIn(str(self.admin_employee), str(al))
        self.assertIn(str(self.leave_type), str(al))

    def test_unique_together_leave_type_employee(self):
        """Only one AvailableLeave per (leave_type, employee) pair."""
        AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        with self.assertRaises(IntegrityError):
            AvailableLeaveFactory(
                employee_id=self.admin_employee,
                leave_type_id=self.leave_type,
            )

    def test_available_days_default_zero(self):
        al = AvailableLeave(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        self.assertEqual(al.available_days, 0)

    def test_carryforward_days_default_zero(self):
        al = AvailableLeave(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        self.assertEqual(al.carryforward_days, 0)

    def test_total_leave_days_computed_on_save(self):
        """total_leave_days = available_days + carryforward_days (computed in save)."""
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            available_days=10,
        )
        al.carryforward_days = 3
        al.save()
        al.refresh_from_db()
        self.assertEqual(al.total_leave_days, 13.0)

    def test_carryforward_days_not_negative_after_save(self):
        """save() ensures carryforward_days >= 0."""
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        al.carryforward_days = -5
        al.save()
        al.refresh_from_db()
        self.assertEqual(al.carryforward_days, 0)

    def test_assigned_date_defaults_to_today(self):
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        # assigned_date may be datetime or date depending on field type
        assigned = al.assigned_date
        if hasattr(assigned, "date"):
            assigned = assigned.date()
        self.assertEqual(assigned, date.today())

    def test_different_employees_same_leave_type(self):
        """Two different employees can have the same leave type."""
        al1 = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        al2 = AvailableLeaveFactory(
            employee_id=self.manager_employee,
            leave_type_id=self.leave_type,
        )
        self.assertNotEqual(al1.pk, al2.pk)

    def test_update_available_days(self):
        al = AvailableLeaveFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            available_days=5,
        )
        al.available_days = 20
        al.save()
        al.refresh_from_db()
        self.assertEqual(al.available_days, 20)


# ---------------------------------------------------------------------------
# LeaveRequest Tests (~20)
# ---------------------------------------------------------------------------
class LeaveRequestCreateTest(HorillaTestCase):
    """CRUD for LeaveRequest."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leave_type = LeaveTypeFactory(company_id=cls.company_a)
        # Assign the leave type to the admin employee so requests pass validation
        cls.available_leave = AvailableLeaveFactory(
            employee_id=cls.admin_employee,
            leave_type_id=cls.leave_type,
            available_days=30,
        )

    def _make_request(self, **kwargs):
        """Helper to create a LeaveRequest with sensible defaults."""
        defaults = {
            "employee_id": self.admin_employee,
            "leave_type_id": self.leave_type,
            "start_date": date.today() + timedelta(days=1),
            "end_date": date.today() + timedelta(days=3),
            "start_date_breakdown": "full_day",
            "end_date_breakdown": "full_day",
            "description": "Test leave",
            "status": "requested",
        }
        defaults.update(kwargs)
        return LeaveRequest(**defaults)

    def test_create_leave_request(self):
        lr = self._make_request()
        lr.save()
        self.assertIsNotNone(lr.pk)
        self.assertEqual(lr.status, "requested")

    def test_str_representation(self):
        lr = self._make_request()
        lr.save()
        result = str(lr)
        self.assertIn(str(self.admin_employee), result)
        self.assertIn("requested", result)

    def test_status_choices(self):
        valid_statuses = [choice[0] for choice in LEAVE_STATUS]
        self.assertIn("requested", valid_statuses)
        self.assertIn("approved", valid_statuses)
        self.assertIn("cancelled", valid_statuses)
        self.assertIn("rejected", valid_statuses)

    def test_breakdown_choices(self):
        valid_breakdowns = [choice[0] for choice in BREAKDOWN]
        self.assertIn("full_day", valid_breakdowns)
        self.assertIn("first_half", valid_breakdowns)
        self.assertIn("second_half", valid_breakdowns)

    def test_requested_days_calculated_on_save(self):
        """save() auto-calculates requested_days from dates and breakdowns."""
        lr = self._make_request(
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            start_date_breakdown="full_day",
            end_date_breakdown="full_day",
        )
        lr.save()
        # 3 full days: day1 + day2 + day3
        self.assertEqual(lr.requested_days, 3.0)

    def test_requested_days_half_day_start(self):
        lr = self._make_request(
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            start_date_breakdown="first_half",
            end_date_breakdown="full_day",
        )
        lr.save()
        # 0.5 (start) + 1 (middle) + 1 (end) = 2.5
        self.assertEqual(lr.requested_days, 2.5)

    def test_requested_days_half_day_end(self):
        lr = self._make_request(
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            start_date_breakdown="full_day",
            end_date_breakdown="first_half",
        )
        lr.save()
        # 1 (start) + 1 (middle) + 0.5 (end) = 2.5
        self.assertEqual(lr.requested_days, 2.5)

    def test_requested_days_single_full_day(self):
        tomorrow = date.today() + timedelta(days=1)
        lr = self._make_request(
            start_date=tomorrow,
            end_date=tomorrow,
            start_date_breakdown="full_day",
            end_date_breakdown="full_day",
        )
        lr.save()
        self.assertEqual(lr.requested_days, 1.0)

    def test_requested_days_single_half_day(self):
        tomorrow = date.today() + timedelta(days=1)
        lr = self._make_request(
            start_date=tomorrow,
            end_date=tomorrow,
            start_date_breakdown="first_half",
            end_date_breakdown="first_half",
        )
        lr.save()
        self.assertEqual(lr.requested_days, 0.5)

    def test_requested_dates_returns_correct_list(self):
        start = date.today() + timedelta(days=1)
        end = date.today() + timedelta(days=4)
        lr = self._make_request(start_date=start, end_date=end)
        lr.save()
        dates = lr.requested_dates()
        self.assertEqual(len(dates), 4)
        self.assertEqual(dates[0], start)
        self.assertEqual(dates[-1], end)

    def test_requested_dates_single_day(self):
        tomorrow = date.today() + timedelta(days=1)
        lr = self._make_request(start_date=tomorrow, end_date=tomorrow)
        lr.save()
        dates = lr.requested_dates()
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0], tomorrow)

    def test_clean_end_date_before_start_date_raises(self):
        """clean() raises ValidationError if end_date < start_date."""
        lr = self._make_request(
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            lr.clean()

    def test_clean_same_day_breakdown_mismatch_raises(self):
        """Same-day leave with different start/end breakdowns raises error."""
        tomorrow = date.today() + timedelta(days=1)
        lr = self._make_request(
            start_date=tomorrow,
            end_date=tomorrow,
            start_date_breakdown="first_half",
            end_date_breakdown="second_half",
        )
        with self.assertRaises(ValidationError):
            lr.clean()

    def test_clean_overlapping_leave_raises(self):
        """Overlapping leave request for same employee should raise error."""
        start = date.today() + timedelta(days=10)
        end = date.today() + timedelta(days=12)
        lr1 = self._make_request(start_date=start, end_date=end)
        lr1.save()

        lr2 = self._make_request(
            start_date=start + timedelta(days=1),
            end_date=end + timedelta(days=1),
        )
        lr2.save()
        with self.assertRaises(ValidationError):
            lr2.clean()

    def test_status_default_is_requested(self):
        lr = self._make_request()
        self.assertEqual(lr.status, "requested")

    def test_status_transition_to_approved(self):
        lr = self._make_request()
        lr.save()
        lr.status = "approved"
        lr.save()
        lr.refresh_from_db()
        self.assertEqual(lr.status, "approved")

    def test_status_transition_to_rejected(self):
        lr = self._make_request()
        lr.save()
        lr.status = "rejected"
        lr.save()
        lr.refresh_from_db()
        self.assertEqual(lr.status, "rejected")

    def test_status_transition_to_cancelled(self):
        lr = self._make_request()
        lr.save()
        lr.status = "cancelled"
        lr.save()
        lr.refresh_from_db()
        self.assertEqual(lr.status, "cancelled")

    def test_leave_clashes_count_reset_on_cancel(self):
        """Cancelling a request should reset leave_clashes_count to 0."""
        lr = self._make_request()
        lr.save()
        lr.status = "cancelled"
        lr.save()
        lr.refresh_from_db()
        self.assertEqual(lr.leave_clashes_count, 0)

    def test_delete_requested_leave_succeeds(self):
        """Requested leave can be deleted."""
        lr = self._make_request()
        lr.save()
        pk = lr.pk
        lr.delete()
        self.assertFalse(LeaveRequest.objects.filter(pk=pk).exists())

    def test_delete_approved_leave_blocked(self):
        """Approved leave cannot be deleted (only requested can)."""
        lr = self._make_request()
        lr.save()
        lr.status = "approved"
        lr.save()
        pk = lr.pk
        lr.delete()
        # The record should still exist because delete() only works on "requested" status
        self.assertTrue(LeaveRequest.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# LeaveAllocationRequest Tests (~5)
# ---------------------------------------------------------------------------
class LeaveAllocationRequestTest(HorillaTestCase):
    """Tests for LeaveAllocationRequest model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leave_type = LeaveTypeFactory(company_id=cls.company_a)

    def test_create_allocation_request(self):
        alloc = LeaveAllocationRequestFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        self.assertIsNotNone(alloc.pk)
        self.assertEqual(alloc.status, "requested")

    def test_str_representation(self):
        alloc = LeaveAllocationRequestFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        result = str(alloc)
        self.assertIn(str(self.admin_employee), result)
        self.assertIn(str(self.leave_type), result)

    def test_status_choices(self):
        valid_statuses = [choice[0] for choice in LEAVE_ALLOCATION_STATUS]
        self.assertIn("requested", valid_statuses)
        self.assertIn("approved", valid_statuses)
        self.assertIn("rejected", valid_statuses)
        # No "cancelled" for allocation requests
        self.assertNotIn("cancelled", valid_statuses)

    def test_clean_raises_when_status_not_requested(self):
        """clean() prevents editing when status is not 'requested'."""
        alloc = LeaveAllocationRequestFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
        )
        # Manually set status to approved bypassing clean
        LeaveAllocationRequest.objects.filter(pk=alloc.pk).update(status="approved")
        alloc.refresh_from_db()
        with self.assertRaises(ValidationError):
            alloc.clean()

    def test_requested_days_stored(self):
        alloc = LeaveAllocationRequestFactory(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            requested_days=7.5,
        )
        self.assertEqual(alloc.requested_days, 7.5)


# ---------------------------------------------------------------------------
# RestrictLeave Tests (~5)
# ---------------------------------------------------------------------------
class RestrictLeaveTest(HorillaTestCase):
    """Tests for RestrictLeave model."""

    def test_create_restrict_leave(self):
        rl = RestrictLeaveFactory(department=self.department)
        self.assertIsNotNone(rl.pk)

    def test_str_representation(self):
        rl = RestrictLeaveFactory(
            title="Year End Freeze",
            department=self.department,
        )
        self.assertEqual(str(rl), "Year End Freeze")

    def test_required_fields_title(self):
        with self.assertRaises(Exception):
            RestrictLeave.objects.create(
                title=None,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=3),
                department=self.department,
            )

    def test_date_range(self):
        start = date(2026, 12, 20)
        end = date(2026, 12, 31)
        rl = RestrictLeaveFactory(
            start_date=start,
            end_date=end,
            department=self.department,
        )
        self.assertEqual(rl.start_date, start)
        self.assertEqual(rl.end_date, end)

    def test_department_required(self):
        """RestrictLeave requires a department FK."""
        with self.assertRaises(Exception):
            RestrictLeave.objects.create(
                title="No Dept",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=1),
                department=None,
            )

    def test_include_all_default_true(self):
        rl = RestrictLeaveFactory(department=self.department)
        self.assertTrue(rl.include_all)
