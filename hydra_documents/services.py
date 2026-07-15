import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import File
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from hydra_documents.audit import AccessContext, log_access
from hydra_documents.models import DocumentAccessLog, PrivateDocument
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


def inspect_upload(upload):
    max_bytes = settings.HYDRA_PRIVATE_DOCUMENT_MAX_BYTES
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
    return content_type, total, digest.hexdigest()


@transaction.atomic
def upload_private_document(
    *, actor, candidate_id, title, category, upload, audit_context: AccessContext
):
    required = (
        "hydra_documents.add_privatedocument",
        "hydra_documents.view_privatedocument",
        "hydra_people.view_person",
        "recruitment.view_candidate",
    )
    if not actor.has_perms(required):
        raise PermissionDenied
    candidate = linked_candidate_for_user(user=actor, candidate_id=candidate_id)
    candidate = Candidate._base_manager.select_for_update().get(pk=candidate.pk)
    person = Person.objects.select_for_update().get(
        pk=candidate.hydra_person_link.person_id
    )
    content_type, size, digest = inspect_upload(upload)
    document = PrivateDocument(
        person=person,
        candidate=candidate,
        title=" ".join(title.split()),
        category=category,
        original_filename=_safe_filename(upload.name),
        verified_content_type=content_type,
        size=size,
        sha256=digest,
        created_by=actor,
        modified_by=actor,
    )
    document.full_clean(exclude=("file",))
    saved_name = None
    try:
        document.file.save(upload.name, File(upload), save=False)
        saved_name = document.file.name
        document.save()
        log_access(
            actor=actor,
            context=audit_context,
            document=document,
            document_uuid=document.uuid,
            action=DocumentAccessLog.Action.UPLOAD,
            outcome=DocumentAccessLog.Outcome.ALLOWED,
            reason="uploaded",
        )
    except Exception:
        if saved_name:
            document.file.storage.delete(saved_name)
        raise
    return document
