from django import forms
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_templates.models import MessageTemplate


class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = (
            "company",
            "code",
            "name",
            "language",
            "subject",
            "body",
            "is_active",
        )
        widgets = {
            "body": forms.Textarea(attrs={"rows": 10}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["company"].queryset = Company._base_manager.filter(
            pk__in=company_ids_for_user(user=actor)
        ).order_by("company")
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "oh-switch__checkbox"
            elif isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class TemplateDataExportForm(forms.Form):
    company = forms.ModelChoiceField(
        label=_("Limit to company"),
        queryset=Company._base_manager.none(),
        required=False,
        empty_label=_("All companies in my active scope"),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company._base_manager.filter(
            pk__in=company_ids_for_user(user=actor)
        ).order_by("company")
        self.fields["company"].widget.attrs["class"] = "oh-select oh-select-2 w-100"
