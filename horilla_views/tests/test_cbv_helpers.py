"""Horilla views CBV helper smoke tests."""

from django.test import SimpleTestCase

from horilla_views.cbv_methods import get_short_uuid, merge_dicts


class CbvHelperTests(SimpleTestCase):
    def test_short_uuid_prefix(self):
        value = get_short_uuid(8)
        self.assertTrue(value.startswith("hlv"))
        self.assertEqual(len(value), 3 + 8)

    def test_merge_dicts_extends_lists(self):
        merged = merge_dicts(
            {"k": {"M": [1]}},
            {"k": {"M": [2], "N": [3]}},
        )
        self.assertEqual(merged["k"]["M"], [1, 2])
        self.assertEqual(merged["k"]["N"], [3])
