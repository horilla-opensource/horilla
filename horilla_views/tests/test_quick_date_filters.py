"""Quick Date menu ranges (horilla_views.cbv_methods.get_quick_date_filters)."""

import re
from datetime import date, datetime
from unittest import mock

from django.test import SimpleTestCase
from django.utils import translation

from horilla_views.cbv_methods import get_quick_date_filters, week_start
from horilla_views.generic.cbv.views import QUICK_DATE_RANGES

FIELDS = ("attendance_date", "attendance_date__gte", "attendance_date__lte")
WEDNESDAY = datetime(2026, 10, 21, 9, 30)


def ranges_on(now, language):
    """{label: (from, to)} as the menu would set them on `now`."""
    with mock.patch("horilla_views.cbv_methods.datetime") as clock:
        clock.now.return_value = now
        with translation.override(language):
            filters = get_quick_date_filters(QUICK_DATE_RANGES, FIELDS)
            out = {}
            for label, attrs in filters:
                values = dict(re.findall(r"\[name=(\w+)\]'\)\.val\('([^']*)'\)", attrs))
                out[str(label)] = (
                    values.get("attendance_date__gte") or values.get("attendance_date"),
                    values.get("attendance_date__lte") or values.get("attendance_date"),
                )
            return out


class QuickDateFilterTests(SimpleTestCase):
    def test_week_start_follows_the_language(self):
        with translation.override("en-gb"):  # Monday
            self.assertEqual(week_start(date(2026, 10, 21)), date(2026, 10, 19))
            self.assertEqual(week_start(date(2026, 10, 19)), date(2026, 10, 19))
            self.assertEqual(week_start(date(2026, 10, 25)), date(2026, 10, 19))
        with translation.override("en"):  # Sunday
            self.assertEqual(week_start(date(2026, 10, 21)), date(2026, 10, 18))
            self.assertEqual(week_start(date(2026, 10, 18)), date(2026, 10, 18))

    def test_this_week_and_last_week_are_calendar_weeks(self):
        uk = ranges_on(WEDNESDAY, "en-gb")
        self.assertEqual(uk["This Week"], ("2026-10-19", "2026-10-25"))
        self.assertEqual(uk["Last Week"], ("2026-10-12", "2026-10-18"))
        us = ranges_on(WEDNESDAY, "en")
        self.assertEqual(us["This Week"], ("2026-10-18", "2026-10-24"))
        self.assertEqual(us["Last Week"], ("2026-10-11", "2026-10-17"))

    def test_seven_day_ranges_include_today(self):
        uk = ranges_on(WEDNESDAY, "en-gb")
        self.assertEqual(uk["Last 7 Days"], ("2026-10-15", "2026-10-21"))
        self.assertEqual(uk["Next 7 Days"], ("2026-10-21", "2026-10-27"))

    def test_single_days_are_unchanged(self):
        uk = ranges_on(WEDNESDAY, "en-gb")
        self.assertEqual(uk["Yesterday"], ("2026-10-20", "2026-10-20"))
        self.assertEqual(uk["Today"], ("2026-10-21", "2026-10-21"))
        self.assertEqual(uk["Tomorrow"], ("2026-10-22", "2026-10-22"))
