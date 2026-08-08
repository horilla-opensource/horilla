"""Audit activity-feed helper smoke tests."""

from datetime import date, datetime, timedelta

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from horilla_audit.activity_feed import history_action_phrase, history_date_label


class HistoryActionPhraseTests(SimpleTestCase):
    def test_empty_changes(self):
        self.assertEqual(history_action_phrase([]), _("updated record"))

    def test_single_field(self):
        phrase = history_action_phrase([{"field_label": "Department"}])
        self.assertIn("department", phrase.lower())


class HistoryDateLabelTests(SimpleTestCase):
    def test_today_and_yesterday(self):
        today = date(2026, 8, 7)
        self.assertEqual(
            history_date_label(datetime(2026, 8, 7, 12, 0), today=today),
            _("Today"),
        )
        self.assertEqual(
            history_date_label(datetime(2026, 8, 6, 12, 0), today=today),
            _("Yesterday"),
        )
