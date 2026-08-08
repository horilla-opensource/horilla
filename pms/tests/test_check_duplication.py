"""PMS feedback duplication helper smoke tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from pms.methods import check_duplication


class CheckDuplicationTests(SimpleTestCase):
    def test_filters_already_requested_employees(self):
        emp_a, emp_b, emp_c = object(), object(), object()
        feedback = SimpleNamespace(
            subordinate_id=MagicMock(all=MagicMock(return_value=[emp_a])),
            colleague_id=MagicMock(all=MagicMock(return_value=[emp_b])),
            manager_id=None,
            employee_id=None,
        )
        updated = check_duplication(feedback, [emp_a, emp_b, emp_c])
        self.assertEqual(updated, [emp_c])
