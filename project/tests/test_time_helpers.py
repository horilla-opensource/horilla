"""Project time helper smoke tests."""

from django.test import SimpleTestCase

from project.methods import strtime_seconds


class StrtimeSecondsTests(SimpleTestCase):
    def test_hours_and_minutes(self):
        self.assertEqual(strtime_seconds("1:30"), 5400)

    def test_with_seconds(self):
        self.assertEqual(strtime_seconds("0:0:5"), 5)
