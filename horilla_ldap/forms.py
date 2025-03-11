from django import forms
from django.template.loader import render_to_string

from base.forms import ModelForm

from .models import LDAPSettings


class LDAPSettingsForm(ModelForm):
    bind_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "oh-input w-100"}), required=True
    )

    class Meta:
        model = LDAPSettings
        fields = ["ldap_server", "bind_dn", "bind_password", "base_dn"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
