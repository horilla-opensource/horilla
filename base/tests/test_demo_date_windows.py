"""Demo date-window helpers — no DB."""

from datetime import date, timedelta

from django.test import SimpleTestCase

from base.demo_data.dates import (
    attendance_dates_for_employee,
    should_be_present_today,
    spaced_dates,
    weekdays_inclusive,
)


class DemoDateWindowTests(SimpleTestCase):
    def test_weekdays_skip_saturday_sunday(self):
        days = weekdays_inclusive(date(2026, 8, 15), date(2026, 8, 23))
        self.assertTrue(all(d.weekday() < 5 for d in days))
        self.assertNotIn(date(2026, 8, 16), days)  # Sunday
        self.assertNotIn(date(2026, 8, 22), days)  # Saturday

    def test_spaced_dates_are_unique_and_bounded(self):
        start, end = date(2026, 2, 20), date(2026, 8, 19)
        dates = spaced_dates(start, end, 26, weekdays_only=True)
        self.assertEqual(len(dates), 26)
        self.assertEqual(len(set(dates)), 26)
        self.assertEqual(dates[0], weekdays_inclusive(start, end)[0])
        self.assertEqual(dates[-1], weekdays_inclusive(start, end)[-1])
        self.assertTrue(all(start <= d <= end for d in dates))
        self.assertTrue(all(d.weekday() < 5 for d in dates))

    def test_nobody_present_on_weekend(self):
        saturday = date(2026, 8, 22)
        self.assertFalse(should_be_present_today(1, saturday))
        self.assertFalse(should_be_present_today(87, saturday))

    def test_present_today_is_not_everyone(self):
        today = date(2026, 8, 19)  # Wednesday
        present = [i for i in range(1, 201) if should_be_present_today(i, today)]
        self.assertGreater(len(present), 100)
        self.assertLess(len(present), 200)

    def test_absent_employees_do_not_get_today_as_last_date(self):
        today = date(2026, 8, 19)
        start = today - timedelta(days=180)
        absent_id = 90  # 90 % 100 = 90, not < 87
        self.assertFalse(should_be_present_today(absent_id, today))
        dates = attendance_dates_for_employee(absent_id, start, today, 26)
        self.assertNotIn(today, dates)
        self.assertLess(max(dates), today)

    def test_present_employees_include_today_on_weekdays(self):
        today = date(2026, 8, 19)
        start = today - timedelta(days=180)
        present_id = 1
        self.assertTrue(should_be_present_today(present_id, today))
        dates = attendance_dates_for_employee(present_id, start, today, 26)
        self.assertEqual(dates[-1], today)
