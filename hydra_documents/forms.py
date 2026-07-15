from django import forms
from django.utils.translation import gettext_lazy as _

from hydra_documents.models import PrivateDocument


class PrivateDocumentUploadForm(forms.Form):
    title = forms.CharField(max_length=160, label=_("Document title"))
    category = forms.ChoiceField(
        choices=PrivateDocument.Category.choices, label=_("Category")
    )
    file = forms.FileField(
        label=_("File"),
        help_text=_("PDF, JPEG or PNG; maximum 10 MB."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )
