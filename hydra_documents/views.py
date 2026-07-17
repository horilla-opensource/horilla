from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_documents.audit import access_context_from_request, log_access
from hydra_documents.forms import (
    DocumentDeletionForm,
    DocumentLegalHoldForm,
    PrivateDocumentTypeForm,
    PrivateDocumentUploadForm,
)
from hydra_documents.models import (
    DocumentAccessLog,
    PrivateDocument,
    PrivateDocumentType,
)
from hydra_documents.selectors import (
    current_documents_for_candidate,
    document_types_for_candidate,
    document_types_for_user,
    documents_for_candidate,
)
from hydra_documents.services import (
    delete_private_document,
    save_private_document_type,
    set_document_legal_hold,
    upload_private_document,
)
from hydra_people.recruitment_selectors import linked_candidate_for_user


def _add_form_error(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error("file" if "file" in form.fields else None, error)


@login_required
def candidate_documents(request, candidate_id):
    if not request.user.has_perm("hydra_documents.view_privatedocument"):
        raise PermissionDenied
    candidate = linked_candidate_for_user(user=request.user, candidate_id=candidate_id)
    can_replace = request.user.has_perm(
        "hydra_documents.replace_privatedocument"
    )
    form = PrivateDocumentUploadForm(
        request.POST or None,
        request.FILES or None,
        document_types=document_types_for_candidate(
            user=request.user, candidate=candidate
        ),
        replacement_documents=(
            current_documents_for_candidate(
                user=request.user, candidate_id=candidate.pk
            )
            if can_replace
            else PrivateDocument.objects.none()
        ),
    )
    can_upload = request.user.has_perms(
        (
            "hydra_documents.add_privatedocument",
            "hydra_documents.view_privatedocumenttype",
        )
    )
    if request.method == "POST":
        if not can_upload:
            raise PermissionDenied
        if form.is_valid():
            try:
                upload_private_document(
                    actor=request.user,
                    candidate_id=candidate.pk,
                    document_type_uuid=form.cleaned_data["document_type"].uuid,
                    title=form.cleaned_data["title"],
                    issued_on=form.cleaned_data["issued_on"],
                    expires_on=form.cleaned_data["expires_on"],
                    replaces_uuid=(
                        form.cleaned_data["replaces"].uuid
                        if form.cleaned_data["replaces"]
                        else None
                    ),
                    replacement_reason=form.cleaned_data["replacement_reason"],
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
            "can_replace": can_replace,
            "can_manage_types": request.user.has_perms(
                (
                    "hydra_documents.view_privatedocumenttype",
                    "hydra_documents.add_privatedocumenttype",
                )
            ),
            "can_manage_hold": request.user.has_perm(
                "hydra_documents.manage_privatedocumenthold"
            ),
            "can_delete": request.user.has_perm(
                "hydra_documents.delete_privatedocument"
            ),
        },
    )


@login_required
def private_document_type_list(request):
    if not request.user.has_perm("hydra_documents.view_privatedocumenttype"):
        raise PermissionDenied
    return render(
        request,
        "hydra_documents/document_type_list.html",
        {
            "document_types": document_types_for_user(
                user=request.user, include_inactive=True
            ),
            "can_add": request.user.has_perm(
                "hydra_documents.add_privatedocumenttype"
            ),
            "can_change": request.user.has_perm(
                "hydra_documents.change_privatedocumenttype"
            ),
        },
    )


@login_required
def private_document_type_form(request, type_uuid=None):
    required = (
        "hydra_documents.view_privatedocumenttype",
        (
            "hydra_documents.change_privatedocumenttype"
            if type_uuid
            else "hydra_documents.add_privatedocumenttype"
        ),
    )
    if not request.user.has_perms(required):
        raise PermissionDenied
    document_type = None
    if type_uuid:
        document_type = document_types_for_user(
            user=request.user, include_inactive=True
        ).filter(uuid=type_uuid).first()
        if document_type is None:
            raise Http404
        if document_type.company_id is None and not request.user.is_superuser:
            raise Http404
    form = PrivateDocumentTypeForm(
        request.POST or None,
        instance=document_type,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_private_document_type(
                actor=request.user,
                document_type=document_type or PrivateDocumentType(),
                cleaned_data=form.cleaned_data,
            )
        except ValidationError as error:
            _add_form_error(form, error)
        else:
            messages.success(request, _("Document type saved."))
            return redirect("hydra-private-document-type-list")
    return render(
        request,
        "hydra_documents/document_type_form.html",
        {"form": form, "document_type": document_type},
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
    if document.deleted_at:
        log_access(
            actor=request.user,
            context=audit_context,
            document=document,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.DENIED,
            reason="document_deleted",
        )
        raise Http404
    if not document.scanned_at:
        log_access(
            actor=request.user,
            context=audit_context,
            document=document,
            document_uuid=document_uuid,
            action=DocumentAccessLog.Action.DOWNLOAD,
            outcome=DocumentAccessLog.Outcome.DENIED,
            reason="not_scanned",
        )
        raise Http404
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


@login_required
@require_POST
def private_document_legal_hold(request, document_uuid):
    if not request.user.has_perms(
        (
            "hydra_documents.view_privatedocument",
            "hydra_documents.manage_privatedocumenthold",
        )
    ):
        raise PermissionDenied
    form = DocumentLegalHoldForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("A valid legal-hold action and reason are required."))
    else:
        try:
            document = set_document_legal_hold(
                actor=request.user,
                document_uuid=document_uuid,
                enabled=form.cleaned_data["action"] == "apply",
                reason=form.cleaned_data["reason"],
                audit_context=access_context_from_request(request),
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, _("Document legal hold updated."))
            return redirect(
                "hydra-candidate-documents", candidate_id=document.candidate_id
            )
    document = PrivateDocument.objects.filter(uuid=document_uuid).first()
    if document is None:
        raise Http404
    linked_candidate_for_user(user=request.user, candidate_id=document.candidate_id)
    return redirect("hydra-candidate-documents", candidate_id=document.candidate_id)


@login_required
@require_POST
def private_document_delete(request, document_uuid):
    if not request.user.has_perms(
        (
            "hydra_documents.view_privatedocument",
            "hydra_documents.delete_privatedocument",
        )
    ):
        raise PermissionDenied
    form = DocumentDeletionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("A deletion reason is required."))
    else:
        try:
            document = delete_private_document(
                actor=request.user,
                document_uuid=document_uuid,
                reason=form.cleaned_data["reason"],
                audit_context=access_context_from_request(request),
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, _("Document securely deleted."))
            return redirect(
                "hydra-candidate-documents", candidate_id=document.candidate_id
            )
    document = PrivateDocument.objects.filter(uuid=document_uuid).first()
    if document is None:
        raise Http404
    linked_candidate_for_user(user=request.user, candidate_id=document.candidate_id)
    return redirect("hydra-candidate-documents", candidate_id=document.candidate_id)
