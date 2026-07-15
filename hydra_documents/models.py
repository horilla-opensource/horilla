from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from horilla.models import HorillaModel
from hydra_documents.storage import private_document_storage
from hydra_people.models import Person
from recruitment.models import Candidate


def private_document_path(instance, filename):
    extension = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }[instance.verified_content_type]
    identifier = instance.uuid.hex
    return f"candidate-documents/{identifier[:2]}/{identifier}{extension}"


class PrivateDocument(HorillaModel):
    class Category(models.TextChoices):
        IDENTITY = "identity", _("Identity")
        RECRUITMENT = "recruitment", _("Recruitment")
        OTHER = "other", _("Other")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="private_documents"
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name="hydra_private_documents"
    )
    title = models.CharField(max_length=160)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    file = models.FileField(
        storage=private_document_storage,
        upload_to=private_document_path,
        max_length=255,
    )
    original_filename = models.CharField(max_length=255)
    verified_content_type = models.CharField(max_length=50)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (("download_privatedocument", "Can download private document"),)
        indexes = (
            models.Index(fields=("candidate", "created_at"), name="hydra_doc_candidate_idx"),
            models.Index(fields=("person", "created_at"), name="hydra_doc_person_idx"),
        )

    def __str__(self):
        return f"{self.person.hydra_id} — {self.title}"


class ImmutableAccessLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Document access logs are append-only.")

    def delete(self):
        raise TypeError("Document access logs are append-only.")


class DocumentAccessLog(models.Model):
    class Action(models.TextChoices):
        UPLOAD = "upload", _("Upload")
        DOWNLOAD = "download", _("Download")

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
