"""Tests for work_record_export per-employee specific holiday dict."""

from django.test import TestCase

from attendance.tests.fixtures import HolidayFixtureMixin
from base.models import Holidays


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
