"""Report dynamic filter util smoke tests."""

from datetime import date

from django.test import SimpleTestCase

from report.dynamic_filter_utils import parse_multi_value, resolve_relative_date_range


class ResolveRelativeDateRangeTests(SimpleTestCase):
    def test_today(self):
        start, end = resolve_relative_date_range("today")
        self.assertEqual(start, date.today())
        self.assertEqual(end, date.today())

    def test_unknown_returns_none(self):
        self.assertIsNone(resolve_relative_date_range("not_an_op"))


class ParseMultiValueTests(SimpleTestCase):
    def test_json_array(self):
        self.assertEqual(parse_multi_value('["a","b"]'), ["a", "b"])

    def test_plain_string(self):
        self.assertEqual(parse_multi_value("Sales"), ["Sales"])
