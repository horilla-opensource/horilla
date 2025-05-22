from django.template.loader import render_to_string

from base.forms import ModelForm

from .models import GeoFencing


class GeoFencingSetupForm(ModelForm):
    verbose_name = "Geofence Configuration"

    class Meta:
        model = GeoFencing
        exclude = ["company_id"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
