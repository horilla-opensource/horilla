from django.template.loader import render_to_string

from base.forms import ModelForm
from facedetection.models import FaceDetection


class FaceDetectionSetupForm(ModelForm):
    verbose_name = "Facedetection Configuration"

    class Meta:
        model = FaceDetection
        exclude = ["company_id"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
