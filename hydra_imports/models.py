from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.models import JobPosition
from horilla.models import HorillaModel
from hydra_people.models import Person
from recruitment.models import Candidate, Recruitment


class CandidateImportSession(HorillaModel):
    class Status(models.TextChoices):
        READY = "ready", _("Ready to apply")
        BLOCKED = "blocked", _("Blocked")
        APPLIED = "applied", _("Applied")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    recruitment = models.ForeignKey(
        Recruitment,
        on_delete=models.PROTECT,
        related_name="hydra_candidate_imports",
    )
    job_position = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        related_name="hydra_candidate_imports",
    )
    source_filename = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64, editable=False)
    fingerprint = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.BLOCKED,
        editable=False,
    )
    row_count = models.PositiveIntegerField(default=0, editable=False)
    valid_count = models.PositiveIntegerField(default=0, editable=False)
    duplicate_count = models.PositiveIntegerField(default=0, editable=False)
    error_count = models.PositiveIntegerField(default=0, editable=False)
    applied_at = models.DateTimeField(null=True, blank=True, editable=False)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="applied_candidate_imports",
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (("import_candidate", "Can preview and apply candidate imports"),)
        indexes = (
            models.Index(fields=("created_by", "status"), name="hydra_imp_owner_status_idx"),
            models.Index(fields=("recruitment", "status"), name="hydra_imp_recruit_status_idx"),
        )

    def __str__(self):
        return f"{self.source_filename} — {self.get_status_display()}"

    def get_absolute_url(self):
        return reverse("hydra-candidate-import-detail", kwargs={"session_uuid": self.uuid})


class CandidateImportRow(models.Model):
    class Outcome(models.TextChoices):
        VALID = "valid", _("Valid")
        ERROR = "error", _("Error")
        DUPLICATE = "duplicate", _("Duplicate")

    session = models.ForeignKey(
        CandidateImportSession,
        on_delete=models.PROTECT,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    error_message = models.TextField(blank=True, max_length=2000)
    duplicate_reason = models.TextField(blank=True, max_length=1000)
    source_row_hash = models.CharField(max_length=64, editable=False)

    passport_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, blank=True)
    citizenship = models.CharField(max_length=2, blank=True)
    preferred_language = models.CharField(max_length=3, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=25, blank=True)
    whatsapp_viber = models.CharField(max_length=25, blank=True)
    candidate_mobile = models.CharField(max_length=15, blank=True)

    created_person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="candidate_import_rows",
    )
    created_candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="hydra_import_rows",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("row_number", "pk")
        default_permissions = ()
        constraints = (
            models.UniqueConstraint(
                fields=("session", "row_number"),
                name="hydra_imp_session_row_uniq",
            ),
        )
        indexes = (
            models.Index(fields=("session", "outcome"), name="hydra_imp_row_outcome_idx"),
        )

    def __str__(self):
        return f"{self.session_id}:{self.row_number} — {self.get_outcome_display()}"
