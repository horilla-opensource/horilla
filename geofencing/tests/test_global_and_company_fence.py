"""A global geofence and company geofences must work together (issue #1286).

Reported as: after a global fence exists, adding a fence for a company answers "Not valid", and the
global fence is not applied to any company. Both come from the same place:

* the setup page validated a company's new fence before giving it its company, and the model
  allows only one fence without a company - so as soon as a global fence existed, the new one
  (still company-less at that moment) was rejected;
* every lookup asked only for ``company_id=<this company>``, so the global fence was never used.

A company's own fence overrides the global one; a company with none falls back to it.
Nominatim is mocked - the model asks it to reverse-geocode on save.
"""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.urls import reverse

from geofencing.models import GeoFencing
from horilla.testkit import make_company, make_employee, make_user

FENCE = {
    "latitude": "12.97",
    "longitude": "77.59",
    "radius_in_meters": "150",
    "start": "on",
}


def make_fence(company=None, **extra):
    values = {
        "latitude": 12.97,
        "longitude": 77.59,
        "radius_in_meters": 100,
        "start": True,
    }
    values.update(extra)
    return GeoFencing.objects.create(company_id=company, **values)


@patch("geofencing.models.Nominatim")
class FenceForCompanyTests(TestCase):
    def setUp(self):
        self.acme = make_company("Acme")
        self.globex = make_company("Globex", hq=False)

    def test_a_company_without_a_fence_uses_the_global_one(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        global_fence = make_fence(None, radius_in_meters=500)
        self.assertEqual(GeoFencing.for_company(self.acme), global_fence)
        self.assertEqual(GeoFencing.for_company(self.globex), global_fence)

    def test_a_companys_own_fence_overrides_the_global_one(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None, radius_in_meters=500)
        own = make_fence(self.acme, radius_in_meters=50)
        self.assertEqual(GeoFencing.for_company(self.acme), own)

    def test_no_fence_at_all_is_none(self, nominatim):
        self.assertIsNone(GeoFencing.for_company(self.acme))
        self.assertIsNone(GeoFencing.for_company(None))

    def test_the_web_punch_check_follows_the_global_fence(self, nominatim):
        from attendance.methods.utils import geofence_denial_web

        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None, radius_in_meters=100)
        far_away = RequestFactory().get("/", {"latitude": "40.0", "longitude": "-74.0"})
        self.assertIsNotNone(geofence_denial_web(far_away, self.acme))
        nearby = RequestFactory().get("/", {"latitude": "12.97", "longitude": "77.59"})
        self.assertIsNone(geofence_denial_web(nearby, self.acme))

    def test_a_switched_off_global_fence_blocks_nobody(self, nominatim):
        from attendance.methods.utils import geofence_denial_web

        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None, start=False)
        far_away = RequestFactory().get("/", {"latitude": "40.0", "longitude": "-74.0"})
        self.assertIsNone(geofence_denial_web(far_away, self.acme))


@patch("geofencing.models.Nominatim")
class ApiPunchCheckTests(TestCase):
    """The mobile/API punch check asks the company for its fence, and falls back to the global one."""

    LOCATION_CHECK = "geofencing.views.GeoFencingEmployeeLocationCheckAPIView.post"

    def request_for(self, company):
        from types import SimpleNamespace

        return SimpleNamespace(
            user=SimpleNamespace(
                id=1, employee_get=SimpleNamespace(get_company=lambda: company)
            ),
            data={},
        )

    def company_without_a_fence(self):
        from django.core.exceptions import ObjectDoesNotExist

        class Company:
            @property
            def geo_fencing(self):
                raise ObjectDoesNotExist("no fence")

        return Company()

    def test_the_global_fence_is_enforced_for_a_company_without_one(self, nominatim):
        from horilla_api.api_views.attendance.views import geofence_denial

        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None, start=True)
        with patch(self.LOCATION_CHECK) as location_check:
            from types import SimpleNamespace

            location_check.return_value = SimpleNamespace(status_code=200)
            geofence_denial(self.request_for(self.company_without_a_fence()))
        location_check.assert_called_once()

    def test_no_fence_at_all_lets_the_punch_through(self, nominatim):
        from horilla_api.api_views.attendance.views import geofence_denial

        with patch(self.LOCATION_CHECK) as location_check:
            self.assertIsNone(
                geofence_denial(self.request_for(self.company_without_a_fence()))
            )
        location_check.assert_not_called()


@patch("geofencing.models.Nominatim")
class SetupPageTests(TestCase):
    def setUp(self):
        self.acme = make_company("Acme")
        self.admin = make_user("fence-admin", is_superuser=True)
        make_employee(
            company=self.acme, email="fence-admin@test.horilla", user=self.admin
        )
        self.client.force_login(self.admin)
        self.url = reverse("geo-config")

    def post_for(self, company_id, **extra):
        session = self.client.session
        session["selected_company"] = company_id
        session.save()
        response = self.client.post(self.url, {**FENCE, **extra})
        return response

    def test_a_company_fence_can_be_added_after_a_global_one(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None)
        response = self.post_for(str(self.acme.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GeoFencing.objects.filter(company_id=self.acme).exists())
        self.assertEqual(GeoFencing.objects.count(), 2)

    def test_the_global_fence_can_still_be_edited(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        global_fence = make_fence(None, radius_in_meters=100)
        self.post_for("all", radius_in_meters="250")
        global_fence.refresh_from_db()
        self.assertEqual(global_fence.radius_in_meters, 250)
        self.assertEqual(GeoFencing.objects.count(), 1)

    def test_a_second_global_fence_is_still_refused(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        make_fence(None)
        other = GeoFencing(
            latitude=1, longitude=1, radius_in_meters=10, company_id=None
        )
        with self.assertRaises(Exception):
            other.save()

    def test_editing_a_company_fence_updates_it_in_place(self, nominatim):
        nominatim.return_value.reverse.return_value = MagicMock()
        own = make_fence(self.acme, radius_in_meters=100)
        self.post_for(str(self.acme.pk), radius_in_meters="300")
        own.refresh_from_db()
        self.assertEqual(own.radius_in_meters, 300)
        self.assertEqual(GeoFencing.objects.count(), 1)
