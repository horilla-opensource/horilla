"""Form for creating/editing report subscriptions — a real Django ModelForm
built on Horilla's standard base.forms.ModelForm, so it renders through the
same generic create/edit component (generic/form.html) as the rest of the
app instead of a hand-built modal."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from report.models import ReportSubscription

_SELECT_CLASS = "oh-select oh-select-2 select2-hidden-accessible"


class ReportSubscriptionForm(ModelForm):
    format = forms.ChoiceField(
        label=_("Attachment"),
        choices=[("xlsx", _("Excel")), ("pdf", _("PDF"))],
        initial="xlsx",
    )

    class Meta:
        model = ReportSubscription
        fields = ["report_slug", "name", "frequency", "recipients"]
        labels = {
            "report_slug": _("Report"),
            "name": _("Name"),
            "frequency": _("Frequency"),
            "recipients": _("Recipients"),
        }

    def __init__(self, *args, report_choices=None, lock_report=None, **kwargs):
        super().__init__(*args, **kwargs)

        editing = bool(self.instance and self.instance.pk)
        if editing:
            # The report a subscription is for never changes after creation
            # — show it (so the user has context) but lock the value: a
            # disabled field ignores whatever a client submits and always
            # uses this single fixed choice instead.
            self.fields["report_slug"] = forms.ChoiceField(
                label=_("Report"),
                choices=[(self.instance.report_slug, self.instance.report_name)],
                disabled=True,
                widget=forms.Select(attrs={"class": _SELECT_CLASS}),
            )
            self.initial.setdefault(
                "format", (self.instance.filters or {}).get("format") or "xlsx"
            )
        elif lock_report:
            from report.registry import get_report

            definition = get_report(lock_report)
            display = str(definition.name) if definition else lock_report
            self.fields["report_slug"] = forms.ChoiceField(
                label=_("Report"),
                choices=[(lock_report, display)],
                disabled=True,
                widget=forms.Select(attrs={"class": _SELECT_CLASS}),
            )
        elif report_choices is not None:
            self.fields["report_slug"] = forms.ChoiceField(
                label=_("Report"),
                choices=[("", _("Select a report…"))] + report_choices,
                widget=forms.Select(attrs={"class": _SELECT_CLASS}),
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        filters = dict(instance.filters or {})
        filters["format"] = self.cleaned_data.get("format") or "xlsx"
        instance.filters = filters
        if commit:
            instance.save()
        return instance
