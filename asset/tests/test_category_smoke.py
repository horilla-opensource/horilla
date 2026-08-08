"""Asset category smoke tests."""

from django.test import TestCase

from asset.models import AssetCategory


class AssetCategorySmokeTests(TestCase):
    def test_create_category(self):
        cat = AssetCategory.objects.create(
            asset_category_name="Laptops UnitTest",
            asset_category_description="Test category",
        )
        self.assertIsNotNone(cat.pk)
        self.assertEqual(str(cat), "Laptops UnitTest")
