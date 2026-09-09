"""A FilterSet must accept a plain dict as `data`, not only a QueryDict.

CybroOdooDev/Horilla#3313. `HorillaFilterSet` called `self.data.getlist(...)`
at six places. django-filter accepts any mapping as `data`, and eight call
sites in the dashboards pass a dict literal --
`EmployeeFilter({"not_in_yet": today})` and friends. Every one of them raised
`AttributeError: 'dict' object has no attribute 'getlist'`, returned a 500, and
left the dashboard card it feeds spinning on "Loading..." indefinitely. A
customer reported it as "some elements are stuck loading" after a v1 to v2
migration; it is not migration-related, it affects every 2.1.x install.

The dict cases below are the real call sites, by class. The QueryDict and None
cases are here because the fix would be worthless if it broke the ordinary
request path that every filter form in the product uses.
"""

import datetime

from django.http import QueryDict
from django.test import SimpleTestCase

from asset.filters import AssetHistoryFilter
from employee.filters import EmployeeFilter
from payroll.filters import ReimbursementFilter


class FilterSetDictDataTests(SimpleTestCase):
    databases = {"default"}

    def _build(self, factory):
        """Construct and touch .qs -- the error surfaced during __init__."""
        instance = factory()
        instance.qs.query  # force the queryset to build
        return instance

    def test_employee_filter_accepts_a_dict(self):
        today = datetime.date.today()
        for key in ("not_in_yet", "not_out_yet"):
            with self.subTest(key=key):
                self._build(lambda: EmployeeFilter({key: today}))

    def test_asset_history_filter_accepts_a_dict(self):
        self._build(lambda: AssetHistoryFilter({"returned_assets": "True"}))

    def test_reimbursement_filter_accepts_a_dict(self):
        self._build(lambda: ReimbursementFilter({"status": "requested"}))

    def test_a_dict_value_that_is_already_a_list_is_not_rewrapped(self):
        f = self._build(lambda: EmployeeFilter({"custom_field": ["a", "b"]}))
        self.assertEqual(f._data_getlist("custom_field"), ["a", "b"])

    def test_a_scalar_dict_value_reads_back_as_one_element(self):
        f = self._build(lambda: EmployeeFilter({"custom_field": "a"}))
        self.assertEqual(f._data_getlist("custom_field"), ["a"])

    def test_a_missing_key_reads_back_empty(self):
        f = self._build(lambda: EmployeeFilter({"other": "x"}))
        self.assertEqual(f._data_getlist("custom_field"), [])

    # --- the ordinary request path must be untouched ---

    def test_querydict_still_uses_getlist_semantics(self):
        data = QueryDict("custom_field=a&custom_field=b")
        f = self._build(lambda: EmployeeFilter(data))
        self.assertEqual(f._data_getlist("custom_field"), ["a", "b"])

    def test_none_data_is_still_accepted(self):
        f = self._build(lambda: EmployeeFilter(None))
        self.assertEqual(f._data_getlist("custom_field"), [])
