"""
forms.py
"""
from django import forms
from django.utils.translation import gettext_lazy as trans
from django.template.loader import render_to_string
from payroll.models.models import WorkRecord
from payroll.models.models import Contract


class ModelForm(forms.ModelForm):
    """
    ModelForm override for additional style
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({"class": "oh-input oh-calendar-input w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                label = trans(field.label)
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                label = trans(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})


class ContractForm(ModelForm):
    """
    ContactForm
    """
    verbose_name = trans("Contract")
    class Meta:
        """
        Meta class for additional options
        """

        fields = "__all__"
        exclude = [
            "is_active",
        ]
        model = Contract

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contract_name"].widget.attrs["autocomplete"] = "off"
        self.fields["contract_start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["contract_start_date"].widget.attrs["class"] = "oh-input w-100"
        self.fields["contract_start_date"].widget = forms.TextInput(
            attrs={"type": "date", "class": "oh-input w-100"}
        )
        self.fields["contract_end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["contract_end_date"].widget.attrs["class"] = "oh-input w-100"
        self.fields["contract_end_date"].widget = forms.TextInput(
            attrs={"type": "date", "class": "oh-input w-100"}
        )
        self.fields["employee_id"].widget.attrs["data-contract-style"] = ""
        self.fields["department"].widget.attrs["data-contract-style"] = ""
        self.fields["job_position"].widget.attrs["data-contract-style"] = ""
        self.fields["job_role"].widget.attrs["data-contract-style"] = ""
        self.fields["work_type"].widget.attrs["data-contract-style"] = ""
        self.fields["shift"].widget.attrs["data-contract-style"] = ""

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("contract_form.html", context)
        return table_html


class WorkRecordForm(ModelForm):
    """
    WorkRecordForm
    """

    class Meta:
        """
        Meta class for additional options
        """

        fields = "__all__"
        model = WorkRecord
