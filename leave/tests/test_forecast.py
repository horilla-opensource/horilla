"""Tests for AvailableLeave.forcasted_leaves()."""

from datetime import date

from django.test import TestCase


class LeaveForecastTests(TestCase):
    def test_forcasted_leaves_before_reset_returns_0(self):
        from types import SimpleNamespace

        from leave.models import AvailableLeave

        avail = SimpleNamespace(
            leave_type_id=SimpleNamespace(
                total_days=12,
                leave_type_next_reset_date=lambda: date(2024, 6, 1),
            )
        )
        self.assertEqual(
            AvailableLeave.forcasted_leaves(avail, date(2024, 5, 1)),
            0,
        )

    def test_forcasted_leaves_on_or_after_reset_returns_total(self):
        from types import SimpleNamespace

        from leave.models import AvailableLeave

        avail = SimpleNamespace(
            leave_type_id=SimpleNamespace(
                total_days=12,
                leave_type_next_reset_date=lambda: date(2024, 6, 1),
            )
        )
        self.assertEqual(
            AvailableLeave.forcasted_leaves(avail, date(2024, 6, 1)),
            12,
        )

    def test_forcasted_leaves_parses_string_date(self):
        from types import SimpleNamespace

        from leave.models import AvailableLeave

        avail = SimpleNamespace(
            leave_type_id=SimpleNamespace(
                total_days=12,
                leave_type_next_reset_date=lambda: date(2024, 6, 1),
            )
        )
        self.assertEqual(
            AvailableLeave.forcasted_leaves(avail, "2024-06-15"),
            12,
        )
