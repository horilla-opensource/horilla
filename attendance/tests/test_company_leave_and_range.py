"""Tests for company weekly offs and multi-day holiday ranges."""

from datetime import date, timedelta

from django.test import TestCase

from attendance.methods.utils import attendance_day_checking
from attendance.tests.fixtures import HolidayFixtureMixin
from base.models import Holidays


class TestCompanyLeaveAndRange(HolidayFixtureMixin, TestCase):
    def test_sunday_company_leave_zeroes_minimum_hour(self):
        from base.models import CompanyLeaves

        # Find a past Sunday that is not already a holiday fixture date
        sunday = date.today() - timedelta(days=90)
        while sunday.weekday() != 6:
            sunday -= timedelta(days=1)
        company_leave = CompanyLeaves.objects.create(
            based_on_week=None,
            based_on_week_day="6",
        )
        company_leave.company_id.set([self.company])
        self.assertEqual(
            attendance_day_checking(str(sunday), "08:00"),
            "00:00",
        )
        monday = sunday + timedelta(days=1)
        self.assertEqual(
            attendance_day_checking(str(monday), "08:00"),
            "08:00",
        )

    def test_multi_day_holiday_zeroes_middle_day(self):
        start = date.today() - timedelta(days=120)
        # Avoid colliding with fixture holiday dates
        while start in {self.global_date, self.specific_date, self.normal_date}:
            start -= timedelta(days=1)
        end = start + timedelta(days=2)
        Holidays.objects.create(
            name="Multi Day Holiday",
            start_date=start,
            end_date=end,
            is_specific=False,
            company_id=self.company,
        )
        middle = start + timedelta(days=1)
        outside = end + timedelta(days=1)
        self.assertEqual(attendance_day_checking(str(middle), "08:00"), "00:00")
        self.assertEqual(attendance_day_checking(str(outside), "08:00"), "08:00")
