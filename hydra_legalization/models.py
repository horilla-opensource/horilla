from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from horilla.models import HorillaModel
from hydra_documents.models import PrivateDocument
from hydra_people.models import Person


class LegalizationCase(HorillaModel):
    class CaseType(models.TextChoices):
        WORK_PERMIT = "work_permit", _("Work permit")
        TEMPORARY_RESIDENCE = "temporary_residence", _("Temporary residence")
        VISA = "visa", _("Visa")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        COLLECTING_DOCUMENTS = "collecting_documents", _("Collecting documents")
        SUBMITTED = "submitted", _("Submitted")
        ADDITIONAL_INFORMATION = "additional_information", _("Additional information")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        EXPIRED = "expired", _("Expired")
        CLOSED = "closed", _("Closed")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="legalization_cases"
    )
    case_type = models.CharField(max_length=32, choices=CaseType.choices)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.DRAFT, editable=False
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responsible_legalization_cases",
    )
    reference_number = models.CharField(max_length=100, blank=True)
    deadline = models.DateField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, max_length=1000)

    class Meta:
        ordering = ("deadline", "person__passport_name", "pk")
        permissions = (
            ("assign_legalizationcase", "Can assign legalization cases"),
            ("transition_legalizationcase", "Can transition legalization cases"),
            ("link_privatedocument", "Can link private documents to legalization cases"),
        )
        indexes = (
            models.Index(fields=("person", "status"), name="hydra_leg_person_status_idx"),
            models.Index(fields=("responsible", "status"), name="hydra_leg_owner_status_idx"),
            models.Index(fields=("deadline",), name="hydra_leg_deadline_idx"),
        )

    def __str__(self):
        return f"{self.person.hydra_id} — {self.get_case_type_display()}"

    def get_absolute_url(self):
        return reverse("hydra-legalization-detail", kwargs={"case_uuid": self.uuid})

    @property
    def is_overdue(self):
        terminal = {
            self.Status.APPROVED,
            self.Status.REJECTED,
            self.Status.EXPIRED,
            self.Status.CLOSED,
        }
        return bool(
            self.deadline
            and self.deadline < timezone.localdate()
            and self.status not in terminal
        )

    def clean(self):
        super().clean()
        self.reference_number = " ".join(self.reference_number.split())
        self.notes = self.notes.strip()
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError(
                {"valid_until": _("Valid until cannot be earlier than valid from.")}
            )
        if self.status == self.Status.APPROVED and not (
            self.valid_from and self.valid_until
        ):
            raise ValidationError(
                {"valid_until": _("Approved cases require a complete validity period.")}
            )
        if self.status == self.Status.EXPIRED:
            if not self.valid_until:
                raise ValidationError(
                    {"valid_until": _("Expired cases require a validity end date.")}
                )
            if self.valid_until > timezone.localdate():
                raise ValidationError(
                    {"valid_until": _("A case cannot expire before its validity end date.")}
                )


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Legalization history is append-only.")

    def delete(self):
        raise TypeError("Legalization history is append-only.")


class LegalizationStatusHistory(models.Model):
    case = models.ForeignKey(
        LegalizationCase, on_delete=models.PROTECT, related_name="status_history"
    )
    from_status = models.CharField(
        max_length=32, choices=LegalizationCase.Status.choices, blank=True
    )
    to_status = models.CharField(max_length=32, choices=LegalizationCase.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (("view_legalizationstatushistory", "Can view legalization status history"),)
        indexes = (
            models.Index(fields=("case", "occurred_at"), name="hydra_leg_history_idx"),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Legalization history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization history is append-only.")


class LegalizationCaseDocument(HorillaModel):
    class Role(models.TextChoices):
        IDENTITY = "identity", _("Identity evidence")
        APPLICATION = "application", _("Application")
        DECISION = "decision", _("Decision")
        OTHER = "other", _("Other")

    case = models.ForeignKey(
        LegalizationCase, on_delete=models.PROTECT, related_name="document_links"
    )
    document = models.ForeignKey(
        PrivateDocument,
        on_delete=models.PROTECT,
        related_name="legalization_links",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OTHER)

    class Meta:
        ordering = ("created_at", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("case", "document"), name="hydra_leg_case_document_uniq"
            ),
        )

    def clean(self):
        super().clean()
        if self.case_id and self.document_id:
            if self.case.person_id != self.document.person_id:
                raise ValidationError(
                    {"document": _("The document must belong to the case person.")}
                )

    def __str__(self):
        return f"{self.case} — {self.document.title}"
