"""
Forms for handling payroll-related operations.

This module provides Django ModelForms for creating and managing payroll-related data,
including filing status, tax brackets, and federal tax records.

The forms in this module inherit from the Django `forms.ModelForm` class and customize
the widget attributes to enhance the user interface and provide a better user experience.

"""

from django import forms
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from payroll.methods import federal_tax
from payroll.methods.safe_tax_code import TaxCodeValidationError, validate_tax_code
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


class FilingStatusForm(ModelForm):
    """Form for creating and updating filing status."""

    cols = {
        "filing_status": 12,
        "based_on": 12,
        "description": 12,
    }

    class Meta:
        """Meta options for the form."""

        model = FilingStatus
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs: dict = self.fields["use_py"].widget.attrs
        self.fields["python_code"].required = False
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

    def clean_python_code(self):
        """Reject tax code that violates the sandbox policy at save time."""
        code = self.cleaned_data.get("python_code")
        use_py = self.cleaned_data.get("use_py")
        # Only validate code that will actually be executed (use_py enabled and
        # a non-default value supplied). The default template is trusted.
        if use_py and code and code != federal_tax.CODE:
            try:
                validate_tax_code(code)
            except TaxCodeValidationError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return code


class TaxBracketForm(ModelForm):
    """Form for creating and updating tax bracket."""

    cols = {"min_income": 12, "max_income": 12, "tax_rate": 12}

    class Meta:
        """Meta options for the form."""

        model = TaxBracket
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "filing_status_id": forms.HiddenInput(),
        }
