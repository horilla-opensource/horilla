"""
Tests for employee-specific holiday filtering in the attendance app.

Updated functions under test:
- attendance/methods/utils.py  :: attendance_day_checking()
- attendance/models.py         :: Attendance.adjust_minimum_hour()
- attendance/views/views.py    :: work_records_change_month (leave_dates)
- attendance/views/views.py    :: work_record_export (per-employee specific holiday rows)
"""

from datetime import date, timedelta

from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from attendance.methods.utils import attendance_day_checking, monthly_leave_days
from attendance.models import Attendance
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    Holidays,
    WorkType,
)
from employee.models import Employee, EmployeeWorkInformation

# ─── Shared fixture ────────────────────────────────────────────────────────────


class HolidayFixtureMixin:
    """
    Creates two employees, a global holiday, and an employee-specific holiday.
    All holiday dates are in the past so attendance records can be created on them.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company="Test Corp",
            hq=True,
            address="1 Test St",
            country="US",
            state="CA",
            city="LA",
            zip="90001",
        )

        cls.shift = EmployeeShift.objects.create(employee_shift="Day Shift")
        cls.shift.company_id.add(cls.company)

        cls.work_type = WorkType.objects.create(work_type="Office")
        cls.work_type.company_id.add(cls.company)

        cls.dept = Department.objects.create(department="Engineering")
        cls.dept.company_id.add(cls.company)

        cls.shift_day = EmployeeShiftDay.objects.filter(day="monday").first()

        cls.emp_a = cls._make_employee("emp_a@holiday.test", "Alice", "Holiday")
        cls.emp_b = cls._make_employee("emp_b@holiday.test", "Bob", "Holiday")

        # Dates well in the past to satisfy attendance_date_validate
        cls.global_date = date.today() - timedelta(days=60)
        cls.specific_date = date.today() - timedelta(days=30)
        cls.normal_date = date.today() - timedelta(days=10)

        # Global holiday — is_specific=False, applies to all employees
        cls.global_holiday = Holidays.objects.create(
            name="Global Holiday",
            start_date=cls.global_date,
            end_date=cls.global_date,
            is_specific=False,
            company_id=cls.company,
        )

        # Specific holiday — is_specific=True, assigned only to emp_a
        cls.specific_holiday = Holidays.objects.create(
            name="Specific Holiday",
            start_date=cls.specific_date,
            end_date=cls.specific_date,
            is_specific=True,
            assigning_type="employee",
            company_id=cls.company,
        )
        cls.specific_holiday.employees.add(cls.emp_a)

    @classmethod
    def _make_employee(cls, email, first_name, last_name):
        emp = Employee.objects.create(
            employee_first_name=first_name,
            employee_last_name=last_name,
            email=email,
            phone="9999999999",
        )
        EmployeeWorkInformation.objects.filter(employee_id=emp).update(
            company_id_id=cls.company.pk,
            shift_id_id=cls.shift.pk,
            work_type_id_id=cls.work_type.pk,
        )
        return emp


# ─── 1. attendance_day_checking() ─────────────────────────────────────────────


class TestAttendanceDayChecking(HolidayFixtureMixin, TestCase):
    """
    attendance_day_checking() must return '00:00' only for holidays
    that apply to the given employee.
    """

    def test_global_holiday_no_employee_resets_minimum_hour(self):
        """No employee context: global holiday zeroes minimum_hour."""
        result = attendance_day_checking(str(self.global_date), "08:00")
        self.assertEqual(result, "00:00")

    def test_global_holiday_with_emp_a_resets_minimum_hour(self):
        """emp_a: global holiday zeroes minimum_hour."""
        result = attendance_day_checking(
            str(self.global_date), "08:00", employee=self.emp_a
        )
        self.assertEqual(result, "00:00")

    def test_global_holiday_with_emp_b_resets_minimum_hour(self):
        """emp_b: global holiday also zeroes minimum_hour (applies to all)."""
        result = attendance_day_checking(
            str(self.global_date), "08:00", employee=self.emp_b
        )
        self.assertEqual(result, "00:00")

    def test_specific_holiday_no_employee_does_not_reset(self):
        """No employee context: specific holiday is excluded, hour unchanged."""
        result = attendance_day_checking(str(self.specific_date), "08:00")
        self.assertEqual(result, "08:00")

    def test_specific_holiday_with_assigned_emp_a_resets(self):
        """emp_a is assigned to the specific holiday — hour must become 00:00."""
        result = attendance_day_checking(
            str(self.specific_date), "08:00", employee=self.emp_a
        )
        self.assertEqual(result, "00:00")

    def test_specific_holiday_with_unassigned_emp_b_unchanged(self):
        """emp_b is NOT in the specific holiday — hour must stay unchanged."""
        result = attendance_day_checking(
            str(self.specific_date), "08:00", employee=self.emp_b
        )
        self.assertEqual(result, "08:00")

    def test_normal_date_always_unchanged(self):
        """Non-holiday date: minimum_hour unchanged regardless of employee."""
        for emp in (None, self.emp_a, self.emp_b):
            with self.subTest(employee=emp):
                result = attendance_day_checking(
                    str(self.normal_date), "08:00", employee=emp
                )
                self.assertEqual(result, "08:00")


# ─── 2. Attendance.adjust_minimum_hour() ──────────────────────────────────────


class TestAttendanceAdjustMinimumHour(HolidayFixtureMixin, TestCase):
    """
    Attendance.adjust_minimum_hour() must set minimum_hour='00:00' and
    is_holiday=True only for holidays applicable to the attendance's employee.
    """

    def _make_attendance(self, employee, att_date, minimum_hour="08:00"):
        """Return an unsaved Attendance instance with required fields set."""
        att = Attendance(
            employee_id=employee,
            attendance_date=att_date,
            shift_id=self.shift,
            attendance_day=self.shift_day,
            minimum_hour=minimum_hour,
            attendance_clock_in_date=att_date,
        )
        return att

    def test_global_holiday_zeroes_emp_a(self):
        att = self._make_attendance(self.emp_a, self.global_date)
        att.adjust_minimum_hour()
        self.assertEqual(att.minimum_hour, "00:00")
        self.assertTrue(att.is_holiday)

    def test_global_holiday_zeroes_emp_b(self):
        att = self._make_attendance(self.emp_b, self.global_date)
        att.adjust_minimum_hour()
        self.assertEqual(att.minimum_hour, "00:00")
        self.assertTrue(att.is_holiday)

    def test_specific_holiday_zeroes_assigned_emp_a(self):
        """emp_a is in the specific holiday — must be treated as holiday."""
        att = self._make_attendance(self.emp_a, self.specific_date)
        att.adjust_minimum_hour()
        self.assertEqual(att.minimum_hour, "00:00")
        self.assertTrue(att.is_holiday)

    def test_specific_holiday_does_not_zero_unassigned_emp_b(self):
        """emp_b is NOT in the specific holiday — minimum_hour must stay unchanged."""
        att = self._make_attendance(self.emp_b, self.specific_date)
        att.adjust_minimum_hour()
        self.assertNotEqual(att.minimum_hour, "00:00")
        self.assertFalse(att.is_holiday)

    def test_normal_date_sets_is_holiday_false(self):
        """Non-holiday date: is_holiday must be explicitly set to False."""
        for emp in (self.emp_a, self.emp_b):
            with self.subTest(employee=emp):
                att = self._make_attendance(emp, self.normal_date)
                att.is_holiday = True  # pre-set to confirm the else branch resets it
                att.adjust_minimum_hour()
                self.assertFalse(att.is_holiday)


# ─── 3. leave_dates filtering logic (work_records_change_month) ───────────────


class TestLeaveDatesFiltering(HolidayFixtureMixin, TestCase):
    """
    Mirrors the logic in work_records_change_month that builds leave_dates.
    Specific holiday dates must be filtered out so they don't mark the
    entire work-record column as a holiday for every employee.
    """

    def _build_leave_dates(self, target_date):
        """Replicate the view's leave_dates construction for a given month."""
        month, year = target_date.month, target_date.year
        specific_dates = set(
            Holidays.objects.filter(
                is_specific=True,
                start_date__month=month,
                start_date__year=year,
            ).values_list("start_date", flat=True)
        )
        return [d for d in monthly_leave_days(month, year) if d not in specific_dates]

    def test_global_holiday_included_in_leave_dates(self):
        """Global holiday must appear in leave_dates for all employees."""
        leave_dates = self._build_leave_dates(self.global_date)
        self.assertIn(self.global_date, leave_dates)

    def test_specific_holiday_excluded_from_leave_dates(self):
        """
        Specific holiday must NOT appear in leave_dates — it applies
        only to individual employees, not all columns.
        """
        leave_dates = self._build_leave_dates(self.specific_date)
        self.assertNotIn(self.specific_date, leave_dates)

    def test_normal_date_not_in_leave_dates(self):
        """A regular working day must not appear in leave_dates."""
        leave_dates = self._build_leave_dates(self.normal_date)
        self.assertNotIn(self.normal_date, leave_dates)


# ─── 4. Per-employee specific holiday dict (work_record_export) ───────────────


class TestExportPerEmployeeHoliday(HolidayFixtureMixin, TestCase):
    """
    Mirrors the logic in work_record_export that builds specific_employee_holidays.
    emp_a must have the specific holiday date; emp_b must not.
    """

    def _build_specific_employee_holidays(self, target_date):
        """Replicate the export view's per-employee holiday dict."""
        month, year = target_date.month, target_date.year
        result = {}
        for h in Holidays.objects.filter(
            is_specific=True,
            start_date__month=month,
            start_date__year=year,
        ).prefetch_related("employees"):
            for emp in h.employees.all():
                result.setdefault(emp.pk, set()).add(h.start_date)
        return result

    def test_assigned_employee_has_specific_holiday(self):
        """emp_a is in the specific holiday — must appear in per-employee dict."""
        emp_holidays = self._build_specific_employee_holidays(self.specific_date)
        self.assertIn(self.emp_a.pk, emp_holidays)
        self.assertIn(self.specific_date, emp_holidays[self.emp_a.pk])

    def test_unassigned_employee_has_no_specific_holiday(self):
        """emp_b is NOT in the specific holiday — must not appear."""
        emp_holidays = self._build_specific_employee_holidays(self.specific_date)
        emp_b_dates = emp_holidays.get(self.emp_b.pk, set())
        self.assertNotIn(self.specific_date, emp_b_dates)

    def test_global_holiday_not_in_specific_dict(self):
        """Global holidays must not appear in the per-employee specific dict."""
        emp_holidays = self._build_specific_employee_holidays(self.global_date)
        self.assertEqual(emp_holidays, {})
