from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra.models import HorillaModel
from hydra_documents.models import PrivateDocument, PrivateDocumentType
from hydra_people.models import Person


LEGALIZATION_DELEGATION_MAX_DURATION_DAYS = 90


class LegalizationCaseType(models.TextChoices):
    WORK_PERMIT = "work_permit", _("Work permit")
    TEMPORARY_RESIDENCE = "temporary_residence", _("Temporary residence")
    VISA = "visa", _("Visa")
    OTHER = "other", _("Other")


class LegalizationStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    COLLECTING_DOCUMENTS = "collecting_documents", _("Collecting documents")
    SUBMITTED = "submitted", _("Submitted")
    ADDITIONAL_INFORMATION = "additional_information", _("Additional information")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")
    CLOSED = "closed", _("Closed")


class LegalizationAuthorityEventChannel(models.TextChoices):
    ONLINE_PORTAL = "online_portal", _("Online portal")
    IN_PERSON = "in_person", _("In person")
    POST = "post", _("Post")
    EMAIL = "email", _("Email")
    OTHER = "other", _("Other")


class LegalizationConfigurationQuerySet(models.QuerySet):
    def delete(self):
        raise TypeError("Legalization configuration must be deactivated, not deleted.")


class LegalizationAuthority(HorillaModel):
    """Approved authority dictionary; company NULL denotes a system-wide entry."""

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_legalization_authorities",
        null=True,
        blank=True,
    )
    code = models.SlugField(max_length=60)
    name = models.CharField(max_length=200)
    jurisdiction = models.CharField(max_length=200, blank=True)
    allowed_channels = models.JSONField(default=list)

    objects = LegalizationConfigurationQuerySet.as_manager()

    class Meta:
        ordering = ("company__company", "name", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code"),
                condition=models.Q(company__isnull=False),
                name="hydra_leg_authority_company_code_uniq",
            ),
            models.UniqueConstraint(
                fields=("code",),
                condition=models.Q(company__isnull=True),
                name="hydra_leg_authority_global_code_uniq",
            ),
        )

    def clean(self):
        super().clean()
        self.code = self.code.strip().lower()
        self.name = " ".join(self.name.split())
        self.jurisdiction = " ".join(self.jurisdiction.split())
        supported = {value for value, _label in LegalizationAuthorityEventChannel.choices}
        if not isinstance(self.allowed_channels, list) or not self.allowed_channels:
            raise ValidationError(
                {"allowed_channels": _("Choose at least one authority channel.")}
            )
        if any(value not in supported for value in self.allowed_channels):
            raise ValidationError(
                {"allowed_channels": _("An unsupported authority channel was selected.")}
            )
        self.allowed_channels = sorted(set(self.allowed_channels))

    def snapshot(self):
        return {
            "uuid": str(self.uuid),
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "jurisdiction": self.jurisdiction,
            "allowed_channels": list(self.allowed_channels),
        }

    def __str__(self):
        scope = str(self.company) if self.company_id else str(_("Global"))
        return f"{scope} / {self.name}"

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization configuration must be deactivated, not deleted.")


class LegalizationProcedureType(HorillaModel):
    """Fixed-field procedure configuration whose rules are snapshotted per case."""

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_legalization_procedures",
        null=True,
        blank=True,
    )
    code = models.SlugField(max_length=60)
    name = models.CharField(max_length=160)
    case_type = models.CharField(max_length=32, choices=LegalizationCaseType.choices)
    description = models.TextField(blank=True, max_length=1000)
    default_deadline_days = models.PositiveSmallIntegerField(null=True, blank=True)
    renewal_lead_days = models.PositiveSmallIntegerField(default=90)
    requires_authority = models.BooleanField(default=True)
    authorities = models.ManyToManyField(
        LegalizationAuthority,
        related_name="procedures",
        blank=True,
    )

    objects = LegalizationConfigurationQuerySet.as_manager()

    class Meta:
        ordering = ("company__company", "name", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code"),
                condition=models.Q(company__isnull=False),
                name="hydra_leg_procedure_company_code_uniq",
            ),
            models.UniqueConstraint(
                fields=("code",),
                condition=models.Q(company__isnull=True),
                name="hydra_leg_procedure_global_code_uniq",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(default_deadline_days__isnull=True)
                    | models.Q(default_deadline_days__gt=0)
                ),
                name="hydra_leg_procedure_deadline_positive",
            ),
            models.CheckConstraint(
                check=models.Q(renewal_lead_days__gt=0),
                name="hydra_leg_procedure_renewal_positive",
            ),
        )

    def clean(self):
        super().clean()
        self.code = self.code.strip().lower()
        self.name = " ".join(self.name.split())
        self.description = self.description.strip()
        if self.default_deadline_days and self.default_deadline_days > 3650:
            raise ValidationError(
                {"default_deadline_days": _("The default deadline cannot exceed ten years.")}
            )
        if self.renewal_lead_days > 3650:
            raise ValidationError(
                {"renewal_lead_days": _("The renewal lead time cannot exceed ten years.")}
            )

    def rules_snapshot(self, *, company_id):
        statuses = [
            {"status": row.status, "label": row.label, "sort_order": row.sort_order}
            for row in self.status_rules.filter(is_active=True).order_by(
                "sort_order", "pk"
            )
        ]
        requirements = [
            {
                "uuid": str(row.uuid),
                "code": row.code,
                "name": row.name,
                "document_type_uuid": str(row.document_type.uuid),
                "document_type_name": row.document_type.name,
                "required_before_status": row.required_before_status,
            }
            for row in self.requirements.filter(is_active=True)
            .select_related("document_type")
            .order_by("sort_order", "pk")
        ]
        authorities = [
            row.snapshot()
            for row in self.authorities.filter(is_active=True).filter(
                models.Q(company__isnull=True) | models.Q(company_id=company_id)
            )
        ]
        return {
            "procedure_uuid": str(self.uuid),
            "procedure_company_id": self.company_id,
            "case_company_id": company_id,
            "code": self.code,
            "name": self.name,
            "case_type": self.case_type,
            "default_deadline_days": self.default_deadline_days,
            "renewal_lead_days": self.renewal_lead_days,
            "requires_authority": self.requires_authority,
            "statuses": statuses,
            "requirements": requirements,
            "authorities": authorities,
        }

    def __str__(self):
        scope = str(self.company) if self.company_id else str(_("Global"))
        return f"{scope} / {self.name}"

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization configuration must be deactivated, not deleted.")


class LegalizationCaseQuerySet(models.QuerySet):
    IMMUTABLE_CONFIGURATION_FIELDS = {
        "person_id",
        "company_id",
        "procedure_type_id",
        "case_type",
        "procedure_snapshot",
    }

    def update(self, **kwargs):
        aliases = {
            "person": "person_id",
            "company": "company_id",
            "procedure_type": "procedure_type_id",
        }
        fields = {aliases.get(field, field) for field in kwargs}
        if fields.intersection(self.IMMUTABLE_CONFIGURATION_FIELDS):
            raise TypeError("Legalization case procedure identity is immutable.")
        return super().update(**kwargs)


class LegalizationCase(HorillaModel):
    CaseType = LegalizationCaseType
    Status = LegalizationStatus

    objects = LegalizationCaseQuerySet.as_manager()

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="legalization_cases"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_legalization_cases",
    )
    procedure_type = models.ForeignKey(
        LegalizationProcedureType,
        on_delete=models.PROTECT,
        related_name="cases",
    )
    case_type = models.CharField(max_length=32, choices=CaseType.choices)
    procedure_snapshot = models.JSONField(default=dict, editable=False)
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
            ("view_legalizationworkload", "Can view legalization workload"),
            ("transition_legalizationcase", "Can transition legalization cases"),
            ("link_privatedocument", "Can link private documents to legalization cases"),
            (
                "receive_legalization_escalations",
                "Can receive scoped legalization escalations",
            ),
        )
        indexes = (
            models.Index(fields=("company", "status"), name="hydra_leg_company_status_idx"),
            models.Index(fields=("person", "status"), name="hydra_leg_person_status_idx"),
            models.Index(fields=("responsible", "status"), name="hydra_leg_owner_status_idx"),
            models.Index(fields=("deadline",), name="hydra_leg_deadline_idx"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("person", "company", "procedure_type"),
                condition=models.Q(
                    status__in=(
                        "draft",
                        "collecting_documents",
                        "submitted",
                        "additional_information",
                    )
                ),
                name="hydra_leg_active_procedure_uniq",
            ),
        )

    def __str__(self):
        return f"{self.person.hydra_id} — {self.procedure_name}"

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
        if self.procedure_type_id:
            if self.procedure_type.company_id not in (None, self.company_id):
                raise ValidationError(
                    {"procedure_type": _("The procedure is outside the case company.")}
                )
            if self.case_type != self.procedure_type.case_type:
                raise ValidationError(
                    {"procedure_type": _("The procedure classifier does not match the case.")}
                )
        snapshot = self.procedure_snapshot
        required_snapshot_keys = {
            "procedure_uuid",
            "case_company_id",
            "case_type",
            "name",
            "statuses",
            "requirements",
            "authorities",
        }
        if not isinstance(snapshot, dict) or not required_snapshot_keys.issubset(snapshot):
            raise ValidationError(
                {"procedure_type": _("A complete immutable procedure snapshot is required.")}
            )
        if self.procedure_type_id and snapshot.get("procedure_uuid") != str(
            self.procedure_type.uuid
        ):
            raise ValidationError(
                {"procedure_type": _("The procedure snapshot does not match the case.")}
            )
        if snapshot.get("case_company_id") != self.company_id:
            raise ValidationError(
                {"company": _("The procedure snapshot does not match the case company.")}
            )
        enabled_statuses = {
            row.get("status")
            for row in snapshot.get("statuses", [])
            if isinstance(row, dict)
        }
        if self.status not in enabled_statuses:
            raise ValidationError(
                {"status": _("The status is disabled in this case procedure snapshot.")}
            )
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

    @property
    def procedure_name(self):
        return self.procedure_snapshot.get("name") or self.procedure_type.name

    @property
    def configured_status_label(self):
        labels = {
            row.get("status"): row.get("label")
            for row in self.procedure_snapshot.get("statuses", [])
            if isinstance(row, dict)
        }
        return labels.get(self.status) or self.get_status_display()

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self)._base_manager.values(
                "person_id",
                "company_id",
                "procedure_type_id",
                "case_type",
                "procedure_snapshot",
            ).get(pk=self.pk)
            if any(
                original[field] != getattr(self, field)
                for field in LegalizationCaseQuerySet.IMMUTABLE_CONFIGURATION_FIELDS
            ):
                raise TypeError("Legalization case procedure identity is immutable.")
        return super().save(*args, **kwargs)


class LegalizationProcedureStatus(HorillaModel):
    procedure = models.ForeignKey(
        LegalizationProcedureType,
        on_delete=models.PROTECT,
        related_name="status_rules",
    )
    status = models.CharField(max_length=32, choices=LegalizationStatus.choices)
    label = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0)

    objects = LegalizationConfigurationQuerySet.as_manager()

    class Meta:
        ordering = ("procedure", "sort_order", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("procedure", "status"),
                name="hydra_leg_procedure_status_uniq",
            ),
        )

    def clean(self):
        super().clean()
        self.label = " ".join(self.label.split())
        if not self.label:
            raise ValidationError({"label": _("A status label is required.")})

    def __str__(self):
        return f"{self.procedure} / {self.label}"

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization configuration must be deactivated, not deleted.")


class LegalizationProcedureRequirement(HorillaModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    procedure = models.ForeignKey(
        LegalizationProcedureType,
        on_delete=models.PROTECT,
        related_name="requirements",
    )
    code = models.SlugField(max_length=60)
    name = models.CharField(max_length=160)
    document_type = models.ForeignKey(
        PrivateDocumentType,
        on_delete=models.PROTECT,
        related_name="legalization_requirements",
    )
    required_before_status = models.CharField(
        max_length=32,
        choices=LegalizationStatus.choices,
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    objects = LegalizationConfigurationQuerySet.as_manager()

    class Meta:
        ordering = ("procedure", "sort_order", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("procedure", "code"),
                name="hydra_leg_requirement_code_uniq",
            ),
            models.UniqueConstraint(
                fields=("procedure", "document_type", "required_before_status"),
                name="hydra_leg_requirement_type_status_uniq",
            ),
        )

    def clean(self):
        super().clean()
        self.code = self.code.strip().lower()
        self.name = " ".join(self.name.split())
        if self.document_type_id and self.procedure_id:
            type_company = self.document_type.company_id
            procedure_company = self.procedure.company_id
            if type_company is not None and type_company != procedure_company:
                raise ValidationError(
                    {"document_type": _("The document type is outside the procedure company.")}
                )

    def __str__(self):
        return f"{self.procedure} / {self.name}"

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization configuration must be deactivated, not deleted.")


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Legalization history is append-only.")

    def delete(self):
        raise TypeError("Legalization history is append-only.")


class LegalizationConfigurationEvent(models.Model):
    class EntityType(models.TextChoices):
        PROCEDURE = "procedure", _("Procedure")
        AUTHORITY = "authority", _("Authority")
        REQUIREMENT = "requirement", _("Requirement")
        CASE_POLICY = "case_policy", _("Legacy case policy")

    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        UPDATED = "updated", _("Updated")
        ADOPTED = "adopted", _("Adopted")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_uuid = models.UUIDField()
    action = models.CharField(max_length=12, choices=Action.choices)
    before_snapshot = models.JSONField(default=dict)
    after_snapshot = models.JSONField(default=dict)
    reason = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_configuration_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            (
                "view_legalizationconfigurationevent",
                "Can view legalization configuration history",
            ),
        )
        indexes = (
            models.Index(
                fields=("entity_type", "entity_uuid", "occurred_at"),
                name="hydra_leg_config_event_idx",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Legalization configuration history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization configuration history is append-only.")


class LegalizationCaseDelegationQuerySet(models.QuerySet):
    REVOCATION_FIELDS = {
        "is_active",
        "revoked_at",
        "revoked_by",
        "revocation_reason",
        "modified_by",
    }

    def update(self, **kwargs):
        if set(kwargs) - self.REVOCATION_FIELDS:
            raise TypeError("Legalization delegation facts cannot be rewritten.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Legalization delegations cannot be deleted.")


class LegalizationCaseDelegation(HorillaModel):
    MAX_DURATION_DAYS = LEGALIZATION_DELEGATION_MAX_DURATION_DAYS

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    case = models.ForeignKey(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="delegations",
    )
    principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_delegations_given",
    )
    deputy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_delegations_received",
    )
    valid_from = models.DateField(default=timezone.localdate)
    valid_until = models.DateField()
    reason = models.CharField(max_length=255)
    revoked_at = models.DateTimeField(null=True, blank=True, editable=False)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_delegations_revoked",
        null=True,
        blank=True,
        editable=False,
    )
    revocation_reason = models.CharField(max_length=255, blank=True, editable=False)

    objects = LegalizationCaseDelegationQuerySet.as_manager()

    class Meta:
        ordering = ("-valid_from", "-pk")
        default_permissions = ("view",)
        permissions = (
            (
                "manage_legalizationdelegation",
                "Can manage legalization case delegations",
            ),
        )
        indexes = (
            models.Index(
                fields=("case", "is_active", "valid_from", "valid_until"),
                name="hydra_leg_deleg_case_idx",
            ),
            models.Index(
                fields=("deputy", "is_active", "valid_from", "valid_until"),
                name="hydra_leg_deleg_deputy_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=~models.Q(principal=models.F("deputy")),
                name="hydra_leg_deleg_distinct_users",
            ),
            models.CheckConstraint(
                check=models.Q(valid_until__gte=models.F("valid_from")),
                name="hydra_leg_deleg_valid_dates",
            ),
            models.CheckConstraint(
                check=models.Q(
                    valid_until__lte=models.F("valid_from")
                    + timedelta(
                        days=LEGALIZATION_DELEGATION_MAX_DURATION_DAYS - 1
                    )
                ),
                name="hydra_leg_deleg_bounded_dates",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        is_active=True,
                        revoked_at__isnull=True,
                        revoked_by__isnull=True,
                        revocation_reason="",
                    )
                    | (
                        models.Q(
                            is_active=False,
                            revoked_at__isnull=False,
                            revoked_by__isnull=False,
                        )
                        & ~models.Q(revocation_reason="")
                    )
                ),
                name="hydra_leg_deleg_revocation_shape",
            ),
            models.UniqueConstraint(
                fields=("case", "valid_from", "valid_until"),
                condition=models.Q(is_active=True),
                name="hydra_leg_deleg_exact_window_uniq",
            ),
        )

    CORE_FIELDS = (
        "case_id",
        "principal_id",
        "deputy_id",
        "valid_from",
        "valid_until",
        "reason",
        "created_by_id",
        "created_at",
    )

    def clean(self):
        super().clean()
        self.reason = " ".join(self.reason.split())
        self.revocation_reason = " ".join(self.revocation_reason.split())
        if not self.reason:
            raise ValidationError({"reason": _("A delegation reason is required.")})
        if self.principal_id and self.deputy_id and self.principal_id == self.deputy_id:
            raise ValidationError({"deputy": _("The responsible user cannot be their own deputy.")})
        if self.valid_from and self.valid_until:
            if self.valid_until < self.valid_from:
                raise ValidationError({"valid_until": _("The end date cannot precede the start date.")})
            if (self.valid_until - self.valid_from).days >= self.MAX_DURATION_DAYS:
                raise ValidationError(
                    {"valid_until": _("A delegation cannot exceed 90 calendar days.")}
                )

    def is_current(self, day=None):
        day = day or timezone.localdate()
        return (
            self.is_active
            and self.valid_from <= day <= self.valid_until
            and self.case.responsible_id == self.principal_id
        )

    @property
    def state_label(self):
        if not self.is_active:
            return _("Revoked")
        day = timezone.localdate()
        if self.valid_from > day:
            return _("Scheduled")
        if self.valid_until < day:
            return _("Ended")
        if self.case.responsible_id != self.principal_id:
            return _("Superseded")
        return _("Current")

    @property
    def can_revoke(self):
        return (
            self.is_active
            and self.valid_until >= timezone.localdate()
            and self.case.responsible_id == self.principal_id
        )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.values(*self.CORE_FIELDS).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.CORE_FIELDS):
                raise TypeError("Legalization delegation facts cannot be rewritten.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization delegations cannot be deleted.")

    def __str__(self):
        return f"{self.case} / {self.principal} -> {self.deputy}"


class LegalizationWorkEventQuerySet(models.QuerySet):
    DELIVERY_FIELDS = {
        "notification_status",
        "notification_attempts",
        "notification_last_attempt_at",
        "notification_error_code",
        "notification",
    }

    def update(self, **kwargs):
        if set(kwargs) - self.DELIVERY_FIELDS:
            raise TypeError("Legalization work events are append-only.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Legalization work events are append-only.")


class LegalizationWorkEvent(models.Model):
    class Action(models.TextChoices):
        RESPONSIBILITY_ASSIGNED = "responsibility_assigned", _("Responsibility assigned")
        RESPONSIBILITY_TRANSFERRED = (
            "responsibility_transferred",
            _("Responsibility transferred"),
        )
        DELEGATION_CREATED = "delegation_created", _("Delegation created")
        DELEGATION_REVOKED = "delegation_revoked", _("Delegation revoked")

    class NotificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    case = models.ForeignKey(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="work_events",
    )
    delegation = models.ForeignKey(
        LegalizationCaseDelegation,
        on_delete=models.PROTECT,
        related_name="work_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_work_events_from",
        null=True,
        blank=True,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_work_events_to",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_work_events_recorded",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.USER)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_work_events_received",
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=255)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    notification_attempts = models.PositiveSmallIntegerField(default=0)
    notification_last_attempt_at = models.DateTimeField(null=True, blank=True)
    notification_error_code = models.CharField(max_length=80, blank=True)
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.PROTECT,
        related_name="hydra_legalization_work_events",
        null=True,
        blank=True,
    )

    objects = LegalizationWorkEventQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_legalizationworkevent", "Can view legalization work events"),
        )
        indexes = (
            models.Index(
                fields=("case", "occurred_at"),
                name="hydra_leg_work_case_idx",
            ),
            models.Index(
                fields=("notification_status", "occurred_at"),
                name="hydra_leg_work_notify_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=~models.Q(reason=""),
                name="hydra_leg_work_reason_required",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(source="user", actor__isnull=False)
                    | models.Q(source="system", actor__isnull=True)
                ),
                name="hydra_leg_work_source_actor",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        action="responsibility_assigned",
                        delegation__isnull=True,
                        from_user__isnull=True,
                        effective_from__isnull=True,
                        effective_until__isnull=True,
                    )
                    | models.Q(
                        action="responsibility_transferred",
                        delegation__isnull=True,
                        from_user__isnull=False,
                        effective_from__isnull=True,
                        effective_until__isnull=True,
                    )
                    | models.Q(
                        action__in=("delegation_created", "delegation_revoked"),
                        delegation__isnull=False,
                        from_user__isnull=False,
                        effective_from__isnull=False,
                        effective_until__isnull=False,
                    )
                ),
                name="hydra_leg_work_action_shape",
            ),
            models.CheckConstraint(
                check=models.Q(from_user__isnull=True)
                | ~models.Q(from_user=models.F("to_user")),
                name="hydra_leg_work_distinct_users",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(recipient__isnull=False)
                    | models.Q(notification_status="not_applicable")
                ),
                name="hydra_leg_work_notify_target",
            ),
            models.CheckConstraint(
                check=~models.Q(notification_status="sent")
                | models.Q(notification__isnull=False),
                name="hydra_leg_work_sent_record",
            ),
            models.UniqueConstraint(
                fields=("case", "action"),
                condition=models.Q(action="responsibility_assigned"),
                name="hydra_leg_initial_owner_event_uniq",
            ),
            models.UniqueConstraint(
                fields=("delegation", "action"),
                condition=models.Q(delegation__isnull=False),
                name="hydra_leg_deleg_event_uniq",
            ),
        )

    CORE_FIELDS = (
        "case_id",
        "delegation_id",
        "action",
        "from_user_id",
        "to_user_id",
        "actor_id",
        "source",
        "recipient_id",
        "reason",
        "effective_from",
        "effective_until",
        "occurred_at",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.values(*self.CORE_FIELDS).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.CORE_FIELDS):
                raise TypeError("Legalization work events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization work events are append-only.")

    def __str__(self):
        return f"{self.case} / {self.get_action_display()}"


class LegalizationStatusHistory(models.Model):
    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

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
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.USER)
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
        constraints = (
            models.CheckConstraint(
                check=(
                    models.Q(source="user", actor__isnull=False)
                    | models.Q(source="system", actor__isnull=True)
                ),
                name="hydra_leg_history_source_actor",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Legalization history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization history is append-only.")


class LegalizationRenewalLink(models.Model):
    class Source(models.TextChoices):
        CREATED = "created", _("Created as renewal")
        MANUAL = "manual", _("Manual historical link")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    predecessor = models.OneToOneField(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="renewal_as_predecessor",
    )
    successor = models.OneToOneField(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="renewal_as_successor",
    )
    source = models.CharField(max_length=12, choices=Source.choices)
    reason = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_renewal_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("created_at", "pk")
        default_permissions = ("view",)
        permissions = (
            ("create_legalizationrenewallink", "Can create legalization renewal links"),
        )
        constraints = (
            models.CheckConstraint(
                check=~models.Q(predecessor=models.F("successor")),
                name="hydra_leg_renewal_distinct",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(source="created", reason="")
                    | (models.Q(source="manual") & ~models.Q(reason=""))
                ),
                name="hydra_leg_renewal_reason_shape",
            ),
        )

    def clean(self):
        super().clean()
        self.reason = " ".join(self.reason.split())
        if self.predecessor_id and self.successor_id:
            if self.predecessor_id == self.successor_id:
                raise ValidationError(_("A case cannot renew itself."))
            if self.predecessor.person_id != self.successor.person_id:
                raise ValidationError(_("Renewal cases must belong to the same person."))
            if self.predecessor.company_id != self.successor.company_id:
                raise ValidationError(_("Renewal cases must belong to the same company."))
            if self.predecessor.procedure_type_id != self.successor.procedure_type_id:
                raise ValidationError(_("Renewal cases must use the same procedure."))
            predecessor_order = (self.predecessor.created_at, self.predecessor.pk)
            successor_order = (self.successor.created_at, self.successor.pk)
            if (
                None not in predecessor_order + successor_order
                and predecessor_order >= successor_order
            ):
                raise ValidationError(_("The predecessor must be older than the successor."))
        if self.source == self.Source.CREATED and self.reason:
            raise ValidationError({"reason": _("Created renewals cannot have a backfill reason.")})
        if self.source == self.Source.MANUAL and not self.reason:
            raise ValidationError({"reason": _("A manual historical link requires a reason.")})

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Legalization renewal links are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization renewal links are append-only.")

    def __str__(self):
        return f"{self.predecessor} → {self.successor}"


class LegalizationAuthorityEvent(models.Model):
    class EventType(models.TextChoices):
        SUBMITTED = "submitted", _("Submitted to authority")
        REFERENCE_ASSIGNED = "reference_assigned", _("Reference assigned")
        INFORMATION_REQUESTED = "information_requested", _("Additional information requested")
        INFORMATION_RESPONDED = "information_responded", _("Additional information submitted")
        APPROVED = "approved", _("Decision approved")
        REJECTED = "rejected", _("Decision rejected")

    Channel = LegalizationAuthorityEventChannel

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    idempotency_key = models.UUIDField(default=uuid4, editable=False)
    case = models.ForeignKey(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="authority_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    occurred_on = models.DateField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    authority_config = models.ForeignKey(
        LegalizationAuthority,
        on_delete=models.PROTECT,
        related_name="events",
    )
    authority = models.CharField(max_length=200)
    authority_snapshot = models.JSONField(default=dict, editable=False)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    reference_number = models.CharField(max_length=100, blank=True)
    response_deadline = models.DateField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    evidence_document = models.ForeignKey(
        PrivateDocument,
        on_delete=models.PROTECT,
        related_name="legalization_authority_events",
    )
    evidence_sha256 = models.CharField(max_length=64, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legalization_authority_events",
    )
    details = models.TextField(blank=True, max_length=1000)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_on", "-recorded_at", "-pk")
        default_permissions = ("view",)
        permissions = (
            ("record_legalizationauthorityevent", "Can record legalization authority events"),
        )
        indexes = (
            models.Index(
                fields=("case", "occurred_on", "recorded_at"),
                name="hydra_leg_authority_case_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("case", "idempotency_key"),
                name="hydra_leg_authority_idem_uniq",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        event_type="information_requested",
                        response_deadline__isnull=False,
                    )
                    | (
                        ~models.Q(event_type="information_requested")
                        & models.Q(response_deadline__isnull=True)
                    )
                ),
                name="hydra_leg_authority_deadline_shape",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        event_type="approved",
                        valid_from__isnull=False,
                        valid_until__isnull=False,
                    )
                    | (
                        ~models.Q(event_type="approved")
                        & models.Q(valid_from__isnull=True, valid_until__isnull=True)
                    )
                ),
                name="hydra_leg_authority_validity_shape",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(event_type="reference_assigned")
                    | ~models.Q(reference_number="")
                ),
                name="hydra_leg_authority_reference",
            ),
        )

    CORE_FIELDS = (
        "idempotency_key",
        "case_id",
        "event_type",
        "occurred_on",
        "recorded_at",
        "authority_config_id",
        "authority",
        "authority_snapshot",
        "channel",
        "reference_number",
        "response_deadline",
        "valid_from",
        "valid_until",
        "evidence_document_id",
        "evidence_sha256",
        "actor_id",
        "details",
    )

    def clean(self):
        super().clean()
        self.authority = " ".join(self.authority.split())
        self.reference_number = " ".join(self.reference_number.split())
        self.details = self.details.strip()
        if not self.authority:
            raise ValidationError({"authority": _("Authority is required.")})
        snapshot = self.authority_snapshot
        if (
            not isinstance(snapshot, dict)
            or snapshot.get("uuid") != str(self.authority_config.uuid)
            or snapshot.get("name") != self.authority
        ):
            raise ValidationError(
                {"authority_config": _("A matching immutable authority snapshot is required.")}
            )
        if self.channel not in snapshot.get("allowed_channels", []):
            raise ValidationError(
                {"channel": _("This channel is not allowed for the selected authority.")}
            )
        if self.occurred_on and self.occurred_on > timezone.localdate():
            raise ValidationError({"occurred_on": _("An authority event cannot be in the future.")})
        if self.event_type == self.EventType.INFORMATION_REQUESTED:
            if not self.response_deadline:
                raise ValidationError(
                    {"response_deadline": _("An information request requires a response deadline.")}
                )
            if self.occurred_on and self.response_deadline < self.occurred_on:
                raise ValidationError(
                    {"response_deadline": _("The response deadline cannot precede the request.")}
                )
        elif self.response_deadline:
            raise ValidationError(
                {"response_deadline": _("A response deadline is only valid for an information request.")}
            )
        if self.event_type == self.EventType.APPROVED:
            if not (self.valid_from and self.valid_until):
                raise ValidationError(
                    {"valid_until": _("An approval requires a complete validity period.")}
                )
            if self.valid_until < self.valid_from:
                raise ValidationError(
                    {"valid_until": _("Valid until cannot be earlier than valid from.")}
                )
        elif self.valid_from or self.valid_until:
            raise ValidationError(
                {"valid_until": _("Validity dates are only valid for an approval.")}
            )
        if self.event_type == self.EventType.REFERENCE_ASSIGNED and not self.reference_number:
            raise ValidationError(
                {"reference_number": _("A reference assignment requires a reference number.")}
            )
        if self.event_type == self.EventType.REJECTED and not self.details:
            raise ValidationError({"details": _("A rejection requires details.")})

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Legalization authority events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization authority events are append-only.")

    def __str__(self):
        return f"{self.case} — {self.get_event_type_display()}"


class LegalizationAutomationEventQuerySet(models.QuerySet):
    DELIVERY_FIELDS = {
        "notification_status",
        "notification_attempts",
        "notification_last_attempt_at",
        "notification_error_code",
        "notification",
    }

    def update(self, **kwargs):
        if set(kwargs) - self.DELIVERY_FIELDS:
            raise TypeError("Legalization automation event facts are append-only.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Legalization automation events are append-only.")


class LegalizationAutomationEvent(models.Model):
    class EventType(models.TextChoices):
        DEADLINE_REMINDER = "deadline_reminder", _("Deadline reminder")
        DEADLINE_OVERDUE = "deadline_overdue", _("Deadline overdue")
        VALIDITY_REMINDER = "validity_reminder", _("Validity reminder")
        AUTO_EXPIRED = "auto_expired", _("Automatically expired")

    class NotificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    case = models.ForeignKey(
        LegalizationCase,
        on_delete=models.PROTECT,
        related_name="automation_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    due_date = models.DateField()
    threshold_days = models.PositiveSmallIntegerField(default=0)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_legalization_automation_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    notification_attempts = models.PositiveSmallIntegerField(default=0)
    notification_last_attempt_at = models.DateTimeField(null=True, blank=True)
    notification_error_code = models.CharField(max_length=80, blank=True)
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.PROTECT,
        related_name="hydra_legalization_automation_events",
        null=True,
        blank=True,
    )

    objects = LegalizationAutomationEventQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            (
                "view_legalizationautomationevent",
                "Can view legalization automation events",
            ),
        )
        indexes = (
            models.Index(
                fields=("notification_status", "occurred_at"),
                name="hydra_leg_auto_notify_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "case",
                    "event_type",
                    "due_date",
                    "threshold_days",
                    "recipient",
                ),
                name="hydra_leg_auto_event_uniq",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        event_type__in=("deadline_reminder", "validity_reminder"),
                        threshold_days__gt=0,
                    )
                    | models.Q(
                        event_type__in=("deadline_overdue", "auto_expired"),
                        threshold_days=0,
                    )
                ),
                name="hydra_leg_auto_threshold",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(notification_status="sent")
                    | models.Q(notification__isnull=False)
                ),
                name="hydra_leg_auto_sent_record",
            ),
        )

    CORE_FIELDS = (
        "case_id",
        "event_type",
        "due_date",
        "threshold_days",
        "recipient_id",
        "occurred_at",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.values(*self.CORE_FIELDS).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.CORE_FIELDS):
                raise TypeError("Legalization automation event facts are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Legalization automation events are append-only.")


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
