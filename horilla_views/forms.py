"""
horilla_views/forms.py
"""

from django import forms
from django.utils.safestring import SafeText
from django.template.loader import render_to_string
from base.thread_local_middleware import _thread_locals


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
