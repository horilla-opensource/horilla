"""Tests for calculate_requested_days()."""

from datetime import date

from django.test import TestCase


class CalculateRequestedDaysTests(TestCase):
    def test_same_day_full(self):
        from leave.methods import calculate_requested_days

        d = date(2024, 3, 1)
        self.assertEqual(
            calculate_requested_days(d, d, "full_day", "full_day"),
            1,
        )

    def test_same_day_half(self):
        from leave.methods import calculate_requested_days

        d = date(2024, 3, 1)
        self.assertEqual(
            calculate_requested_days(d, d, "first_half", "first_half"),
            0.5,
        )

    def test_multi_day_full(self):
        from leave.methods import calculate_requested_days

        start = date(2024, 3, 1)
        end = date(2024, 3, 3)
        self.assertEqual(
            calculate_requested_days(start, end, "full_day", "full_day"),
            3,
        )

    def test_multi_day_half_ends(self):
        from leave.methods import calculate_requested_days

        start = date(2024, 3, 1)
        end = date(2024, 3, 3)
        self.assertEqual(
            calculate_requested_days(start, end, "second_half", "first_half"),
            2.0,
        )
