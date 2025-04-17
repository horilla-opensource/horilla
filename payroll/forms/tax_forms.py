"""
Forms for handling payroll-related operations.

This module provides Django ModelForms for creating and managing payroll-related data,
including filing status, tax brackets, and federal tax records.

The forms in this module inherit from the Django `forms.ModelForm` class and customize
the widget attributes to enhance the user interface and provide a better user experience.

"""

import uuid
from datetime import date

from django import forms
from django.utils.translation import gettext_lazy as _

from base.methods import reload_queryset
from horilla import horilla_middlewares
from payroll.methods import federal_tax
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


class ModelForm(forms.ModelForm):
    """Custom ModelForm with enhanced widget attributes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            input_widget = field.widget

            if isinstance(input_widget, (forms.DateInput)):
                field.initial = date.today()

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

            try:
                self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class FilingStatusForm(ModelForm):
    """Form for creating and updating filing status."""

    class Meta:
        """Meta options for the form."""

        model = FilingStatus
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs: dict = self.fields["use_py"].widget.attrs
        attrs[
            "onchange"
        ] = """
        if($(this).is(':checked')){
            $('#oc-editor').show();
            //$("#objectCreateModal #objectCreateModalTarget").css("max-width","90%")
        }else{
            //$("#objectCreateModal #objectCreateModalTarget").css("max-width","650px")
            $('#oc-editor').hide();
        }
        """

        if self.instance.pk is None:
            self.instance.python_code = federal_tax.CODE
        else:
            del self.fields["use_py"]
            del self.fields["python_code"]


class TaxBracketForm(ModelForm):
    """Form for creating and updating tax bracket."""

    class Meta:
        """Meta options for the form."""

        model = TaxBracket
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "filing_status_id": forms.HiddenInput(),
        }
