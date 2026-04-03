"""
Unit tests for base module forms.

Covers CSS class injection on the ModelForm base class, and validation /
field behavior for CompanyForm, DepartmentForm, TagsForm, and HolidayForm.
"""

from datetime import date, timedelta

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

from base.forms import CompanyForm, DepartmentForm, HolidayForm, ModelForm, TagsForm
from base.models import Tags
from base.tests.factories import CompanyFactory
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# Helper: minimal ModelForm subclass for testing CSS injection
# ---------------------------------------------------------------------------
class _DummyModel:
    """Stub used only to build a throwaway ModelForm for widget tests."""

    pass


class _CSSTestForm(ModelForm):
    """
    A ModelForm subclass with one field of each major widget type so we can
    verify the CSS-class injection logic in ModelForm.__init__.
    """

    text_field = forms.CharField(label="Name")
    email_field = forms.EmailField(label="Email")
    number_field = forms.IntegerField(label="Amount")
    select_field = forms.ChoiceField(
        label="Choice",
        choices=[("a", "A"), ("b", "B")],
    )
    textarea_field = forms.CharField(
        label="Notes",
        widget=forms.Textarea,
    )
    checkbox_field = forms.BooleanField(
        label="Active",
        required=False,
    )
    date_field = forms.DateField(
        label="Start",
        widget=forms.DateInput,
    )
    time_field = forms.TimeField(
        label="Clock In",
        widget=forms.TimeInput,
    )

    class Meta:
        model = Tags  # reuse a real model to keep ModelForm happy
        fields = []  # no model fields; we only test the manually declared ones


# ===========================================================================
# 1. ModelForm Base — CSS class injection (~8 tests)
# ===========================================================================
class ModelFormCSSInjectionTests(HorillaTestCase):
    """Verify that ModelForm.__init__ applies the correct CSS classes."""

    def _make_form(self):
        return _CSSTestForm()

    # -- Text / Number / Email inputs ---
    def test_text_input_gets_form_control(self):
        """TextInput widgets receive 'oh-input' and 'form-control'."""
        form = self._make_form()
        css = form.fields["text_field"].widget.attrs.get("class", "")
        self.assertIn("oh-input", css)
        self.assertIn("form-control", css)

    def test_email_input_gets_form_control(self):
        """EmailInput widgets receive 'form-control'."""
        form = self._make_form()
        css = form.fields["email_field"].widget.attrs.get("class", "")
        self.assertIn("form-control", css)

    def test_number_input_gets_form_control(self):
        """NumberInput widgets receive 'form-control'."""
        form = self._make_form()
        css = form.fields["number_field"].widget.attrs.get("class", "")
        self.assertIn("form-control", css)

    # -- Select ---
    def test_select_gets_oh_select(self):
        """Select widgets receive 'oh-select' CSS class."""
        form = self._make_form()
        css = form.fields["select_field"].widget.attrs.get("class", "")
        self.assertIn("oh-select", css)

    # -- Textarea ---
    def test_textarea_gets_form_control(self):
        """Textarea widgets receive 'form-control'."""
        form = self._make_form()
        css = form.fields["textarea_field"].widget.attrs.get("class", "")
        self.assertIn("form-control", css)

    def test_textarea_rows_and_cols(self):
        """Textarea widgets get rows=2 and cols=40 by default."""
        form = self._make_form()
        attrs = form.fields["textarea_field"].widget.attrs
        self.assertEqual(attrs.get("rows"), 2)
        self.assertEqual(attrs.get("cols"), 40)

    # -- Checkbox ---
    def test_checkbox_gets_oh_switch(self):
        """CheckboxInput widgets receive 'oh-switch__checkbox'."""
        form = self._make_form()
        css = form.fields["checkbox_field"].widget.attrs.get("class", "")
        self.assertIn("oh-switch__checkbox", css)

    # -- Date / Time ---
    def test_date_input_type_set(self):
        """DateInput widget gets input_type='date'."""
        form = self._make_form()
        widget = form.fields["date_field"].widget
        self.assertEqual(widget.input_type, "date")

    def test_time_input_type_set(self):
        """TimeInput widget gets input_type='time'."""
        form = self._make_form()
        widget = form.fields["time_field"].widget
        self.assertEqual(widget.input_type, "time")


# ===========================================================================
# 2. CompanyForm (~6 tests)
# ===========================================================================
class CompanyFormTests(HorillaTestCase):
    """Tests for CompanyForm validation and field handling."""

    def _valid_data(self, **overrides):
        data = {
            "company": "Acme Corp",
            "address": "100 Main St",
            "country": "US",
            "state": "CA",
            "city": "LA",
            "zip": "90001",
        }
        data.update(overrides)
        return data

    def _valid_icon(self):
        """Return a small valid PNG file for the icon field."""
        return SimpleUploadedFile(
            "icon.png",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
            content_type="image/png",
        )

    def test_valid_data_is_valid(self):
        """CompanyForm accepts valid company data with icon."""
        form = CompanyForm(
            data=self._valid_data(),
            files={"icon": self._valid_icon()},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_company(self):
        """CompanyForm.save() persists a new Company."""
        form = CompanyForm(
            data=self._valid_data(),
            files={"icon": self._valid_icon()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        company = form.save()
        self.assertIsNotNone(company.pk)
        self.assertEqual(company.company, "Acme Corp")

    def test_company_name_required(self):
        """Company name is required."""
        form = CompanyForm(data=self._valid_data(company=""))
        self.assertFalse(form.is_valid())
        self.assertIn("company", form.errors)

    def test_address_required(self):
        """Address is required."""
        form = CompanyForm(data=self._valid_data(address=""))
        self.assertFalse(form.is_valid())
        self.assertIn("address", form.errors)

    def test_excludes_date_format_and_time_format(self):
        """Meta.exclude removes date_format, time_format, is_active."""
        form = CompanyForm()
        self.assertNotIn("date_format", form.fields)
        self.assertNotIn("time_format", form.fields)
        self.assertNotIn("is_active", form.fields)

    def test_icon_oversized_file_rejected(self):
        """validate_image rejects files larger than 5 MB."""
        big_file = SimpleUploadedFile(
            "big.png",
            b"\x00" * (6 * 1024 * 1024),  # 6 MB
            content_type="image/png",
        )
        form = CompanyForm(data=self._valid_data(), files={"icon": big_file})
        self.assertFalse(form.is_valid())
        self.assertIn("icon", form.errors)


# ===========================================================================
# 3. DepartmentForm (~5 tests)
# ===========================================================================
class DepartmentFormTests(HorillaTestCase):
    """Tests for DepartmentForm."""

    def test_valid_data_is_valid(self):
        """DepartmentForm accepts a department name."""
        form = DepartmentForm(data={"department": "Engineering"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_department(self):
        """DepartmentForm.save() persists a new Department."""
        form = DepartmentForm(data={"department": "Sales"})
        self.assertTrue(form.is_valid(), form.errors)
        dept = form.save()
        self.assertIsNotNone(dept.pk)
        self.assertEqual(dept.department, "Sales")

    def test_department_name_required(self):
        """Department name cannot be blank."""
        form = DepartmentForm(data={"department": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("department", form.errors)

    def test_company_id_m2m_field_present(self):
        """company_id (M2M) is included in the form."""
        form = DepartmentForm()
        self.assertIn("company_id", form.fields)

    def test_save_with_company_m2m(self):
        """DepartmentForm.save() can associate companies via M2M."""
        company = CompanyFactory()
        form = DepartmentForm(
            data={
                "department": "Marketing",
                "company_id": [company.pk],
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        dept = form.save()
        self.assertIn(company, dept.company_id.all())


# ===========================================================================
# 4. TagsForm (~4 tests)
# ===========================================================================
class TagsFormTests(HorillaTestCase):
    """Tests for TagsForm."""

    def test_valid_data_is_valid(self):
        """TagsForm accepts title + color."""
        form = TagsForm(data={"title": "Urgent", "color": "#ff0000"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_tag(self):
        """TagsForm.save() persists a Tag."""
        form = TagsForm(data={"title": "Priority", "color": "#00ff00"})
        self.assertTrue(form.is_valid(), form.errors)
        tag = form.save()
        self.assertIsNotNone(tag.pk)
        self.assertEqual(tag.title, "Priority")

    def test_title_required(self):
        """Title is required."""
        form = TagsForm(data={"title": "", "color": "#000000"})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_color_widget_is_color_input(self):
        """Color field renders as <input type='color'>."""
        form = TagsForm()
        widget = form.fields["color"].widget
        # Django's TextInput(attrs={"type": "color"}) sets input_type on the
        # widget instance; the "type" key is consumed from attrs.
        self.assertEqual(widget.input_type, "color")


# ===========================================================================
# 5. HolidayForm (~5 tests)
# ===========================================================================
class HolidayFormTests(HorillaTestCase):
    """Tests for HolidayForm."""

    def _valid_data(self, **overrides):
        today = date.today()
        data = {
            "name": "New Year",
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "recurring": False,
            "company_id": self.company_a.pk,
        }
        data.update(overrides)
        return data

    def test_valid_data_is_valid(self):
        """HolidayForm accepts valid holiday data."""
        form = HolidayForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_holiday(self):
        """HolidayForm.save() persists a Holiday."""
        form = HolidayForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        holiday = form.save()
        self.assertIsNotNone(holiday.pk)
        self.assertEqual(holiday.name, "New Year")

    def test_name_required(self):
        """Holiday name is required."""
        form = HolidayForm(data=self._valid_data(name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_start_date_required(self):
        """Start date is required."""
        data = self._valid_data()
        data.pop("start_date")
        form = HolidayForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)

    def test_end_date_before_start_date_rejected(self):
        """End date earlier than start date triggers a validation error."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        form = HolidayForm(
            data=self._valid_data(
                start_date=today.isoformat(),
                end_date=yesterday.isoformat(),
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)

    def test_date_fields_have_date_widget_type(self):
        """start_date and end_date widgets render as type='date'."""
        form = HolidayForm()
        for field_name in ("start_date", "end_date"):
            widget = form.fields[field_name].widget
            self.assertEqual(
                widget.input_type,
                "date",
                f"{field_name} should render as type='date'",
            )
