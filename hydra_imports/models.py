from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import JobPosition
from hydra.models import HorillaModel
from hydra_people.models import Person
from recruitment.models import Candidate, Recruitment


class CandidateImportSession(HorillaModel):
    class Status(models.TextChoices):
        READY = "ready", _("Ready to apply")
        BLOCKED = "blocked", _("Blocked")
        APPLIED = "applied", _("Applied")
        EXPIRED = "expired", _("Expired and redacted")

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
    fingerprint = models.CharField(max_length=64, editable=False)
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
    sensitive_data_purge_after = models.DateTimeField(editable=False, db_index=True)
    sensitive_data_purged_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (
            ("import_candidate", "Can preview and apply candidate imports"),
            ("purge_candidateimportsession", "Can discard candidate import source data"),
        )
        indexes = (
            models.Index(fields=("created_by", "status"), name="hydra_imp_owner_status_idx"),
            models.Index(fields=("recruitment", "status"), name="hydra_imp_recruit_status_idx"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("fingerprint",),
                condition=models.Q(status__in=("ready", "blocked", "applied")),
                name="hydra_imp_active_fingerprint_uniq",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(status="expired")
                    | models.Q(sensitive_data_purged_at__isnull=False)
                ),
                name="hydra_imp_expired_is_purged",
            ),
        )

    def __str__(self):
        return f"{self.source_filename_for_display} — {self.lifecycle_status_display}"

    def get_absolute_url(self):
        return reverse("hydra-candidate-import-detail", kwargs={"session_uuid": self.uuid})

    @property
    def sensitive_data_available(self):
        return bool(
            self.sensitive_data_purged_at is None
            and self.sensitive_data_purge_after
            and self.sensitive_data_purge_after > timezone.now()
        )

    @property
    def can_apply(self):
        return self.status == self.Status.READY and self.sensitive_data_available

    @property
    def source_filename_for_display(self):
        if self.sensitive_data_available:
            return self.source_filename
        return _("Retained import audit")

    @property
    def lifecycle_status_display(self):
        if (
            self.status in {self.Status.READY, self.Status.BLOCKED}
            and not self.sensitive_data_available
        ):
            return self.Status.EXPIRED.label
        return self.get_status_display()


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


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Candidate import lifecycle events are append-only.")

    def delete(self):
        raise TypeError("Candidate import lifecycle events are append-only.")


class CandidateImportLifecycleEvent(models.Model):
    class EventType(models.TextChoices):
        SENSITIVE_DATA_PURGED = "sensitive_data_purged", _("Sensitive data purged")

    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

    class Reason(models.TextChoices):
        RETENTION_EXPIRED = "retention_expired", _("Retention expired")
        MANUALLY_DISCARDED = "manually_discarded", _("Manually discarded")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    session = models.ForeignKey(
        CandidateImportSession,
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    source = models.CharField(max_length=12, choices=Source.choices)
    reason = models.CharField(max_length=32, choices=Reason.choices)
    previous_status = models.CharField(
        max_length=16,
        choices=CandidateImportSession.Status.choices,
    )
    resulting_status = models.CharField(
        max_length=16,
        choices=CandidateImportSession.Status.choices,
    )
    rows_redacted = models.PositiveIntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="candidate_import_lifecycle_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("session", "event_type"),
                name="hydra_imp_lifecycle_once",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(source="user", actor__isnull=False)
                    | models.Q(source="system", actor__isnull=True)
                ),
                name="hydra_imp_lifecycle_source_actor",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Candidate import lifecycle events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Candidate import lifecycle events are append-only.")
