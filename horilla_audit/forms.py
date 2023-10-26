"""
forms.py
"""
from collections.abc import Mapping
from typing import Any
from django import forms
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from horilla_audit.models import HorillaAuditInfo, AuditTag


class HistoryForm(forms.Form):
    """
    HistoryForm
    """

    history_title = forms.CharField(required=False)
    history_description = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": "Enter text", "class": "oh-input w-100", "rows": "2"}
        ),
        required=False,
    )
    history_highlight = forms.BooleanField(required=False)
    history_tags = forms.ModelMultipleChoiceField(
        queryset=AuditTag.objects.all(), required=False
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
