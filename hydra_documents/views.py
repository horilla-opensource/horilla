from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from hydra_documents.audit import access_context_from_request, log_access
from hydra_documents.forms import PrivateDocumentUploadForm
from hydra_documents.models import DocumentAccessLog, PrivateDocument
from hydra_documents.selectors import documents_for_candidate
from hydra_documents.services import upload_private_document
from hydra_people.recruitment_selectors import linked_candidate_for_user


def _add_form_error(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error("file", error)


@login_required
def candidate_documents(request, candidate_id):
    if not request.user.has_perm("hydra_documents.view_privatedocument"):
        raise PermissionDenied
    candidate = linked_candidate_for_user(user=request.user, candidate_id=candidate_id)
    form = PrivateDocumentUploadForm(request.POST or None, request.FILES or None)
    can_upload = request.user.has_perm("hydra_documents.add_privatedocument")
    if request.method == "POST":
        if not can_upload:
            raise PermissionDenied
        if form.is_valid():
            try:
                upload_private_document(
                    actor=request.user,
                    candidate_id=candidate.pk,
                    title=form.cleaned_data["title"],
                    category=form.cleaned_data["category"],
                    upload=form.cleaned_data["file"],
                    audit_context=access_context_from_request(request),
                )
            except ValidationError as error:
                _add_form_error(form, error)
            else:
                messages.success(request, _("Private document uploaded."))
                return redirect("hydra-candidate-documents", candidate_id=candidate.pk)
    return render(
        request,
        "hydra_documents/candidate_documents.html",
        {
            "candidate": candidate,
            "person": candidate.hydra_person_link.person,
            "documents": documents_for_candidate(
                user=request.user, candidate_id=candidate.pk
            ),
            "form": form,
            "can_upload": can_upload,
        },
    )


@login_required
def private_document_download(request, document_uuid):
    audit_context = access_context_from_request(request)
    document = PrivateDocument.objects.filter(uuid=document_uuid).select_related(
        "candidate"
    ).first()
    if not request.user.has_perms(
        (
            "hydra_documents.view_privatedocument",
            "hydra_documents.download_privatedocument",
        )
    ):
        log_access(
            actor=request.user,
            context=audit_context,
            document=document,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.DENIED,
            reason="permission_denied",
        )
        return HttpResponseForbidden()
    if document is None:
        log_access(
            actor=request.user,
            context=audit_context,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.NOT_FOUND,
            reason="unknown_document",
        )
        raise Http404
    try:
        linked_candidate_for_user(user=request.user, candidate_id=document.candidate_id)
    except Http404:
        log_access(
            actor=request.user,
            context=audit_context,
            document=document,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.DENIED,
            reason="outside_scope",
        )
        raise
    try:
        file_handle = document.file.open("rb")
    except (FileNotFoundError, OSError):
        log_access(
            actor=request.user,
            context=audit_context,
            document=document,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.ERROR,
            reason="storage_error",
        )
        raise Http404
    log_access(
        actor=request.user,
        context=audit_context,
        document=document,
        document_uuid=document_uuid,
        action=DocumentAccessLog.Action.DOWNLOAD,
        outcome=DocumentAccessLog.Outcome.ALLOWED,
        reason="downloaded",
    )
    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=document.original_filename,
        content_type=document.verified_content_type,
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response
