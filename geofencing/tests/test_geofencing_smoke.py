"""Geofencing create smoke tests (Nominatim mocked)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from geofencing.models import GeoFencing
from horilla.testkit import make_company


class GeoFencingSmokeTests(TestCase):
    @patch("geofencing.models.Nominatim")
    def test_create_with_mocked_geocoder(self, nominatim_cls):
        nominatim_cls.return_value.reverse.return_value = MagicMock()
        company = make_company("Geo Co")
        geo = GeoFencing(
            latitude=12.97,
            longitude=77.59,
            radius_in_meters=100,
            company_id=company,
            start=False,
        )
        geo.save()
        self.assertIsNotNone(geo.pk)
        self.assertFalse(geo.start)
