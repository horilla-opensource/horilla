"""
Tests for accessibility module models and methods.

Covers DefaultAccessibility model CRUD, ACCESSBILITY_FEATURE choices registry,
and the check_is_accessible() business logic method.
"""

from accessibility.accessibility import ACCESSBILITY_FEATURE
from accessibility.methods import check_is_accessible
from accessibility.models import DefaultAccessibility
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# ACCESSBILITY_FEATURE Registry Tests
# ---------------------------------------------------------------------------
class AccessibilityFeatureRegistryTests(HorillaTestCase):
    """Tests for the ACCESSBILITY_FEATURE choices list."""

    def test_feature_registry_is_list_of_tuples(self):
        self.assertIsInstance(ACCESSBILITY_FEATURE, list)
        for item in ACCESSBILITY_FEATURE:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_feature_registry_contains_employee_view(self):
        keys = [choice[0] for choice in ACCESSBILITY_FEATURE]
        self.assertIn("employee_view", keys)

    def test_feature_registry_contains_employee_detailed_view(self):
        keys = [choice[0] for choice in ACCESSBILITY_FEATURE]
        self.assertIn("employee_detailed_view", keys)


# ---------------------------------------------------------------------------
# DefaultAccessibility Model Tests
# ---------------------------------------------------------------------------
class DefaultAccessibilityModelTests(HorillaTestCase):
    """CRUD and field tests for DefaultAccessibility."""

    def test_create_default_accessibility(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=False,
            is_enabled=True,
        )
        self.assertIsNotNone(da.pk)
        self.assertEqual(da.feature, "employee_view")

    def test_exclude_all_default_false(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
        )
        self.assertFalse(da.exclude_all)

    def test_is_enabled_default_true(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
        )
        self.assertTrue(da.is_enabled)

    def test_employees_m2m(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            is_enabled=True,
        )
        da.employees.add(self.admin_employee, self.regular_employee)
        self.assertEqual(da.employees.count(), 2)
        self.assertIn(self.admin_employee, da.employees.all())

    def test_update_accessibility(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=False,
        )
        da.exclude_all = True
        da.save()
        da.refresh_from_db()
        self.assertTrue(da.exclude_all)

    def test_delete_accessibility(self):
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
        )
        pk = da.pk
        da.delete()
        self.assertFalse(DefaultAccessibility.objects.filter(pk=pk).exists())

    def test_filter_json_field(self):
        filter_data = {"department": "Engineering", "level": 3}
        da = DefaultAccessibility.objects.create(
            feature="employee_detailed_view",
            filter=filter_data,
        )
        da.refresh_from_db()
        self.assertEqual(da.filter, filter_data)


# ---------------------------------------------------------------------------
# check_is_accessible() Method Tests
# ---------------------------------------------------------------------------
class CheckIsAccessibleTests(HorillaTestCase):
    """Tests for the check_is_accessible() business logic method."""

    def test_no_rule_returns_true(self):
        """When no DefaultAccessibility rule exists for a feature, access is allowed."""
        result = check_is_accessible(
            "employee_view", "test_cache_key_1", self.admin_employee
        )
        self.assertTrue(result)

    def test_none_feature_returns_true(self):
        """When feature is None/empty, access is allowed."""
        result = check_is_accessible(None, "test_cache_key_2", self.admin_employee)
        self.assertTrue(result)

    def test_exclude_all_returns_false(self):
        """When exclude_all=True, no employee can access the feature."""
        DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=True,
            is_enabled=True,
        )
        result = check_is_accessible(
            "employee_view", "test_cache_key_3", self.admin_employee
        )
        self.assertFalse(result)

    def test_employee_in_allow_list_returns_true(self):
        """Employee explicitly added to the allow list can access the feature."""
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=False,
            is_enabled=True,
        )
        da.employees.add(self.admin_employee)
        result = check_is_accessible(
            "employee_view", "test_cache_key_4", self.admin_employee
        )
        self.assertTrue(result)

    def test_employee_not_in_allow_list_returns_false(self):
        """Employee NOT in allow list is denied access when a rule exists."""
        da = DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=False,
            is_enabled=True,
        )
        da.employees.add(self.manager_employee)  # only manager allowed
        result = check_is_accessible(
            "employee_view", "test_cache_key_5", self.regular_employee
        )
        self.assertFalse(result)

    def test_disabled_rule_returns_true(self):
        """When is_enabled=False, the rule is ignored and access is allowed."""
        DefaultAccessibility.objects.create(
            feature="employee_view",
            filter={},
            exclude_all=True,
            is_enabled=False,
        )
        result = check_is_accessible(
            "employee_view", "test_cache_key_6", self.admin_employee
        )
        self.assertTrue(result)

    def test_no_employee_returns_false(self):
        """When employee is None, access is denied."""
        result = check_is_accessible("employee_view", "test_cache_key_7", None)
        self.assertFalse(result)
