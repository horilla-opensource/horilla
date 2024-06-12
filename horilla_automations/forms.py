"""
horilla_automations/forms.py
"""

from typing import Any
from django import forms
from django.template.loader import render_to_string
from horilla_automations.methods.methods import generate_choices
from horilla_automations.models import MODEL_CHOICES, MailAutomation
from base.forms import ModelForm


class AutomationForm(ModelForm):
    """
    AutomationForm
    """

    condition_html = forms.CharField(widget=forms.HiddenInput())
    condition_querystring = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.data:
            mail_to = []

            initial = []
            mail_details_choice = []
            if self.instance.pk:
                mail_to = generate_choices(self.instance.model)[0]
                mail_details_choice = generate_choices(self.instance.model)[1]
            self.fields["mail_to"] = forms.MultipleChoiceField(choices=mail_to)
            self.fields["mail_details"] = forms.ChoiceField(
                choices=mail_details_choice,
                help_text="Fill mail template details(reciever/instance, `self` will be the person who trigger the automation)",
            )
            self.fields["mail_to"].initial = initial
            attrs = self.fields["mail_to"].widget.attrs
            attrs["class"] = "oh-select oh-select-2 w-100"
        attrs = self.fields["model"].widget.attrs
        self.fields["model"].choices = [("", "Select model")] + list(set(MODEL_CHOICES))
        attrs["onchange"] = "getToMail($(this))"
        self.fields["mail_template"].empty_label = None
        attrs = attrs.copy()
        del attrs["onchange"]
        self.fields["mail_details"].widget.attrs = attrs
        if self.instance.pk:
            self.fields["condition"].initial = self.instance.condition_html
            self.fields["condition_html"].initial = self.instance.condition_html
            self.fields["condition_querystring"].initial = (
                self.instance.condition_querystring
            )

    class Meta:
        model = MailAutomation
        fields = "__all__"

    def save(self, commit: bool = ...) -> Any:
        self.instance: MailAutomation = self.instance
        condition_querystring = self.cleaned_data["condition_querystring"]
        condition_html = self.cleaned_data["condition_html"]
        mail_to = self.data.getlist("mail_to")
        self.instance.mail_to = str(mail_to)
        self.instance.mail_details = self.data["mail_details"]
        self.instance.condition_querystring = condition_querystring
        self.instance.condition_html = condition_html
        return super().save(commit)
