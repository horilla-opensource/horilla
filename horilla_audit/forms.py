"""
forms.py
"""

from collections.abc import Mapping
from typing import Any

from django import forms
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from horilla_audit.models import AuditModelConfig, AuditTag, HorillaAuditInfo


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
                    "class": "oh-select oh-select-2",
                    "style": "width:100%;",
                    "data-placeholder": "Select fields…",
                }
            ),
        )


def _eligible_models():
    """Return concrete HorillaModel subclasses that can be audit-tracked."""
    from django.apps import apps as django_apps

    from horilla.models import HorillaModel

    eligible = []
    for model in django_apps.get_models():
        if not issubclass(model, HorillaModel) or model._meta.abstract:
            continue
        eligible.append(model)
    eligible.sort(key=lambda m: (m._meta.app_label, m._meta.model_name))
    return eligible


def model_choices():
    from horilla_audit.registry import DEFAULT_TRACKED_MODELS

    defaults = {(a.lower(), m.lower()) for a, m in DEFAULT_TRACKED_MODELS}
    choices = []
    for m in _eligible_models():
        app_label = m._meta.app_label
        model_name = m._meta.model_name
        label = f"{app_label} — {m._meta.verbose_name.title()}"
        if (app_label.lower(), model_name.lower()) in defaults:
            label = f"{label} ({_('default')})"
        choices.append((f"{app_label}.{model_name}", label))
    return choices


def field_choices_for(app_label, model_name):
    from django.apps import apps as django_apps

    try:
        model = django_apps.get_model(app_label, model_name)
    except LookupError:
        return []
    skip = {"horilla_history", "objects"}
    return [
        (f.name, getattr(f, "verbose_name", f.name) or f.name)
        for f in model._meta.get_fields()
        if getattr(f, "concrete", False)
        and not f.many_to_many
        and not f.auto_created
        and f.name not in skip
    ]


class AuditModelConfigForm(forms.ModelForm):
    """Form for picking which models are tracked by auditlog."""

    model_paths = forms.MultipleChoiceField(
        required=False,
        label=_("Tracked Models"),
        widget=forms.SelectMultiple(
            attrs={
                "class": "oh-select oh-select-2 select2-hidden-accessible",
                "style": "width:100%; height:200px;",
            }
        ),
        help_text=_(
            "Select the models whose changes should be recorded in the audit log. "
            "If no models are selected, the built-in defaults (Employee, "
            "EmployeeWorkInformation, EmployeeBankDetails) are used."
        ),
    )

    class Meta:
        model = AuditModelConfig
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model_paths"].choices = model_choices()
        existing = AuditModelConfig.objects.filter(is_enabled=True).values_list(
            "app_label", "model_name"
        )
        self.fields["model_paths"].initial = [f"{a}.{m}" for a, m in existing]


class AuditModelFieldsForm(forms.Form):
    """Form for selecting which fields of a model are tracked."""

    fields_to_track = forms.MultipleChoiceField(
        required=False,
        label=_("Tracked Fields"),
        widget=forms.SelectMultiple(
            attrs={
                "class": "oh-select oh-select-2 select2-hidden-accessible",
                "style": "width:100%; height:240px;",
            }
        ),
        help_text=_("Leave empty to track every field on the model."),
    )

    def __init__(self, *args, app_label=None, model_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fields_to_track"].choices = field_choices_for(
            app_label, model_name
        )
