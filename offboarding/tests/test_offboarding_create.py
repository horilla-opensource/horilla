"""Offboarding create smoke tests."""

from django.test import TestCase

from horilla.testkit import make_company
from offboarding.models import Offboarding, OffboardingGeneralSetting


class OffboardingCreateTests(TestCase):
    def test_create_seeds_stages(self):
        company = make_company("Offboard Co")
        process = Offboarding.objects.create(
            title="Exit Wave",
            description="Unit smoke offboarding",
            company_id=company,
        )
        self.assertGreaterEqual(process.offboardingstage_set.count(), 5)
        titles = set(process.offboardingstage_set.values_list("title", flat=True))
        self.assertIn("Exit interview", titles)

    def test_general_setting_defaults(self):
        company = make_company("Offboard Settings")
        setting = OffboardingGeneralSetting.objects.create(company_id=company)
        self.assertFalse(setting.resignation_request)
