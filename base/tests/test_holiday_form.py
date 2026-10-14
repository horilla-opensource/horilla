"""Tests for HolidayForm: company-less holidays, Available for All, uniqueness."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from base.forms import HolidayForm
from base.models import Department, Holidays
from horilla.testkit import make_company


class HolidayFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company("Holiday Corp")
        cls.other = make_company("Other Corp")
        cls.dept = Department.objects.create(department="Ops")

    def _data(self, **extra):
        data = {
            "name": "Founders Day",
            "start_date": "2026-11-01",
            "end_date": "2026-11-01",
            "available_for_all": "on",
        }
        data.update(extra)
        return data

    def test_global_holiday_without_company(self):
        form = HolidayForm(self._data())
        self.assertTrue(form.is_valid(), form.errors)
        holiday = form.save()
        self.assertIsNone(holiday.company_id)
        self.assertFalse(holiday.is_specific)

    def test_available_for_all_clears_selection(self):
        holiday = Holidays.objects.create(
            name="X",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            is_specific=True,
        )
        holiday.department.add(self.dept)
        form = HolidayForm(
            self._data(
                start_date="2026-11-02",
                end_date="2026-11-02",
                department=[self.dept.pk],
            ),
            instance=holiday,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        holiday.refresh_from_db()
        self.assertFalse(holiday.is_specific)
        self.assertFalse(holiday.department.exists())

    def test_restricted_requires_a_selection(self):
        data = self._data()
        del data["available_for_all"]
        form = HolidayForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("department", form.errors)

    def test_restricted_by_department_saved(self):
        data = self._data(department=[self.dept.pk])
        del data["available_for_all"]
        form = HolidayForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        holiday = form.save()
        self.assertTrue(holiday.is_specific)
        self.assertEqual(list(holiday.department.all()), [self.dept])

    def test_duplicate_global_rejected(self):
        self.assertTrue((f := HolidayForm(self._data())).is_valid())
        f.save()
        form = HolidayForm(self._data(name="Again"))
        self.assertFalse(form.is_valid())

    def test_duplicate_same_company_rejected_other_company_allowed(self):
        f = HolidayForm(self._data(company_id=self.company.pk))
        self.assertTrue(f.is_valid(), f.errors)
        f.save()
        self.assertFalse(HolidayForm(self._data(company_id=self.company.pk)).is_valid())
        self.assertTrue(HolidayForm(self._data(company_id=self.other.pk)).is_valid())
        # a global holiday on the same dates is a different scope
        self.assertTrue(HolidayForm(self._data()).is_valid())

    def test_model_level_full_clean(self):
        Holidays.objects.create(
            name="A", start_date=date(2026, 12, 1), end_date=date(2026, 12, 1)
        )
        with self.assertRaises(ValidationError):
            Holidays(
                name="B", start_date=date(2026, 12, 1), end_date=date(2026, 12, 1)
            ).full_clean()


class HolidayViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from horilla.testkit import make_employee, make_user

        cls.company = make_company("View Corp")
        cls.user = make_user("holiday_admin", is_superuser=True)
        make_employee(company=cls.company, email="ha@test.horilla", user=cls.user)
        cls.holiday = Holidays.objects.create(
            name="Existing",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 5),
            company_id=cls.company,
        )

    def setUp(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["selected_company"] = str(self.company.pk)
        session.save()
        self.hx = {"HTTP_HX_REQUEST": "true"}

    def test_company_field_not_forced_hidden(self):
        from django.urls import reverse

        response = self.client.get(reverse("holiday-creation"), **self.hx)
        self.assertContains(response, 'name="company_id"')
        self.assertNotContains(response, 'type="hidden" name="company_id"')
        self.assertContains(response, "All Companies")

    def test_duplicate_form_has_all_fields_prefilled(self):
        from django.urls import reverse

        response = self.client.get(
            reverse("duplicate-holiday", kwargs={"pk": self.holiday.pk}), **self.hx
        )
        for field in ("available_for_all", "department", "job_position", "company_id"):
            self.assertContains(response, f'name="{field}"')
        self.assertContains(response, "Existing (copy)")

    def test_duplicate_post_shows_unique_error(self):
        from django.urls import reverse

        response = self.client.post(
            reverse("duplicate-holiday", kwargs={"pk": self.holiday.pk}),
            {
                "name": "Dup",
                "start_date": "2026-11-05",
                "end_date": "2026-11-05",
                "available_for_all": "on",
                "company_id": self.company.pk,
            },
            **self.hx,
        )
        self.assertContains(response, "already exists for this date range")
        self.assertEqual(Holidays.objects.count(), 1)


class HolidayImportTests(TestCase):
    def test_csv_import_company_column(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from base.views import csv_holiday_import

        company = make_company("Import Corp")
        csv_data = (
            "Holiday Name,Start Date,End Date,Recurring,Company\n"
            "Scoped,2026-01-01,2026-01-01,no,import corp\n"
            "Global,2026-01-01,2026-01-01,no,\n"
            "Legacy Four Cols,2026-02-01,2026-02-01,yes\n"
            "Bad,2026-03-01,2026-03-01,no,Nowhere Ltd\n"
            "Dup,2026-01-01,2026-01-01,no,Import Corp\n"
        )
        errors, total = csv_holiday_import(
            SimpleUploadedFile("h.csv", csv_data.encode(), content_type="text/csv")
        )
        self.assertEqual(total, 5)
        self.assertEqual(Holidays.objects.entire().count(), 3)
        self.assertTrue(
            Holidays.objects.entire().filter(name="Scoped", company_id=company).exists()
        )
        self.assertTrue(
            Holidays.objects.entire()
            .filter(name="Global", company_id__isnull=True)
            .exists()
        )
        messages = {k for e in errors for k in e}
        self.assertIn("Company Error", messages)
        self.assertIn("Duplicate Error", messages)

    def test_csv_import_with_selected_company(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from base.views import csv_holiday_import

        company = make_company("Sel Corp")
        make_company("Other Import Corp")
        csv_data = (
            "Holiday Name,Start Date,End Date,Recurring,Company\n"
            "Ok,2026-04-01,2026-04-01,no,Sel Corp\n"
            "Blank,2026-04-02,2026-04-02,no,\n"
            "Wrong,2026-04-03,2026-04-03,no,Other Import Corp\n"
        )
        errors, total = csv_holiday_import(
            SimpleUploadedFile("h.csv", csv_data.encode(), content_type="text/csv"),
            company,
        )
        self.assertEqual(
            list(Holidays.objects.entire().values_list("name", flat=True)), ["Ok"]
        )
        self.assertEqual(sum("Company Error" in e for e in errors), 2)
