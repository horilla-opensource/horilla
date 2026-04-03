"""
Tests for attendance module models.

Covers Attendance, AttendanceActivity, AttendanceOverTime, WorkRecords,
GraceTime, AttendanceLateComeEarlyOut, and AttendanceValidationCondition
with CRUD, validation, and business logic tests.
"""

from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceValidationCondition,
    GraceTime,
    WorkRecords,
)
from attendance.tests.factories import (
    AttendanceActivityFactory,
    AttendanceFactory,
    AttendanceLateComeEarlyOutFactory,
    AttendanceOverTimeFactory,
    AttendanceValidationConditionFactory,
    GraceTimeFactory,
    WorkRecordFactory,
)
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# Attendance Tests (~10)
# ---------------------------------------------------------------------------
class AttendanceCreateTest(HorillaTestCase):
    """Basic CRUD for Attendance."""

    def test_create_attendance(self):
        """Attendance can be created with required fields."""
        att = AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=1),
        )
        self.assertIsNotNone(att.pk)
        self.assertEqual(att.employee_id, self.admin_employee)

    def test_str_representation(self):
        """__str__ includes employee name and date."""
        att = AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=2),
        )
        result = str(att)
        self.assertIn("Admin", result)
        self.assertIn(str(att.attendance_date), result)

    def test_attendance_date_required(self):
        """Attendance without attendance_date should fail."""
        with self.assertRaises(Exception):
            Attendance.objects.create(
                employee_id=self.admin_employee,
                attendance_date=None,
                attendance_clock_in=time(9, 0),
            )

    def test_employee_fk(self):
        """Attendance has correct FK to Employee."""
        att = AttendanceFactory(
            employee_id=self.regular_employee,
            attendance_date=date.today() - timedelta(days=3),
        )
        self.assertEqual(att.employee_id.pk, self.regular_employee.pk)

    def test_unique_together_employee_date(self):
        """Cannot create two attendances for same employee+date."""
        target_date = date.today() - timedelta(days=4)
        AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=target_date,
        )
        with self.assertRaises(IntegrityError):
            AttendanceFactory(
                employee_id=self.admin_employee,
                attendance_date=target_date,
            )

    def test_minimum_hour_default(self):
        """minimum_hour defaults to '00:00'."""
        att = Attendance(employee_id=self.admin_employee, attendance_date=date.today())
        self.assertEqual(att.minimum_hour, "00:00")

    def test_attendance_worked_hour_default(self):
        """attendance_worked_hour defaults to '00:00'."""
        att = Attendance(
            employee_id=self.admin_employee,
            attendance_date=date.today(),
        )
        self.assertEqual(att.attendance_worked_hour, "00:00")

    def test_attendance_validated_default_false(self):
        """attendance_validated defaults to False."""
        att = AttendanceFactory(
            employee_id=self.manager_employee,
            attendance_date=date.today() - timedelta(days=5),
        )
        self.assertFalse(att.attendance_validated)

    def test_overtime_approve_default_false(self):
        """attendance_overtime_approve defaults to False."""
        att = AttendanceFactory(
            employee_id=self.manager_employee,
            attendance_date=date.today() - timedelta(days=6),
        )
        self.assertFalse(att.attendance_overtime_approve)

    def test_at_work_second_computed_on_save(self):
        """at_work_second is populated from attendance_worked_hour on save."""
        att = AttendanceFactory(
            employee_id=self.regular_employee,
            attendance_date=date.today() - timedelta(days=7),
            attendance_worked_hour="08:00",
            minimum_hour="08:00",
        )
        # 8 hours = 28800 seconds
        self.assertEqual(att.at_work_second, 28800)

    def test_overtime_computed_when_worked_exceeds_minimum(self):
        """attendance_overtime should be nonzero when worked > minimum."""
        att = AttendanceFactory(
            employee_id=self.regular_employee,
            attendance_date=date.today() - timedelta(days=8),
            attendance_worked_hour="10:00",
            minimum_hour="08:00",
        )
        # 2 hours overtime
        self.assertEqual(att.attendance_overtime, "02:00")
        self.assertEqual(att.overtime_second, 7200)

    def test_no_overtime_when_worked_equals_minimum(self):
        """attendance_overtime should be '00:00' when worked == minimum."""
        att = AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=9),
            attendance_worked_hour="08:00",
            minimum_hour="08:00",
        )
        self.assertEqual(att.attendance_overtime, "00:00")


class AttendanceCleanTest(HorillaTestCase):
    """Validation tests for Attendance.clean()."""

    def test_clock_in_date_before_attendance_date_raises(self):
        """clock_in_date earlier than attendance_date should raise ValidationError."""
        att = Attendance(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=1),
            attendance_clock_in_date=date.today() - timedelta(days=5),
            attendance_clock_in=time(9, 0),
            attendance_clock_out_date=date.today() - timedelta(days=1),
            attendance_clock_out=time(17, 0),
        )
        with self.assertRaises(ValidationError) as ctx:
            att.clean()
        self.assertIn("attendance_clock_in_date", ctx.exception.message_dict)

    def test_clock_out_date_before_clock_in_date_raises(self):
        """clock_out_date earlier than clock_in_date should raise ValidationError."""
        target = date.today() - timedelta(days=10)
        att = Attendance(
            employee_id=self.admin_employee,
            attendance_date=target,
            attendance_clock_in_date=target,
            attendance_clock_in=time(9, 0),
            attendance_clock_out_date=target - timedelta(days=1),
            attendance_clock_out=time(17, 0),
        )
        with self.assertRaises(ValidationError) as ctx:
            att.clean()
        self.assertIn("attendance_clock_out_date", ctx.exception.message_dict)


# ---------------------------------------------------------------------------
# AttendanceActivity Tests (~6)
# ---------------------------------------------------------------------------
class AttendanceActivityTest(HorillaTestCase):
    """Tests for AttendanceActivity model."""

    def test_create_activity(self):
        """AttendanceActivity can be created."""
        activity = AttendanceActivityFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=1),
        )
        self.assertIsNotNone(activity.pk)

    def test_str_representation(self):
        """__str__ includes employee, date, clock_in, clock_out."""
        activity = AttendanceActivityFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=2),
            clock_in=time(9, 0),
            clock_out=time(17, 0),
        )
        result = str(activity)
        self.assertIn(str(activity.attendance_date), result)

    def test_clock_in_required(self):
        """clock_in is required."""
        with self.assertRaises(Exception):
            AttendanceActivity.objects.create(
                employee_id=self.admin_employee,
                attendance_date=date.today() - timedelta(days=3),
                clock_in_date=date.today() - timedelta(days=3),
                clock_in=None,
            )

    def test_clock_out_nullable(self):
        """clock_out can be null (employee still checked in)."""
        activity = AttendanceActivityFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=4),
            clock_out=None,
            clock_out_date=None,
        )
        self.assertIsNone(activity.clock_out)

    def test_duration_calculation(self):
        """duration() returns correct seconds between clock_in and clock_out."""
        activity = AttendanceActivityFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=5),
            clock_in_date=date.today() - timedelta(days=5),
            clock_in=time(9, 0),
            clock_out_date=date.today() - timedelta(days=5),
            clock_out=time(17, 0),
        )
        # 8 hours = 28800 seconds
        self.assertEqual(activity.duration(), 28800.0)

    def test_duration_format(self):
        """duration_format() returns HH:MM:SS string."""
        activity = AttendanceActivityFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=6),
            clock_in_date=date.today() - timedelta(days=6),
            clock_in=time(9, 0),
            clock_out_date=date.today() - timedelta(days=6),
            clock_out=time(17, 0),
        )
        self.assertEqual(activity.duration_format(), "08:00:00")


# ---------------------------------------------------------------------------
# AttendanceOverTime Tests (~5)
# ---------------------------------------------------------------------------
class AttendanceOverTimeTest(HorillaTestCase):
    """Tests for AttendanceOverTime (Hour Account) model."""

    def test_create_overtime_record(self):
        """AttendanceOverTime can be created."""
        ot = AttendanceOverTimeFactory(employee_id=self.admin_employee)
        self.assertIsNotNone(ot.pk)

    def test_str_representation(self):
        """__str__ includes employee and month."""
        ot = AttendanceOverTimeFactory(
            employee_id=self.admin_employee,
            month="march",
        )
        result = str(ot)
        self.assertIn("march", result)

    def test_month_sequence_set_on_save(self):
        """month_sequence is auto-set based on month name."""
        ot = AttendanceOverTimeFactory(
            employee_id=self.admin_employee,
            month="march",
        )
        # march is index 2 (0-based)
        self.assertEqual(ot.month_sequence, 2)

    def test_worked_hours_computed_from_seconds(self):
        """worked_hours is formatted from hour_account_second on save."""
        ot = AttendanceOverTimeFactory(
            employee_id=self.manager_employee,
            hour_account_second=36000,  # 10 hours
        )
        self.assertEqual(ot.worked_hours, "10:00")

    def test_clean_validates_year_range(self):
        """Year outside 1900-2100 raises ValidationError."""
        ot = AttendanceOverTime(
            employee_id=self.admin_employee,
            month="january",
            year="2200",
        )
        with self.assertRaises(ValidationError) as ctx:
            ot.clean()
        self.assertIn("year", ctx.exception.message_dict)

    def test_clean_validates_year_not_string(self):
        """Non-numeric year raises ValidationError."""
        ot = AttendanceOverTime(
            employee_id=self.admin_employee,
            month="january",
            year="abc",
        )
        with self.assertRaises(ValidationError) as ctx:
            ot.clean()
        self.assertIn("year", ctx.exception.message_dict)


# ---------------------------------------------------------------------------
# WorkRecords Tests (~8)
# ---------------------------------------------------------------------------
class WorkRecordsTest(HorillaTestCase):
    """Tests for WorkRecords model."""

    def test_create_work_record(self):
        """WorkRecord can be created with required fields."""
        wr = WorkRecordFactory(employee_id=self.admin_employee)
        self.assertIsNotNone(wr.pk)

    def test_str_with_record_name(self):
        """__str__ returns record_name when set."""
        wr = WorkRecordFactory(
            employee_id=self.admin_employee,
            record_name="Test Record",
        )
        self.assertEqual(str(wr), "Test Record")

    def test_str_without_record_name(self):
        """__str__ returns type-date-employee when record_name is None."""
        wr = WorkRecordFactory(
            employee_id=self.admin_employee,
            record_name=None,
            work_record_type="ABS",
        )
        result = str(wr)
        self.assertIn("ABS", result)

    def test_work_record_type_choices(self):
        """Valid work_record_type choices: FDP, HDP, ABS, HD, CONF, DFT."""
        valid_types = ["FDP", "HDP", "ABS", "HD", "CONF", "DFT"]
        for wrt in valid_types:
            wr = WorkRecordFactory(
                employee_id=self.admin_employee,
                work_record_type=wrt,
                date=date.today() - timedelta(days=valid_types.index(wrt) + 20),
            )
            self.assertEqual(wr.work_record_type, wrt)

    def test_day_percentage_full_day(self):
        """day_percentage of 1.0 for a full day."""
        wr = WorkRecordFactory(
            employee_id=self.admin_employee,
            day_percentage=1.0,
        )
        self.assertEqual(wr.day_percentage, 1.0)

    def test_day_percentage_half_day(self):
        """day_percentage of 0.5 for a half day."""
        wr = WorkRecordFactory(
            employee_id=self.admin_employee,
            day_percentage=0.5,
            date=date.today() - timedelta(days=30),
        )
        self.assertEqual(wr.day_percentage, 0.5)

    def test_clean_day_percentage_out_of_range(self):
        """day_percentage outside 0.0-1.0 raises ValidationError."""
        wr = WorkRecords(
            employee_id=self.admin_employee,
            date=date.today() - timedelta(days=31),
            work_record_type="FDP",
            day_percentage=1.5,
            note="test",
        )
        with self.assertRaises(ValidationError):
            wr.clean()

    def test_is_leave_record_default_false(self):
        """is_leave_record defaults to False."""
        wr = WorkRecordFactory(employee_id=self.admin_employee)
        self.assertFalse(wr.is_leave_record)

    def test_last_update_set_on_save(self):
        """last_update is auto-set on save."""
        wr = WorkRecordFactory(
            employee_id=self.admin_employee,
            date=date.today() - timedelta(days=32),
        )
        self.assertIsNotNone(wr.last_update)


# ---------------------------------------------------------------------------
# GraceTime Tests (~4)
# ---------------------------------------------------------------------------
class GraceTimeTest(HorillaTestCase):
    """Tests for GraceTime model."""

    def test_create_grace_time(self):
        """GraceTime can be created."""
        gt = GraceTimeFactory()
        self.assertIsNotNone(gt.pk)

    def test_str_representation(self):
        """__str__ includes allowed_time and 'Hours'."""
        gt = GraceTimeFactory(allowed_time="00:15:00")
        result = str(gt)
        self.assertIn("00:15:00", result)
        self.assertIn("Hours", result)

    def test_allowed_time_in_secs_computed(self):
        """allowed_time_in_secs is computed on save from allowed_time."""
        gt = GraceTimeFactory(allowed_time="01:30:00", allowed_time_in_secs=0)
        # save() recomputes: 1*3600 + 30*60 + 0 = 5400
        self.assertEqual(gt.allowed_time_in_secs, 5400)

    def test_only_one_default_allowed(self):
        """Only one GraceTime can be is_default=True."""
        GraceTimeFactory(is_default=True, allowed_time="00:10:00")
        gt2 = GraceTime(
            allowed_time="00:20:00",
            allowed_time_in_secs=1200,
            is_default=True,
        )
        with self.assertRaises(ValidationError):
            gt2.clean()

    def test_duplicate_allowed_time_raises(self):
        """Two non-default GraceTimes with same allowed_time raise ValidationError."""
        GraceTimeFactory(allowed_time="00:15:00", is_default=False)
        gt2 = GraceTime(
            allowed_time="00:15:00",
            allowed_time_in_secs=900,
            is_default=False,
        )
        with self.assertRaises(ValidationError):
            gt2.clean()


# ---------------------------------------------------------------------------
# AttendanceLateComeEarlyOut Tests (~3)
# ---------------------------------------------------------------------------
class AttendanceLateComeEarlyOutTest(HorillaTestCase):
    """Tests for AttendanceLateComeEarlyOut model."""

    def test_create_late_come(self):
        """Late come record can be created."""
        att = AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=40),
        )
        late = AttendanceLateComeEarlyOut(
            attendance_id=att,
            type="late_come",
        )
        late.save()
        self.assertIsNotNone(late.pk)
        # save() auto-sets employee_id from attendance_id
        self.assertEqual(late.employee_id, self.admin_employee)

    def test_create_early_out(self):
        """Early out record can be created."""
        att = AttendanceFactory(
            employee_id=self.manager_employee,
            attendance_date=date.today() - timedelta(days=41),
        )
        early = AttendanceLateComeEarlyOut(
            attendance_id=att,
            type="early_out",
        )
        early.save()
        self.assertIsNotNone(early.pk)

    def test_get_type_display(self):
        """get_type() returns human-readable type."""
        att = AttendanceFactory(
            employee_id=self.admin_employee,
            attendance_date=date.today() - timedelta(days=42),
        )
        late = AttendanceLateComeEarlyOut(attendance_id=att, type="late_come")
        late.save()
        self.assertEqual(str(late.get_type()), "Late Come")


# ---------------------------------------------------------------------------
# AttendanceValidationCondition Tests (~2)
# ---------------------------------------------------------------------------
class AttendanceValidationConditionTest(HorillaTestCase):
    """Tests for AttendanceValidationCondition model."""

    def test_create_condition(self):
        """Validation condition can be created."""
        cond = AttendanceValidationConditionFactory()
        self.assertIsNotNone(cond.pk)

    def test_only_one_condition_allowed(self):
        """Cannot create more than one validation condition."""
        AttendanceValidationConditionFactory()
        cond2 = AttendanceValidationCondition(
            validation_at_work="09:00",
        )
        with self.assertRaises(ValidationError):
            cond2.clean()
