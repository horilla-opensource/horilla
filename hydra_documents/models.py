from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company
from horilla.models import HorillaModel
from hydra_documents.storage import private_document_storage, quarantine_storage
from hydra_people.models import Person
from recruitment.models import Candidate


SUPPORTED_PRIVATE_CONTENT_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
)


class DocumentCategory(models.TextChoices):
    IDENTITY = "identity", _("Identity")
    RECRUITMENT = "recruitment", _("Recruitment")
    LEGALIZATION = "legalization", _("Legalization")
    OTHER = "other", _("Other")


def default_allowed_content_types():
    return list(SUPPORTED_PRIVATE_CONTENT_TYPES)


def default_type_max_bytes():
    return settings.HYDRA_PRIVATE_DOCUMENT_MAX_BYTES


def default_type_retention_days():
    return settings.HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS


def private_document_path(instance, filename):
    extension = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }[instance.verified_content_type]
    identifier = instance.uuid.hex
    return f"candidate-documents/{identifier[:2]}/{identifier}{extension}"


def quarantined_upload_path(instance, filename):
    identifier = instance.uuid.hex
    return f"quarantine/{identifier[:2]}/{identifier}.upload"


def default_retention_until():
    return timezone.localdate() + timedelta(
        days=settings.HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS
    )


class PrivateDocumentType(HorillaModel):
    """Fixed-field, company-scoped rules for future private-document uploads."""

    Category = DocumentCategory

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_private_document_types",
        null=True,
        blank=True,
        help_text=_("Leave empty only for a global system type."),
    )
    code = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=DocumentCategory.choices,
        default=DocumentCategory.OTHER,
    )
    allowed_content_types = models.JSONField(default=default_allowed_content_types)
    max_size_bytes = models.PositiveBigIntegerField(default=default_type_max_bytes)
    retention_days = models.PositiveIntegerField(default=default_type_retention_days)
    requires_expiry_date = models.BooleanField(default=False)
    single_current = models.BooleanField(
        default=True,
        help_text=_("Require an existing current version to be explicitly replaced."),
    )

    class Meta:
        ordering = ("company__company", "name", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code"),
                condition=models.Q(company__isnull=False),
                name="hydra_doc_type_company_code_uniq",
            ),
            models.UniqueConstraint(
                fields=("code",),
                condition=models.Q(company__isnull=True),
                name="hydra_doc_type_global_code_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(max_size_bytes__gt=0),
                name="hydra_doc_type_size_positive",
            ),
            models.CheckConstraint(
                check=models.Q(retention_days__gt=0),
                name="hydra_doc_type_retention_positive",
            ),
        )

    def __str__(self):
        scope = str(self.company) if self.company_id else str(_("Global"))
        return f"{scope} / {self.name}"

    def clean(self):
        super().clean()
        self.code = self.code.strip().lower()
        self.name = " ".join(self.name.split())
        allowed = self.allowed_content_types
        if not isinstance(allowed, list) or not allowed:
            raise ValidationError(
                {"allowed_content_types": _("Choose at least one supported content type.")}
            )
        if any(value not in SUPPORTED_PRIVATE_CONTENT_TYPES for value in allowed):
            raise ValidationError(
                {"allowed_content_types": _("Only PDF, JPEG and PNG rules are supported.")}
            )
        self.allowed_content_types = sorted(set(allowed))
        if self.max_size_bytes > settings.HYDRA_PRIVATE_DOCUMENT_MAX_BYTES:
            raise ValidationError(
                {
                    "max_size_bytes": _(
                        "A type cannot exceed the global private-document size limit."
                    )
                }
            )
        if self.retention_days > 36500:
            raise ValidationError(
                {"retention_days": _("Retention cannot exceed 100 years.")}
            )

    def rules_snapshot(self):
        return {
            "type_uuid": str(self.uuid),
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "company_id": self.company_id,
            "allowed_content_types": list(self.allowed_content_types),
            "max_size_bytes": self.max_size_bytes,
            "retention_days": self.retention_days,
            "requires_expiry_date": self.requires_expiry_date,
            "single_current": self.single_current,
        }


class PrivateDocumentQuerySet(models.QuerySet):
    immutable_version_fields = {
        "person_id",
        "candidate_id",
        "document_type_id",
        "category",
        "lineage_uuid",
        "version_number",
        "replaces_id",
        "replacement_reason",
        "type_rules_snapshot",
        "issued_on",
        "expires_on",
        "original_filename",
        "verified_content_type",
        "size",
        "sha256",
    }

    def update(self, **kwargs):
        aliases = {
            "person": "person_id",
            "candidate": "candidate_id",
            "document_type": "document_type_id",
            "replaces": "replaces_id",
        }
        updated = {aliases.get(field, field) for field in kwargs}
        if self.immutable_version_fields.intersection(updated):
            raise TypeError("Private-document version identity is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Private documents use retention-controlled tombstones.")


class PrivateDocument(HorillaModel):
    Category = DocumentCategory

    objects = PrivateDocumentQuerySet.as_manager()

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="private_documents"
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name="hydra_private_documents"
    )
    document_type = models.ForeignKey(
        PrivateDocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    title = models.CharField(max_length=160)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    file = models.FileField(
        storage=private_document_storage,
        upload_to=private_document_path,
        max_length=255,
        blank=True,
    )
    original_filename = models.CharField(max_length=255)
    verified_content_type = models.CharField(max_length=50)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, editable=False)
    lineage_uuid = models.UUIDField(default=uuid4, editable=False)
    version_number = models.PositiveIntegerField(default=1, editable=False)
    replaces = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="replaced_by",
        null=True,
        blank=True,
        editable=False,
    )
    replacement_reason = models.CharField(max_length=255, blank=True, editable=False)
    type_rules_snapshot = models.JSONField(default=dict, editable=False)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True, db_index=True)
    scanner = models.CharField(max_length=80, blank=True, editable=False)
    scanned_at = models.DateTimeField(null=True, blank=True, editable=False)
    retention_until = models.DateField(default=default_retention_until, db_index=True)
    legal_hold = models.BooleanField(default=False)
    legal_hold_reason = models.CharField(max_length=255, blank=True)
    legal_hold_applied_at = models.DateTimeField(null=True, blank=True, editable=False)
    legal_hold_applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_document_holds_applied",
        null=True,
        blank=True,
        editable=False,
    )
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_private_documents_deleted",
        null=True,
        blank=True,
        editable=False,
    )
    deletion_reason = models.CharField(max_length=255, blank=True, editable=False)
    file_purged_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (
            ("download_privatedocument", "Can download private document"),
            ("manage_privatedocumenthold", "Can manage private document legal hold"),
            ("replace_privatedocument", "Can upload a replacement document version"),
        )
        indexes = (
            models.Index(fields=("candidate", "created_at"), name="hydra_doc_candidate_idx"),
            models.Index(fields=("person", "created_at"), name="hydra_doc_person_idx"),
            models.Index(
                fields=("candidate", "document_type", "version_number"),
                name="hydra_doc_type_version_idx",
            ),
            models.Index(
                fields=("lineage_uuid", "version_number"),
                name="hydra_doc_lineage_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("lineage_uuid", "version_number"),
                name="hydra_doc_lineage_version_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(version_number__gte=1),
                name="hydra_doc_version_positive",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(replaces__isnull=True, version_number=1)
                    | models.Q(replaces__isnull=False, version_number__gt=1)
                ),
                name="hydra_doc_version_shape",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(replaces__isnull=True)
                    | ~models.Q(replaces_id=models.F("pk"))
                ),
                name="hydra_doc_no_self_replace",
            ),
        )

    def clean(self):
        super().clean()
        if self.document_type_id:
            document_type = self.document_type
            if self.category != document_type.category:
                raise ValidationError(
                    {"category": _("Category must match the logical document type.")}
                )
            company_id = getattr(
                getattr(self.candidate, "recruitment_id", None),
                "company_id_id",
                None,
            )
            if document_type.company_id and document_type.company_id != company_id:
                raise ValidationError(
                    {"document_type": _("Document type is outside the application company.")}
                )
            if self.verified_content_type not in document_type.allowed_content_types:
                raise ValidationError(
                    {"verified_content_type": _("Content type is not allowed by this document type.")}
                )
            if self.size > document_type.max_size_bytes:
                raise ValidationError(
                    {"size": _("File exceeds the limit configured for this document type.")}
                )
            if document_type.requires_expiry_date and not self.expires_on:
                raise ValidationError(
                    {"expires_on": _("Expiry date is required for this document type.")}
                )
            if not self.type_rules_snapshot:
                self.type_rules_snapshot = document_type.rules_snapshot()
        if self.issued_on and self.expires_on and self.issued_on > self.expires_on:
            raise ValidationError(
                {"expires_on": _("Expiry date cannot be earlier than issue date.")}
            )
        if self.replaces_id:
            predecessor = self.replaces
            if predecessor.pk == self.pk:
                raise ValidationError({"replaces": _("A document cannot replace itself.")})
            if predecessor.candidate_id != self.candidate_id:
                raise ValidationError(
                    {"replaces": _("A replacement must belong to the same application.")}
                )
            if predecessor.person_id != self.person_id:
                raise ValidationError(
                    {"replaces": _("A replacement must belong to the same Person.")}
                )
            if predecessor.document_type_id != self.document_type_id:
                raise ValidationError(
                    {"replaces": _("A replacement must use the same document type.")}
                )
            if predecessor.deleted_at:
                raise ValidationError(
                    {"replaces": _("A deleted document cannot be replaced.")}
                )
            if self.lineage_uuid != predecessor.lineage_uuid:
                raise ValidationError(
                    {"lineage_uuid": _("A replacement must preserve its version lineage.")}
                )
            if self.version_number != predecessor.version_number + 1:
                raise ValidationError(
                    {"version_number": _("Replacement version number is invalid.")}
                )
            if len(" ".join(self.replacement_reason.split())) < 10:
                raise ValidationError(
                    {"replacement_reason": _("Provide a replacement reason of at least 10 characters.")}
                )
        elif self.version_number != 1:
            raise ValidationError(
                {"version_number": _("An initial document must be version 1.")}
            )

    def save(self, *args, **kwargs):
        if self.pk:
            immutable = PrivateDocumentQuerySet.immutable_version_fields
            previous = PrivateDocument._base_manager.filter(pk=self.pk).values(
                *immutable
            ).first()
            if previous and any(
                previous[field] != getattr(self, field) for field in immutable
            ):
                raise TypeError("Private-document version identity is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Private documents use retention-controlled tombstones.")

    def __str__(self):
        return f"{self.person.hydra_id} — {self.title}"


    @property
    def is_downloadable(self):
        return bool(self.file and self.scanned_at and not self.deleted_at)

    @property
    def is_current_version(self):
        try:
            self.replaced_by
        except PrivateDocument.DoesNotExist:
            return True
        return False


class QuarantinedUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending scan")
        INFECTED = "infected", _("Threat detected")
        ERROR = "error", _("Scan error")
        PROMOTED = "promoted", _("Promoted")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="quarantined_uploads"
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_quarantined_uploads",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_quarantined_uploads",
    )
    document = models.ForeignKey(
        PrivateDocument,
        on_delete=models.PROTECT,
        related_name="quarantine_records",
        null=True,
        blank=True,
    )
    document_type = models.ForeignKey(
        PrivateDocumentType,
        on_delete=models.PROTECT,
        related_name="quarantine_records",
        null=True,
        blank=True,
    )
    replaces = models.ForeignKey(
        PrivateDocument,
        on_delete=models.PROTECT,
        related_name="replacement_quarantine_records",
        null=True,
        blank=True,
    )
    file = models.FileField(
        storage=quarantine_storage,
        upload_to=quarantined_upload_path,
        max_length=255,
        blank=True,
    )
    original_filename = models.CharField(max_length=255)
    verified_content_type = models.CharField(max_length=50)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, editable=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    scanner = models.CharField(max_length=80, blank=True, editable=False)
    scanner_result = models.CharField(max_length=160, blank=True, editable=False)
    scan_completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    purge_after = models.DateTimeField(db_index=True)
    purged_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        default_permissions = ()
        permissions = (("view_quarantinedupload", "Can view quarantined upload"),)
        indexes = (
            models.Index(
                fields=("status", "purge_after"), name="hydra_doc_quarantine_idx"
            ),
        )


class ImmutableAccessLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Document access logs are append-only.")

    def delete(self):
        raise TypeError("Document access logs are append-only.")


class DocumentAccessLog(models.Model):
    class Action(models.TextChoices):
        UPLOAD = "upload", _("Upload")
        DOWNLOAD = "download", _("Download")
        SCAN = "scan", _("Scan")
        LEGAL_HOLD = "legal_hold", _("Legal hold")
        DELETE = "delete", _("Delete")

    class Outcome(models.TextChoices):
        ALLOWED = "allowed", _("Allowed")
        DENIED = "denied", _("Denied")
        NOT_FOUND = "not_found", _("Not found")
        ERROR = "error", _("Error")

    document = models.ForeignKey(
        PrivateDocument,
        on_delete=models.PROTECT,
        related_name="access_logs",
        null=True,
        blank=True,
    )
    document_uuid = models.UUIDField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_document_access_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    reason = models.CharField(max_length=48)
    detail = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent_sha256 = models.CharField(max_length=64, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableAccessLogQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (("view_documentaccesslog", "Can view document access log"),)
        indexes = (
            models.Index(fields=("document_uuid", "occurred_at"), name="hydra_doc_access_idx"),
            models.Index(fields=("actor", "occurred_at"), name="hydra_doc_actor_idx"),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Document access logs are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Document access logs are append-only.")
