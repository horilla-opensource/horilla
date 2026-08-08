"""Company isolation via HorillaCompanyManager + selected-company context."""

from datetime import date, timedelta

from django.test import TestCase

from base.models import Holidays
from horilla.testkit import CompanyFilterTestMixin, make_company


class HolidayCompanyIsolationTests(CompanyFilterTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = make_company("Company A")
        cls.company_b = make_company(
            "Company B",
            address="2 Other St",
            city="SF",
            zip="94105",
        )
        day_a = date.today() - timedelta(days=40)
        day_b = date.today() - timedelta(days=20)
        cls.holiday_a = Holidays.objects.create(
            name="Holiday A",
            start_date=day_a,
            end_date=day_a,
            company_id=cls.company_a,
        )
        cls.holiday_b = Holidays.objects.create(
            name="Holiday B",
            start_date=day_b,
            end_date=day_b,
            company_id=cls.company_b,
        )

    def test_company_a_sees_only_own_holidays(self):
        self.set_company_context(self.company_a.pk)
        visible = list(Holidays.objects.all())
        self.assertIn(self.holiday_a, visible)
        self.assertNotIn(self.holiday_b, visible)

    def test_company_b_sees_only_own_holidays(self):
        self.set_company_context(self.company_b.pk)
        visible = list(Holidays.objects.all())
        self.assertNotIn(self.holiday_a, visible)
        self.assertIn(self.holiday_b, visible)

    def test_entire_bypasses_company_filter(self):
        self.set_company_context(self.company_a.pk)
        all_rows = list(Holidays.objects.entire())
        self.assertIn(self.holiday_a, all_rows)
        self.assertIn(self.holiday_b, all_rows)

    def test_no_company_context_returns_unfiltered(self):
        self.clear_company_context()
        all_rows = list(Holidays.objects.all())
        self.assertIn(self.holiday_a, all_rows)
        self.assertIn(self.holiday_b, all_rows)
