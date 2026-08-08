"""Automation condition helper smoke tests."""

from django.test import SimpleTestCase

from employee.models import Employee
from horilla_automations.methods.methods import (
    evaluate_condition,
    get_model_class,
    split_query_string,
)


class EvaluateConditionTests(SimpleTestCase):
    def test_equality(self):
        self.assertTrue(evaluate_condition(1, "==", 1))
        self.assertTrue(evaluate_condition(1, "!=", 2))

    def test_invalid_operator(self):
        with self.assertRaises(ValueError):
            evaluate_condition(1, ">>>", 2)


class AutomationHelperTests(SimpleTestCase):
    def test_get_model_class(self):
        self.assertIs(get_model_class("employee.models.Employee"), Employee)

    def test_split_query_string(self):
        parts = split_query_string("a=1&logic=b=2")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0].get("a"), "1")
