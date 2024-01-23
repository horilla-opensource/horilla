from django import forms
from horilla_documents.models import Document, DocumentRequest
from base.forms import ModelForm


class DocumentRequestForm(ModelForm):
    """ form to create a new Document Request """

    # employee_id = forms.ModelMultipleChoiceField(
    #     queryset=DocumentRequest._meta.get_field('employee').remote_field.model.objects.all(),
    #     required=False,
    # )

    class Meta:
        model = DocumentRequest
        fields = '__all__'

    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     # Handle the new field name in cleaned_data
    #     instance.employee.set(self.cleaned_data['employee_id'])
    #     if commit:
    #         instance.save()
    #     return instance


class DocumentForm(ModelForm):
    """ form to create a new Document"""
         
    class Meta:
        model = Document
        fields = "__all__"
        exclude = ["document_request_id","status","reject_reason","is_active"]
        widgets = {
            "employee_id": forms.HiddenInput(),
        }

class DocumentUpdateForm(ModelForm):
    """ form to Update a Document"""

    class Meta:
        model = Document
        fields = "__all__"

class DocumentRejectForm(ModelForm):
    """ form to add rejection reason while rejecting a Document"""

    class Meta:
        model = Document
        fields = ["reject_reason"]