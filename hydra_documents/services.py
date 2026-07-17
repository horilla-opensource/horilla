import hashlib
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import File
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_documents.audit import AccessContext, log_access
from hydra_documents.models import (
    DocumentAccessLog,
    PrivateDocument,
    PrivateDocumentType,
    QuarantinedUpload,
)
from hydra_documents.scanning import ScannerError, scan_file
from hydra_documents.selectors import document_types_for_user
from hydra_people.models import Person
from hydra_people.recruitment_selectors import linked_candidate_for_user
from recruitment.models import Candidate


SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def _safe_filename(filename):
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "document")[:255]


def inspect_upload(upload, *, document_type=None):
    max_bytes = (
        min(
            settings.HYDRA_PRIVATE_DOCUMENT_MAX_BYTES,
            document_type.max_size_bytes,
        )
        if document_type
        else settings.HYDRA_PRIVATE_DOCUMENT_MAX_BYTES
    )
    if upload.size <= 0 or upload.size > max_bytes:
        raise ValidationError(
            _("The file must be non-empty and no larger than %(size)s MB."),
            params={"size": max_bytes // (1024 * 1024)},
        )
    digest = hashlib.sha256()
    head = b""
    total = 0
    for chunk in upload.chunks():
        if not head:
            head = chunk[:16]
        digest.update(chunk)
        total += len(chunk)
    upload.seek(0)
    content_type = next((mime for magic, mime in SIGNATURES if head.startswith(magic)), None)
    if not content_type:
        raise ValidationError(_("Only verified PDF, JPEG and PNG files are allowed."))
    if document_type and content_type not in document_type.allowed_content_types:
        raise ValidationError(
            _("This file format is not allowed for the selected document type.")
        )
    return content_type, total, digest.hexdigest()


def _require_upload_scope(*, actor, candidate_id):
    required = (
        "hydra_documents.add_privatedocument",
        "hydra_documents.view_privatedocument",
        "hydra_documents.view_privatedocumenttype",
        "hydra_people.view_person",
        "recruitment.view_candidate",
    )
    if not actor.has_perms(required):
        raise PermissionDenied
    candidate = linked_candidate_for_user(user=actor, candidate_id=candidate_id)
    return candidate, candidate.hydra_person_link.person


def _document_type_for_candidate(
    *, actor, candidate, document_type_uuid, for_update=False
):
    queryset = document_types_for_user(user=actor)
    if for_update:
        queryset = queryset.select_for_update(of=("self",))
    document_type = queryset.filter(uuid=document_type_uuid).first()
    if document_type is None:
        raise Http404
    company_id = getattr(candidate.recruitment_id, "company_id_id", None)
    if document_type.company_id and document_type.company_id != company_id:
        raise Http404
    return document_type


def _replacement_for_candidate(
    *, actor, candidate, document_uuid, for_update=False
):
    if not document_uuid:
        return None
    queryset = PrivateDocument.objects.select_related("document_type")
    if for_update:
        queryset = queryset.select_for_update(of=("self",))
    predecessor = queryset.filter(uuid=document_uuid).first()
    if predecessor is None or predecessor.candidate_id != candidate.pk:
        raise Http404
    linked_candidate_for_user(user=actor, candidate_id=predecessor.candidate_id)
    return predecessor


def _validate_version_request(
    *,
    actor,
    candidate,
    person,
    document_type,
    predecessor,
    replacement_reason,
    lock=False,
):
    reason = " ".join(str(replacement_reason or "").split())
    if predecessor:
        if not actor.has_perm("hydra_documents.replace_privatedocument"):
            raise PermissionDenied
        if predecessor.person_id != person.pk:
            raise ValidationError(
                {"replaces": _("A replacement must belong to the same Person.")}
            )
        if predecessor.document_type_id != document_type.pk:
            raise ValidationError(
                {"replaces": _("A replacement must use the selected document type.")}
            )
        if predecessor.deleted_at:
            raise ValidationError(
                {"replaces": _("A deleted document cannot be replaced.")}
            )
        if len(reason) < 10:
            raise ValidationError(
                {
                    "replacement_reason": _(
                        "Provide a replacement reason of at least 10 characters."
                    )
                }
            )
    elif reason:
        raise ValidationError(
            {"replacement_reason": _("Choose a current version to replace.")}
        )

    current_queryset = PrivateDocument.objects.filter(
        candidate=candidate,
        document_type=document_type,
        deleted_at__isnull=True,
        replaced_by__isnull=True,
    )
    if lock:
        current_queryset = current_queryset.select_for_update(of=("self",))
    current = list(current_queryset.order_by("pk"))
    if predecessor and predecessor not in current:
        raise ValidationError(
            {"replaces": _("Only the current document version can be replaced.")}
        )
    if document_type.single_current and current:
        if predecessor is None:
            raise ValidationError(
                {
                    "replaces": _(
                        "This type already has a current version; choose it explicitly."
                    )
                }
            )
        if current != [predecessor]:
            raise ValidationError(
                _("The document type has conflicting current versions and needs review.")
            )
    return reason


@transaction.atomic
def save_private_document_type(*, actor, document_type, cleaned_data):
    creating = document_type.pk is None
    required = (
        "hydra_documents.view_privatedocumenttype",
        (
            "hydra_documents.add_privatedocumenttype"
            if creating
            else "hydra_documents.change_privatedocumenttype"
        ),
    )
    if not actor.has_perms(required):
        raise PermissionDenied
    if not creating:
        document_type = (
            document_types_for_user(user=actor, include_inactive=True)
            .select_for_update(of=("self",))
            .filter(pk=document_type.pk)
            .first()
        )
        if document_type is None:
            raise Http404
    company = cleaned_data.get("company")
    if company is None and not actor.is_superuser:
        raise PermissionDenied
    if company is not None:
        from hydra_coordination.selectors import company_ids_for_user

        if not actor.is_superuser and company.pk not in company_ids_for_user(user=actor):
            raise PermissionDenied
    for field_name in (
        "company",
        "code",
        "name",
        "category",
        "allowed_content_types",
        "retention_days",
        "requires_expiry_date",
        "single_current",
        "is_active",
    ):
        setattr(document_type, field_name, cleaned_data[field_name])
    document_type.max_size_bytes = cleaned_data["max_size_mb"] * 1024 * 1024
    if creating:
        document_type.created_by = actor
    document_type.modified_by = actor
    document_type.full_clean()
    document_type.save()
    return document_type


def _mark_quarantine(
    quarantine, *, status, scanner="", scanner_result="", document=None
):
    quarantine.status = status
    quarantine.scanner = scanner[:80]
    quarantine.scanner_result = scanner_result[:160]
    quarantine.scan_completed_at = timezone.now()
    quarantine.document = document
    quarantine.save(
        update_fields=(
            "status",
            "scanner",
            "scanner_result",
            "scan_completed_at",
            "document",
        )
    )


def _create_quarantine(
    *,
    actor,
    candidate,
    person,
    document_type,
    predecessor,
    upload,
    content_type,
    size,
    digest,
):
    quarantine = QuarantinedUpload(
        actor=actor,
        candidate=candidate,
        person=person,
        document_type=document_type,
        replaces=predecessor,
        original_filename=_safe_filename(upload.name),
        verified_content_type=content_type,
        size=size,
        sha256=digest,
        purge_after=timezone.now()
        + timedelta(hours=settings.HYDRA_DOCUMENT_QUARANTINE_HOURS),
    )
    quarantine.full_clean(exclude=("file", "document"))
    saved_name = None
    try:
        quarantine.file.save(upload.name, File(upload), save=False)
        saved_name = quarantine.file.name
        quarantine.save()
    except Exception:
        if saved_name:
            quarantine.file.storage.delete(saved_name)
        raise
    return quarantine


def _promote_clean_upload(
    *,
    quarantine,
    actor,
    title,
    issued_on,
    expires_on,
    replacement_reason,
    scan_result,
    audit_context,
):
    private_name = None
    try:
        with transaction.atomic():
            locked_quarantine = QuarantinedUpload.objects.select_for_update().get(
                pk=quarantine.pk,
                status=QuarantinedUpload.Status.PENDING,
            )
            scoped_candidate = linked_candidate_for_user(
                user=actor, candidate_id=locked_quarantine.candidate_id
            )
            candidate = Candidate._base_manager.select_for_update().get(
                pk=scoped_candidate.pk
            )
            person = Person.objects.select_for_update().get(
                pk=candidate.hydra_person_link.person_id
            )
            if locked_quarantine.document_type_id is None:
                raise ValidationError(_("The upload has no logical document type."))
            document_type = _document_type_for_candidate(
                actor=actor,
                candidate=candidate,
                document_type_uuid=locked_quarantine.document_type.uuid,
                for_update=True,
            )
            predecessor = _replacement_for_candidate(
                actor=actor,
                candidate=candidate,
                document_uuid=(
                    locked_quarantine.replaces.uuid
                    if locked_quarantine.replaces_id
                    else None
                ),
                for_update=True,
            )
            reason = _validate_version_request(
                actor=actor,
                candidate=candidate,
                person=person,
                document_type=document_type,
                predecessor=predecessor,
                replacement_reason=replacement_reason,
                lock=True,
            )
            if locked_quarantine.verified_content_type not in document_type.allowed_content_types:
                raise ValidationError(
                    _("The document-type rules changed; review and upload again.")
                )
            if locked_quarantine.size > document_type.max_size_bytes:
                raise ValidationError(
                    _("The document-type size limit changed; review and upload again.")
                )
            if document_type.requires_expiry_date and not expires_on:
                raise ValidationError(
                    {"expires_on": _("Expiry date is required for this document type.")}
                )
            if issued_on and expires_on and issued_on > expires_on:
                raise ValidationError(
                    {"expires_on": _("Expiry date cannot be earlier than issue date.")}
                )
            document = PrivateDocument(
                person=person,
                candidate=candidate,
                document_type=document_type,
                title=" ".join(title.split()) or document_type.name,
                category=document_type.category,
                original_filename=locked_quarantine.original_filename,
                verified_content_type=locked_quarantine.verified_content_type,
                size=locked_quarantine.size,
                sha256=locked_quarantine.sha256,
                lineage_uuid=(predecessor.lineage_uuid if predecessor else uuid4()),
                version_number=(predecessor.version_number + 1 if predecessor else 1),
                replaces=predecessor,
                replacement_reason=reason,
                type_rules_snapshot=document_type.rules_snapshot(),
                issued_on=issued_on,
                expires_on=expires_on,
                scanner=scan_result.scanner,
                scanned_at=timezone.now(),
                retention_until=timezone.localdate()
                + timedelta(days=document_type.retention_days),
                created_by=actor,
                modified_by=actor,
            )
            document.full_clean(exclude=("file",))
            with locked_quarantine.file.open("rb") as source:
                document.file.save(
                    locked_quarantine.original_filename, File(source), save=False
                )
                private_name = document.file.name
                document.save()
            _mark_quarantine(
                locked_quarantine,
                status=QuarantinedUpload.Status.PROMOTED,
                scanner=scan_result.scanner,
                scanner_result=scan_result.result,
                document=document,
            )
            log_access(
                actor=actor,
                context=audit_context,
                document=document,
                document_uuid=document.uuid,
                action=DocumentAccessLog.Action.UPLOAD,
                outcome=DocumentAccessLog.Outcome.ALLOWED,
                reason=("replacement_scanned_clean" if predecessor else "scanned_clean"),
            )
    except Exception:
        if private_name:
            PrivateDocument._meta.get_field("file").storage.delete(private_name)
        raise

    quarantine_name = quarantine.file.name
    try:
        quarantine.file.storage.delete(quarantine_name)
    except OSError:
        return document
    QuarantinedUpload.objects.filter(pk=quarantine.pk).update(
        file="", purged_at=timezone.now()
    )
    return document


def upload_private_document(
    *,
    actor,
    candidate_id,
    document_type_uuid,
    title,
    issued_on,
    expires_on,
    replaces_uuid,
    replacement_reason,
    upload,
    audit_context: AccessContext,
):
    candidate, person = _require_upload_scope(actor=actor, candidate_id=candidate_id)
    document_type = _document_type_for_candidate(
        actor=actor,
        candidate=candidate,
        document_type_uuid=document_type_uuid,
    )
    predecessor = _replacement_for_candidate(
        actor=actor,
        candidate=candidate,
        document_uuid=replaces_uuid,
    )
    _validate_version_request(
        actor=actor,
        candidate=candidate,
        person=person,
        document_type=document_type,
        predecessor=predecessor,
        replacement_reason=replacement_reason,
    )
    if document_type.requires_expiry_date and not expires_on:
        raise ValidationError(
            {"expires_on": _("Expiry date is required for this document type.")}
        )
    if issued_on and expires_on and issued_on > expires_on:
        raise ValidationError(
            {"expires_on": _("Expiry date cannot be earlier than issue date.")}
        )
    content_type, size, digest = inspect_upload(
        upload, document_type=document_type
    )
    quarantine = _create_quarantine(
        actor=actor,
        candidate=candidate,
        person=person,
        document_type=document_type,
        predecessor=predecessor,
        upload=upload,
        content_type=content_type,
        size=size,
        digest=digest,
    )
    try:
        with quarantine.file.open("rb") as source:
            result = scan_file(source)
    except ScannerError:
        _mark_quarantine(
            quarantine,
            status=QuarantinedUpload.Status.ERROR,
            scanner_result="scanner_unavailable",
        )
        log_access(
            actor=actor,
            context=audit_context,
            document_uuid=quarantine.uuid,
            action=DocumentAccessLog.Action.UPLOAD,
            outcome=DocumentAccessLog.Outcome.ERROR,
            reason="scanner_unavailable",
        )
        raise ValidationError(
            _("The document could not be security-scanned. Try again later.")
        )

    if not result.clean:
        _mark_quarantine(
            quarantine,
            status=QuarantinedUpload.Status.INFECTED,
            scanner=result.scanner,
            scanner_result=result.result,
        )
        log_access(
            actor=actor,
            context=audit_context,
            document_uuid=quarantine.uuid,
            action=DocumentAccessLog.Action.UPLOAD,
            outcome=DocumentAccessLog.Outcome.DENIED,
            reason="threat_detected",
        )
        raise ValidationError(_("The document was rejected by the security scanner."))

    try:
        return _promote_clean_upload(
            quarantine=quarantine,
            actor=actor,
            title=title,
            issued_on=issued_on,
            expires_on=expires_on,
            replacement_reason=replacement_reason,
            scan_result=result,
            audit_context=audit_context,
        )
    except (Http404, PermissionDenied):
        _mark_quarantine(
            quarantine,
            status=QuarantinedUpload.Status.ERROR,
            scanner=result.scanner,
            scanner_result="scope_changed",
        )
        raise
    except Exception:
        _mark_quarantine(
            quarantine,
            status=QuarantinedUpload.Status.ERROR,
            scanner=result.scanner,
            scanner_result="promotion_failed",
        )
        raise


def _scoped_document(*, actor, document_uuid, for_update=False):
    queryset = PrivateDocument.objects.select_related("candidate")
    if for_update:
        queryset = queryset.select_for_update()
    document = queryset.filter(uuid=document_uuid).first()
    if document is None:
        raise Http404
    linked_candidate_for_user(user=actor, candidate_id=document.candidate_id)
    return document


def set_document_legal_hold(
    *, actor, document_uuid, enabled, reason, audit_context: AccessContext
):
    required = (
        "hydra_documents.view_privatedocument",
        "hydra_documents.manage_privatedocumenthold",
    )
    if not actor.has_perms(required):
        raise PermissionDenied
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError(_("A legal-hold reason is required."))
    with transaction.atomic():
        document = _scoped_document(
            actor=actor, document_uuid=document_uuid, for_update=True
        )
        if document.deleted_at:
            raise ValidationError(_("A deleted document cannot be placed on legal hold."))
        document.legal_hold = enabled
        document.legal_hold_reason = reason[:255] if enabled else ""
        document.legal_hold_applied_at = timezone.now() if enabled else None
        document.legal_hold_applied_by = actor if enabled else None
        document.modified_by = actor
        document.save(
            update_fields=(
                "legal_hold",
                "legal_hold_reason",
                "legal_hold_applied_at",
                "legal_hold_applied_by",
                "modified_by",
            )
        )
        log_access(
            actor=actor,
            context=audit_context,
            document=document,
            document_uuid=document.uuid,
            action=DocumentAccessLog.Action.LEGAL_HOLD,
            outcome=DocumentAccessLog.Outcome.ALLOWED,
            reason="hold_applied" if enabled else "hold_released",
            detail=reason,
        )
    return document


def delete_private_document(
    *, actor, document_uuid, reason, audit_context: AccessContext
):
    required = (
        "hydra_documents.view_privatedocument",
        "hydra_documents.delete_privatedocument",
    )
    if not actor.has_perms(required):
        raise PermissionDenied
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError(_("A deletion reason is required."))
    with transaction.atomic():
        document = _scoped_document(
            actor=actor, document_uuid=document_uuid, for_update=True
        )
        if document.deleted_at:
            raise ValidationError(_("The document is already deleted."))
        if document.legal_hold:
            raise ValidationError(_("The document is protected by a legal hold."))
        if timezone.localdate() < document.retention_until:
            raise ValidationError(
                _("The document must be retained until %(date)s."),
                params={"date": document.retention_until.isoformat()},
            )
        file_name = document.file.name
        document.deleted_at = timezone.now()
        document.deleted_by = actor
        document.deletion_reason = reason[:255]
        document.modified_by = actor
        document.save(
            update_fields=(
                "deleted_at",
                "deleted_by",
                "deletion_reason",
                "modified_by",
            )
        )

    try:
        if file_name:
            document.file.storage.delete(file_name)
    except OSError:
        log_access(
            actor=actor,
            context=audit_context,
            document=document,
            document_uuid=document.uuid,
            action=DocumentAccessLog.Action.DELETE,
            outcome=DocumentAccessLog.Outcome.ERROR,
            reason="storage_purge_failed",
            detail=reason,
        )
        raise ValidationError(
            _("Access was revoked, but storage cleanup must be retried.")
        )

    document.file = ""
    document.file_purged_at = timezone.now()
    document.save(update_fields=("file", "file_purged_at"))
    log_access(
        actor=actor,
        context=audit_context,
        document=document,
        document_uuid=document.uuid,
        action=DocumentAccessLog.Action.DELETE,
        outcome=DocumentAccessLog.Outcome.ALLOWED,
        reason="retention_delete",
        detail=reason,
    )
    return document


def purge_expired_quarantine(*, now=None, limit=1000):
    if limit <= 0 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")
    now = now or timezone.now()
    purged = 0
    ids = list(
        QuarantinedUpload.objects.filter(
            purge_after__lte=now,
            purged_at__isnull=True,
            status__in=(
                QuarantinedUpload.Status.INFECTED,
                QuarantinedUpload.Status.ERROR,
                QuarantinedUpload.Status.PROMOTED,
            ),
        )
        .order_by("purge_after", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    queryset = QuarantinedUpload.objects.filter(pk__in=ids).order_by(
        "purge_after", "pk"
    )
    for quarantine in queryset.iterator():
        try:
            if quarantine.file.name:
                quarantine.file.storage.delete(quarantine.file.name)
        except OSError:
            continue
        QuarantinedUpload.objects.filter(pk=quarantine.pk).update(
            file="", purged_at=now
        )
        purged += 1
    return purged


def purge_deleted_document_files(*, now=None, limit=1000):
    if limit <= 0 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")
    now = now or timezone.now()
    purged = 0
    ids = list(
        PrivateDocument.objects.filter(
            deleted_at__isnull=False,
            file_purged_at__isnull=True,
        )
        .exclude(file="")
        .order_by("deleted_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    queryset = PrivateDocument.objects.filter(pk__in=ids).order_by(
        "deleted_at", "pk"
    )
    for document in queryset.iterator():
        try:
            document.file.storage.delete(document.file.name)
        except OSError:
            continue
        PrivateDocument.objects.filter(pk=document.pk).update(
            file="", file_purged_at=now
        )
        purged += 1
    return purged
