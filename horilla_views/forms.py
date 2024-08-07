"""
horilla_views/forms.py
"""

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import SafeText

from horilla.horilla_middlewares import _thread_locals
from horilla_views import models


class ToggleColumnForm(forms.Form):
    """
    Toggle column form
    """

    def __init__(self, columns, hidden_fields: list, *args, **kwargs):
        request = getattr(_thread_locals, "request", {})
        self.request = request
        super().__init__(*args, **kwargs)
        for column in columns:
            initial = True
            if column[1] in hidden_fields:
                initial = False

            self.fields[column[1]] = forms.BooleanField(
                label=column[0], initial=initial
            )

    def as_list(self) -> SafeText:
        """
        Render the form fields as HTML table rows with.
        """
        context = {"form": self, "request": self.request}
        table_html = render_to_string("generic/as_list.html", context)
        return table_html


class SavedFilterForm(forms.ModelForm):
    """
    SavedFilterForm
    """

    color = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input w-100",
                "type": "color",
                "placeholder": "Choose a color",
            }
        )
    )

    class Meta:
        model = models.SavedFilter
        fields = ["title", "is_default", "color"]

    def structured(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        request = getattr(_thread_locals, "request", None)
        context = {
            "form": self,
            "request": request,
        }
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs = self.fields["title"].widget.attrs
        attrs["class"] = "oh-input w-100"
        attrs["placeholder"] = "Saved filter title"
        if self.instance.pk:
            self.verbose_name = self.instance.title
