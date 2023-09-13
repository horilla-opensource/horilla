"""
These forms provide a convenient way to handle data input, validation, and customization
of form fields and widgets for the corresponding models in the payroll management system.
"""
import uuid
import datetime
from django import forms
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from base.forms import ModelForm
from employee.models import Employee
from payroll.models import tax_models as models
from payroll.widgets import component_widgets as widget
from payroll.models.models import Contract
import payroll.models.models


class AllowanceForm(forms.ModelForm):
    """
    Form for Allowance model
    """

    load = forms.CharField(widget=widget.AllowanceConditionalVisibility, required=False)
    style = forms.CharField(required=False)
    verbose_name = _("Allowance")

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Allowance
        fields = "__all__"
        widgets = {
            "one_time_date": forms.DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {}
            if instance.one_time_date is not None:
                initial = {
                    "one_time_date": instance.one_time_date.strftime("%Y-%m-%d"),
                }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["style"].widget = widget.StyleWidget(form=self)

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class DeductionForm(forms.ModelForm):
    """
    Form for Deduction model
    """

    load = forms.CharField(widget=widget.DeductionConditionalVisibility, required=False)
    style = forms.CharField(required=False)
    verbose_name = _("Deduction")

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Deduction
        fields = "__all__"
        widgets = {
            "one_time_date": forms.DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {}
            if instance.one_time_date is not None:
                initial = {
                    "one_time_date": instance.one_time_date.strftime("%Y-%m-%d"),
                }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["style"].widget = widget.StyleWidget(form=self)

    def clean(self):
        if (
            self.data.get("update_compensation") is not None
            and self.data.get("update_compensation") != ""
        ):
            if (
                self.data.getlist("specific_employees") is None
                and len(self.data.getlist("specific_employees")) == 0
            ):
                raise forms.ValidationError(
                    {"specific_employees": "You need to choose the employee."}
                )

            if (
                self.data.get("one_time_date") is None
                and self.data.get("one_time_date") == ""
            ):
                raise forms.ValidationError(
                    {"one_time_date": "This field is required."}
                )
            if self.data.get("amount") is None and self.data.get("amount") == "":
                raise forms.ValidationError({"amount": "This field is required."})
        return super().clean()

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class PayslipForm(ModelForm):
    """
    Form for Payslip
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_contracts = Contract.objects.filter(contract_status="active")
        self.fields["employee_id"].choices = [
            (contract.employee_id.id, contract.employee_id)
            for contract in active_contracts
        ]

    class Meta:
        """
        Meta class for additional options
        """

        model = payroll.models.models.Payslip
        fields = [
            "employee_id",
            "start_date",
            "end_date",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class GeneratePayslipForm(forms.Form):
    """
    Form for Payslip
    """

    employee_id = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.filter(
            contract_set__isnull=False, contract_set__contract_status="active"
        ),
        widget=forms.SelectMultiple,
        label="Employee",
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        today = datetime.date.today()
        if end_date < start_date:
            raise forms.ValidationError(
                {
                    "end_date": "The end date must be greater than or equal to the start date."
                }
            )
        if start_date > today:
            raise forms.ValidationError(
                {"end_date": "The start date cannot be in the future."}
            )

        if end_date > today:
            raise forms.ValidationError(
                {"end_date": "The end date cannot be in the future."}
            )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["employee_id"].widget.attrs.update(
            {"class": "oh-select oh-select-2", "id": uuid.uuid4()}
        )
        self.fields["start_date"].widget.attrs.update({"class": "oh-input w-100"})
        self.fields["end_date"].widget.attrs.update({"class": "oh-input w-100"})

    class Meta:
        """
        Meta class for additional options
        """

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PayrollSettingsForm(ModelForm):
    """
    Form for PayrollSettings model
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = models.PayrollSettings
        fields = "__all__"
