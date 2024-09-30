"""
forms.py
"""

from collections.abc import Mapping
from typing import Any

from django import forms
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from horilla_audit.models import AuditTag, HorillaAuditInfo


class HistoryForm(forms.Form):
    """
    HistoryForm
    """

    history_title = forms.CharField(required=False, label=_("Updation title"))
    history_description = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": "Enter text", "class": "oh-input w-100", "rows": "2"}
        ),
        required=False,
        label=_("Updation description"),
    )
    history_highlight = forms.BooleanField(
        required=False, label=_("Updation highlight")
    )
    history_tags = forms.ModelMultipleChoiceField(
        queryset=AuditTag.objects.all(), required=False, label=_("Updation tag")
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.initial = {}
        self.fields["history_title"].widget.attrs.update({"class": "oh-input w-100"})
        self.fields["history_highlight"].widget.attrs.update({"style": "display:block"})
        self.fields["history_tags"].widget.attrs.update(
            {
                "class": "oh-select oh--dynamic-select-2",
                "style": "width:100%",
                "data-ajax-name": "auditDynamicTag",
            }
        )

    def as_history_modal(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_audit/horilla_audit_log.html", context)
        return table_html


class HistoryTrackingFieldsForm(forms.Form):
    excluded_fields = [
        "id",
        "employee_id",
        "objects",
        "mobile",
        "contract_end_date",
        "additional_info",
        "is_from_onboarding",
        "is_directly_converted",
        "experience",
    ]

    def __init__(self, *args, **kwargs):
        from employee.models import EmployeeWorkInformation as model

        super(HistoryTrackingFieldsForm, self).__init__(*args, **kwargs)
        field_choices = [
            (field.name, field.verbose_name)
            for field in model._meta.get_fields()
            if hasattr(field, "verbose_name") and field.name not in self.excluded_fields
        ]
        self.fields["tracking_fields"] = forms.MultipleChoiceField(
            choices=field_choices,
            required=False,
            widget=forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                    "style": "height:270px;",
                }
            ),
        )
