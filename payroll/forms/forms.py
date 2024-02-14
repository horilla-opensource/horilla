"""
forms.py
"""

from datetime import date
from django import forms
from django.forms import widgets
from django.utils.translation import gettext_lazy as trans
from django.template.loader import render_to_string
from base import thread_local_middleware
from payroll.models.models import (
    EncashmentGeneralSettings,
    PayrollGeneralSetting,
    ReimbursementrequestComment,
    WorkRecord,
)
from payroll.models.models import Contract
from base.methods import reload_queryset


class ModelForm(forms.ModelForm):
    """
    ModelForm override for additional style
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        for _, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

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

            try:            
                self.fields["employee_id"].initial = request.user.employee_get 
            except:
                pass

            try:            
                self.fields["company_id"].initial = request.user.employee_get.get_company
            except:
                pass

class ContractForm(ModelForm):
    """
    ContactForm
    """

    verbose_name = trans("Contract")
    contract_start_date = forms.DateField()
    contract_end_date = forms.DateField(required=False)

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
        self.fields["employee_id"].widget.attrs.update(
            {"onchange": "contractInitial(this)"}
        )
        self.fields["contract_start_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_end_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_status"].widget.attrs.update(
            {
                "class": "oh-select",
            }
        )
        if self.instance and self.instance.pk:
            dynamic_url = self.get_dynamic_hx_post_url(self.instance)
            self.fields["contract_status"].widget.attrs.update(
                {
                    "hx-target": "#contractFormTarget",
                    "hx-post": dynamic_url,
                    "hx-swap": "outerHTML",
                }
            )
        first = PayrollGeneralSetting.objects.first()
        if first and self.instance.pk is None:
            self.initial["notice_period_in_month"] = first.notice_period

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("contract_form.html", context)
        return table_html

    def get_dynamic_hx_post_url(self, instance):
        return f"/payroll/update-contract-status/{instance.pk}"


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


class ReimbursementrequestCommentForm(ModelForm):
    """
    ReimbursementrequestCommentForm form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ReimbursementrequestComment
        fields = ("comment",)


class EncashmentGeneralSettingsForm(ModelForm):
    class Meta:
        model = EncashmentGeneralSettings
        fields = "__all__"
