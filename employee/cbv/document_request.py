"""
This page handles the cbv methods for document request page
"""

from typing import Any
from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from employee.models import Employee
from notifications.signals import notify
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from base.methods import choosesubordinates
from horilla.decorators import manager_can_enter
from horilla_documents.forms import DocumentRejectForm, DocumentRequestForm, DocumentUpdateForm,DocumentForm
from horilla_documents.models import Document, DocumentRequest
from horilla_views.generic.cbv.views import HorillaFormView
from horilla_views.cbv_methods import login_required



@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("horilla_documents.add_documentrequests"),name="dispatch")
class DocumentRequestCreateForm(HorillaFormView):
    """
    form view for create and update document request
    """

    form_class = DocumentRequestForm
    model = DocumentRequest
    new_display_title = _("Create Document Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form = choosesubordinates(self.request, self.form, "horilla_documents.add_documentrequest")
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Document Request")

        return context

    def form_valid(self, form: DocumentRequestForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                pk = self.form.instance.pk
                documents = Document.objects.filter(document_request_id=pk)
                doc_obj = form.save()
                doc_obj.employee_id.set(Employee.objects.filter(id__in=form.data.getlist("employee_id")))
                documents.exclude(employee_id__in=doc_obj.employee_id.all()).delete()
                messages.success(self.request, _("Document Request Updated Successfully"))
            else:
                messages.success(self.request, _("Document request created successfully"))
                emp = form.cleaned_data['employee_id'].all()
                users = [ user.employee_user_id for user in emp ]
                notify.send(
                    self.request.user.employee_get,
                    recipient=users,
                    verb=f"{self.request.user.employee_get} requested a document.",
                    verb_ar=f"طلب {self.request.user.employee_get} مستنداً.",
                    verb_de=f"{self.request.user.employee_get} hat ein Dokument angefordert.",
                    verb_es=f"{self.request.user.employee_get} solicitó un documento.",
                    verb_fr=f"{self.request.user.employee_get} a demandé un document.",
                    redirect=reverse("employee-profile"),
                    icon="chatbox-ellipses",
                )
                form.save()
            return self.HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)
    

class DocumentCreateForm(HorillaFormView):
    """
    form view for upload document
    """

    form_class = DocumentForm
    model = Document
    new_display_title = _("Document")

    def get_initial(self) -> dict:
        initial = super().get_initial()
        employee_id = self.kwargs.get("emp_id")
        initial["employee_id"] = employee_id
        initial["expiry_date"] = None
        return initial

    def form_valid(self, form: DocumentForm) -> HttpResponse:
        if form.is_valid():
            messages.success(self.request, _("Document Uploaded Successfully"))
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("horilla_documents.add_document"),name="dispatch")
class DocumentRejectform(HorillaFormView):
    """
    form view for rejecting document on document request and employee individual view
    """

    model = Document
    form_class = DocumentRejectForm
    hx_confirm = _("Do you want to reject this request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Reject")
        return context
    
    def form_valid(self, form: DocumentRejectForm) -> HttpResponse:
        if form.is_valid():
            pk = self.form.instance.pk
            document_obj = get_object_or_404(Document, id=pk)
            if document_obj.document:
                if form.is_valid():
                    document_obj.status = "rejected"
                    document_obj.save()
                    messages.error(self.request, _("Document request rejected"))
            else:
                messages.error(self.request, _("No document uploaded"))
            # form.save()
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)
    


class DocumentUploadForm(HorillaFormView):
    """
    form view for upload documents on document request and employee individual view
    """

    model = Document
    form_class = DocumentUpdateForm
    template_name = "cbv/documents/inherit_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form.fields["title"].widget = forms.HiddenInput()
        self.form.fields["employee_id"].widget = forms.HiddenInput()
        self.form.fields["document_request_id"].widget = forms.HiddenInput()
        self.form.fields["status"].widget = forms.HiddenInput()
        self.form.fields["reject_reason"].widget = forms.HiddenInput()
        self.form.fields["is_digital_asset"].widget = forms.HiddenInput()

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Upload File")
        return context
    

    def form_valid(self, form: DocumentUpdateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Document uploaded successfully"))
                try:
                    notify.send(
                        self.request.user.employee_get,
                        recipient=self.request.user.employee_get.get_reporting_manager().employee_user_id,
                        verb=f"{self.request.user.employee_get} uploaded a document",
                        verb_ar=f"قام {self.request.user.employee_get} بتحميل مستند",
                        verb_de=f"{self.request.user.employee_get} hat ein Dokument hochgeladen",
                        verb_es=f"{self.request.user.employee_get} subió un documento",
                        verb_fr=f"{self.request.user.employee_get} a téléchargé un document",
                        redirect=reverse(
                            "employee-view-individual",
                            kwargs={"obj_id": self.request.user.employee_get.id},
                        ),
                        icon="chatbox-ellipses",
                    )
                except:
                    pass
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)

