"""
Forms for handling payroll-related operations.

This module provides Django ModelForms for creating and managing payroll-related data,
including filing status, tax brackets, and federal tax records.

The forms in this module inherit from the Django `forms.ModelForm` class and customize
the widget attributes to enhance the user interface and provide a better user experience.

"""
import uuid
from django import forms
from django.utils.translation import gettext_lazy as _
from payroll.models.tax_models import TaxBracket
from base.methods import reload_queryset


from payroll.models.tax_models import (
    FederalTax,
)
from payroll.models.models import FilingStatus


class ModelForm(forms.ModelForm):
    """Custom ModelForm with enhanced widget attributes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            input_widget = field.widget
            if isinstance(
                input_widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                label = _(field.label)
                input_widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(input_widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = _(field.label)
                field.empty_label = str(_("---Choose {label}---")).format(label=label)
                self.fields[field_name].widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 w-100",
                        "id": uuid.uuid4(),
                        "style": "height:50px;border-radius:0;",
                    }
                )
            elif isinstance(input_widget, (forms.Textarea)):
                label = _(field.label.title())
                input_widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                input_widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                input_widget.attrs.update({"class": "oh-switch__checkbox"})


class FilingStatusForm(ModelForm):
    """Form for creating and updating filing status."""

    class Meta:
        """Meta options for the form."""

        model = FilingStatus
        fields = "__all__"


class TaxBracketForm(ModelForm):
    """Form for creating and updating tax bracket."""

    class Meta:
        """Meta options for the form."""

        model = TaxBracket
        fields = "__all__"
        widgets = {
            "filing_status_id": forms.Select(
                attrs={"class": "oh-select  oh-select-2 select2-hidden-accessible"}
            ),
        }


class FederalTaxForm(ModelForm):
    """Form for creating and updating tax bracket."""

    class Meta:
        """Meta options for the form."""

        model = FederalTax
        fields = "__all__"
