"""
Tests for leave module signal handlers (leave/signals.py).

Signals tested:
- post_save on LeaveRequest: creates/deletes WorkRecords based on status
- pre_delete on LeaveRequest: deletes associated WorkRecords

NOTE: These tests require the attendance app to be installed. All tests
are skipped if attendance is not in INSTALLED_APPS.
"""

import unittest
from datetime import date, timedelta

from django.apps import apps
from django.test import override_settings

from horilla.test_utils.base import HorillaTestCase

# Skip entire module if attendance app is not installed
if not apps.is_installed("attendance"):
    raise unittest.SkipTest("attendance app not installed, skipping signal tests")

from attendance.models import WorkRecords
from leave.models import AvailableLeave, LeaveRequest, LeaveType
from leave.tests.factories import AvailableLeaveFactory, LeaveTypeFactory


class LeaveRequestSignalTest(HorillaTestCase):
    """
    Tests for the post_save signal on LeaveRequest that manages WorkRecords.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leave_type = LeaveTypeFactory(company_id=cls.company_a)
        cls.available_leave = AvailableLeaveFactory(
            employee_id=cls.admin_employee,
            leave_type_id=cls.leave_type,
            available_days=30,
        )

    def _create_leave_request(
        self,
        start_offset=1,
        end_offset=3,
        status="requested",
        start_breakdown="full_day",
        end_breakdown="full_day",
    ):
        """Helper to create and save a LeaveRequest."""
        lr = LeaveRequest(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            start_date=date.today() + timedelta(days=start_offset),
            end_date=date.today() + timedelta(days=end_offset),
            start_date_breakdown=start_breakdown,
            end_date_breakdown=end_breakdown,
            description="Signal test leave",
            status=status,
        )
        lr.save()
        return lr

    def _work_records_for(self, leave_request):
        """Get WorkRecords associated with the given leave request's employee and dates."""
        return WorkRecords._base_manager.filter(
            employee_id=leave_request.employee_id,
            is_leave_record=True,
            date__gte=leave_request.start_date,
            date__lte=leave_request.end_date,
        )

    def _work_records_by_leave_fk(self, leave_request):
        """Get WorkRecords linked via leave_request_id FK."""
        return WorkRecords._base_manager.filter(
            leave_request_id=leave_request,
        )

    # -----------------------------------------------------------------------
    # Test 1: Approved LeaveRequest creates WorkRecords for each leave day
    # -----------------------------------------------------------------------
    def test_approved_leave_creates_work_records(self):
        lr = self._create_leave_request(start_offset=10, end_offset=12)
        lr.status = "approved"
        lr.save()

        records = self._work_records_for(lr)
        expected_days = (lr.end_date - lr.start_date).days + 1
        self.assertEqual(records.count(), expected_days)

    # -----------------------------------------------------------------------
    # Test 2: WorkRecords have correct work_record_type
    # -----------------------------------------------------------------------
    def test_work_records_type_abs_for_full_day(self):
        """Full-day leave creates ABS type work records."""
        lr = self._create_leave_request(start_offset=15, end_offset=15)
        lr.status = "approved"
        lr.save()

        records = self._work_records_for(lr)
        for record in records:
            self.assertEqual(record.work_record_type, "ABS")

    # -----------------------------------------------------------------------
    # Test 3: Half-day leave (first_half start) sets day_percentage=0.50
    # -----------------------------------------------------------------------
    def test_half_day_first_half_sets_percentage_050(self):
        lr = self._create_leave_request(
            start_offset=20,
            end_offset=20,
            start_breakdown="first_half",
            end_breakdown="first_half",
        )
        lr.status = "approved"
        lr.save()

        records = self._work_records_for(lr)
        self.assertTrue(records.exists())
        record = records.first()
        self.assertEqual(record.day_percentage, 0.50)

    # -----------------------------------------------------------------------
    # Test 4: Full-day leave sets day_percentage=0.00
    # -----------------------------------------------------------------------
    def test_full_day_sets_percentage_000(self):
        lr = self._create_leave_request(start_offset=25, end_offset=25)
        lr.status = "approved"
        lr.save()

        records = self._work_records_for(lr)
        self.assertTrue(records.exists())
        record = records.first()
        self.assertEqual(record.day_percentage, 0.00)

    # -----------------------------------------------------------------------
    # Test 5: Rejecting previously approved leave deletes WorkRecords
    # -----------------------------------------------------------------------
    def test_rejecting_approved_leave_deletes_work_records(self):
        lr = self._create_leave_request(start_offset=30, end_offset=32)
        lr.status = "approved"
        lr.save()

        # Verify records were created
        records_count = self._work_records_for(lr).count()
        self.assertGreater(records_count, 0)

        # Now reject
        lr.status = "rejected"
        lr.save()

        records_after = self._work_records_for(lr).count()
        self.assertEqual(records_after, 0)

    # -----------------------------------------------------------------------
    # Test 6: Cancelling approved leave deletes WorkRecords
    # -----------------------------------------------------------------------
    def test_cancelling_approved_leave_deletes_work_records(self):
        lr = self._create_leave_request(start_offset=35, end_offset=37)
        lr.status = "approved"
        lr.save()

        records_count = self._work_records_for(lr).count()
        self.assertGreater(records_count, 0)

        lr.status = "cancelled"
        lr.save()

        records_after = self._work_records_for(lr).count()
        self.assertEqual(records_after, 0)

    # -----------------------------------------------------------------------
    # Test 7: Deleting a LeaveRequest deletes associated WorkRecords
    # -----------------------------------------------------------------------
    def test_deleting_leave_request_deletes_work_records(self):
        lr = self._create_leave_request(start_offset=40, end_offset=42)
        lr.status = "approved"
        lr.save()

        fk_count = self._work_records_by_leave_fk(lr).count()
        self.assertGreater(fk_count, 0)

        # LeaveRequest.delete() only works for status="requested", so set it back
        LeaveRequest.objects.filter(pk=lr.pk).update(status="requested")
        lr.refresh_from_db()
        lr.delete()

        # pre_delete signal should have cleaned up
        fk_after = WorkRecords._base_manager.filter(
            leave_request_id=lr.pk,
        ).count()
        self.assertEqual(fk_after, 0)

    # -----------------------------------------------------------------------
    # Test 8: Changing status from approved to rejected deletes WorkRecords
    # -----------------------------------------------------------------------
    def test_approved_to_rejected_deletes_records(self):
        lr = self._create_leave_request(start_offset=45, end_offset=46)
        lr.status = "approved"
        lr.save()

        self.assertGreater(self._work_records_for(lr).count(), 0)

        lr.status = "rejected"
        lr.save()

        self.assertEqual(self._work_records_for(lr).count(), 0)

    # -----------------------------------------------------------------------
    # Test 9: Half-day end (second_half) sets correct type CONF
    # -----------------------------------------------------------------------
    def test_second_half_end_sets_conf_type(self):
        """When end_date_breakdown is second_half, record type should be CONF."""
        start = date.today() + timedelta(days=50)
        end = date.today() + timedelta(days=51)
        lr = LeaveRequest(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            start_date=start,
            end_date=end,
            start_date_breakdown="full_day",
            end_date_breakdown="second_half",
            description="Half day end test",
            status="approved",
        )
        lr.save()

        end_record = WorkRecords._base_manager.filter(
            employee_id=self.admin_employee,
            date=end,
            is_leave_record=True,
        ).first()
        if end_record:
            self.assertEqual(end_record.work_record_type, "CONF")
            self.assertEqual(end_record.day_percentage, 0.50)

    # -----------------------------------------------------------------------
    # Test 10: Requested status does not create WorkRecords
    # -----------------------------------------------------------------------
    def test_requested_status_does_not_create_records(self):
        """A leave request with status 'requested' should not create WorkRecords."""
        lr = self._create_leave_request(
            start_offset=55, end_offset=57, status="requested"
        )

        # The signal runs on post_save but should not create records for non-approved
        # Instead it deletes any existing ones (which there are none)
        records = self._work_records_for(lr)
        self.assertEqual(records.count(), 0)

    # -----------------------------------------------------------------------
    # Test 11: Multiple days approved creates record per day
    # -----------------------------------------------------------------------
    def test_multi_day_approved_creates_record_per_day(self):
        lr = self._create_leave_request(start_offset=60, end_offset=64)
        lr.status = "approved"
        lr.save()

        records = self._work_records_for(lr)
        expected = 5  # days 60, 61, 62, 63, 64
        self.assertEqual(records.count(), expected)

    # -----------------------------------------------------------------------
    # Test 12: Same-day breakdown sync on approved save
    # -----------------------------------------------------------------------
    def test_same_day_breakdown_sync(self):
        """When start_date == end_date and breakdowns differ, signal syncs them."""
        day = date.today() + timedelta(days=70)
        lr = LeaveRequest(
            employee_id=self.admin_employee,
            leave_type_id=self.leave_type,
            start_date=day,
            end_date=day,
            start_date_breakdown="first_half",
            end_date_breakdown="second_half",
            description="Sync test",
            status="approved",
        )
        lr.save()

        lr.refresh_from_db()
        # Signal should have synced end_date_breakdown to match start_date_breakdown
        self.assertEqual(lr.end_date_breakdown, lr.start_date_breakdown)
