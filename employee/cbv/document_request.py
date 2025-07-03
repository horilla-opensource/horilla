"""
This page handles the cbv methods for document request page
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import choosesubordinates, is_reportingmanager
from employee.filters import DocumentRequestFilter
from employee.models import Employee
from horilla.decorators import manager_can_enter
from horilla_documents.forms import (
    DocumentForm,
    DocumentRejectCbvForm,
    DocumentRequestForm,
    DocumentUpdateForm,
)
from horilla_documents.models import Document, DocumentRequest
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaNavView
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("horilla_documents.add_documentrequests"), name="dispatch"
)
class DocumentRequestCreateForm(HorillaFormView):
    """
    form view for create and update document request
    """

    form_class = DocumentRequestForm
    model = DocumentRequest
    new_display_title = _("Create Document Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form = choosesubordinates(
            self.request, self.form, "horilla_documents.add_documentrequest"
        )
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Document Request")

        return context

    def form_valid(self, form: DocumentRequestForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                pk = self.form.instance.pk
                documents = Document.objects.filter(document_request_id=pk)
                doc_obj = form.save()
                doc_obj.employee_id.set(
                    Employee.objects.filter(id__in=form.data.getlist("employee_id"))
                )
                documents.exclude(employee_id__in=doc_obj.employee_id.all()).delete()
                messages.success(
                    self.request, _("Document Request Updated Successfully")
                )
            else:
                messages.success(
                    self.request, _("Document request created successfully")
                )
                emp = form.cleaned_data["employee_id"].all()
                users = [user.employee_user_id for user in emp]
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
@method_decorator(manager_can_enter("horilla_documents.add_document"), name="dispatch")
class DocumentRejectCbvForm(HorillaFormView):
    """
    form view for rejecting document on document request and employee individual view
    """

    model = Document
    form_class = DocumentRejectCbvForm
    hx_confirm = _("Do you want to reject this request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Reject")
        return context

    def form_valid(self, form: DocumentRejectCbvForm) -> HttpResponse:
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
            form.save()
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


class DocumentRequestNav(HorillaNavView):
    """
    For nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("document-request-filter-view")
        self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse_lazy('document-request-create')}"
                            """

        if self.request.user.has_perm(
            "employee.change_employee"
        ) or is_reportingmanager(self.request):
            if self.request.user.has_perm(
                "horilla_documents.change_documentrequest"
            ) or is_reportingmanager(self.request):
                self.actions = [
                    {
                        "action": _("Bulk Approve Requests"),
                        "attrs": f"""
                        id="bulkApproveDocument"
                        hx-post="{reverse('document-bulk-approve')}"
                        hx-confirm='Do you really want to approve all the selected requests?'
                        style="cursor: pointer;"
                        hx-on:click="validateDocsIds(event, 'approved');"
                        data-action="approved"
                        """,
                    },
                    {
                        "action": _("Bulk Reject Requests"),
                        "attrs": f"""
                        hx-get={reverse('document-bulk-reject')}
                        data-target="#objectCreateModal"
                        data-toggle="oh-modal-toggle"
                        hx-on:click="validateDocsIds(event, 'rejected');"
                        data-action="rejected"
                        hx-target="#objectCreateModalTarget"
                        id="bulkRejectDocument"
                        style="cursor: pointer;"
                        """,
                    },
                ]
        else:
            self.actions = None

    nav_title = _("Document Requests")
    filter_body_template = "cbv/documents/document_filter.html"
    filter_instance = DocumentRequestFilter()
    filter_form_context_name = "form"
    search_swap_target = "#view-container"
