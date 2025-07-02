# forms.py
from typing import Any

from django.forms import ValidationError
from django.template.loader import render_to_string

from base.forms import ModelForm
from whatsapp.models import WhatsappCredientials


class WhatsappForm(ModelForm):
    cols = {"meta_token": 12}

    class Meta:
        model = WhatsappCredientials
        fields = "__all__"
        exclude = ["is_active", "created_templates"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        companies = cleaned_data.get("company_id")
        is_primary = cleaned_data.get("is_primary")

        if companies:
            for company in companies:
                existing_primary = WhatsappCredientials.objects.filter(
                    company_id=company, is_primary=True
                ).exclude(id=self.instance.id)

                if is_primary:
                    if existing_primary.exists():
                        raise ValidationError(
                            f"Company '{company.company}' already has a primary credential."
                        )
                else:
                    if not existing_primary.exists():
                        cleaned_data["is_primary"] = True

        return cleaned_data
