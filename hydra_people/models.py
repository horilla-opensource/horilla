from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from hydra.models import HydraModel
from recruitment.models import Candidate, Recruitment, Stage


phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ()-]{7,25}$",
    message=_("Enter a valid phone number."),
)
citizenship_validator = RegexValidator(
    regex=r"^[A-Za-z]{2}$",
    message=_("Use a two-letter ISO country code, for example UA or PL."),
)


class Person(HydraModel):
    class Gender(models.TextChoices):
        FEMALE = "female", _("Female")
        MALE = "male", _("Male")
        OTHER = "other", _("Other")
        UNSPECIFIED = "unspecified", _("Unspecified")

    class PreferredLanguage(models.TextChoices):
        POLISH = "pl", _("Polish")
        RUSSIAN = "ru", _("Russian")
        UKRAINIAN = "uk", _("Ukrainian")
        ENGLISH = "en", _("English")
        AZERBAIJANI = "az", _("Azerbaijani")
        SPANISH = "es", _("Spanish")
        FILIPINO = "fil", _("Filipino")
        INDONESIAN = "id", _("Indonesian")
        NEPALI = "ne", _("Nepali")

    class LifecycleState(models.TextChoices):
        PROSPECT = "prospect", _("Prospect")
        CANDIDATE = "candidate", _("Candidate")
        ONBOARDING = "onboarding", _("Onboarding")
        EMPLOYEE = "employee", _("Employee")
        INACTIVE = "inactive", _("Inactive")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    hydra_id = models.CharField(max_length=24, unique=True, editable=False)
    identity_fingerprint = models.CharField(
        max_length=64, blank=True, default="", db_index=True, editable=False
    )
    passport_dob_fingerprint = models.CharField(
        max_length=64, blank=True, default="", db_index=True, editable=False
    )
    email_fingerprint = models.CharField(
        max_length=64, blank=True, default="", db_index=True, editable=False
    )
    phone_fingerprint = models.CharField(
        max_length=64, blank=True, default="", db_index=True, editable=False
    )
    messenger_fingerprint = models.CharField(
        max_length=64, blank=True, default="", db_index=True, editable=False
    )
    passport_name = models.CharField(max_length=255, verbose_name=_("Passport name"))
    first_name = models.CharField(max_length=100, verbose_name=_("First name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last name"))
    date_of_birth = models.DateField(verbose_name=_("Date of birth"))
    gender = models.CharField(
        max_length=16,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
        verbose_name=_("Gender"),
    )
    citizenship = models.CharField(
        max_length=2,
        validators=[citizenship_validator],
        verbose_name=_("Citizenship"),
        help_text=_("Two-letter ISO country code."),
    )
    preferred_language = models.CharField(
        max_length=3,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.POLISH,
        verbose_name=_("Preferred language"),
    )
    phone = models.CharField(
        max_length=25,
        blank=True,
        validators=[phone_validator],
        verbose_name=_("Phone"),
    )
    whatsapp_viber = models.CharField(
        max_length=25,
        blank=True,
        validators=[phone_validator],
        verbose_name=_("WhatsApp / Viber"),
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    lifecycle_state = models.CharField(
        max_length=16,
        choices=LifecycleState.choices,
        default=LifecycleState.PROSPECT,
        verbose_name=_("Lifecycle state"),
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hydra_person",
        verbose_name=_("Employee"),
    )
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="merged_sources",
        editable=False,
        verbose_name=_("Canonical Person"),
    )
    merged_at = models.DateTimeField(null=True, blank=True, editable=False)
    merged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hydra_person_merges_applied",
        editable=False,
    )

    class Meta:
        ordering = ("passport_name", "hydra_id")
        verbose_name = _("Hydra person")
        verbose_name_plural = _("Hydra people")
        permissions = (
            ("link_candidate", "Can link recruitment applications to Hydra person"),
            (
                "review_person_duplicates",
                "Can review Hydra Person duplicate suggestions",
            ),
            ("dismiss_person_duplicate", "Can dismiss Person duplicate suggestions"),
            ("merge_person", "Can merge duplicate Hydra Person records"),
            (
                "convert_person_to_employee",
                "Can convert Hydra person to Hydra employee",
            ),
        )
        indexes = (
            models.Index(fields=("last_name", "first_name"), name="hydra_person_name_idx"),
            models.Index(fields=("date_of_birth", "citizenship"), name="hydra_person_identity_idx"),
        )
        constraints = (
            models.CheckConstraint(
                check=(
                    models.Q(
                        merged_into__isnull=True,
                        merged_at__isnull=True,
                        merged_by__isnull=True,
                    )
                    | models.Q(
                        merged_into__isnull=False,
                        merged_at__isnull=False,
                        merged_by__isnull=False,
                        is_active=False,
                        lifecycle_state="inactive",
                    )
                ),
                name="hyd_person_merge_shape",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(merged_into__isnull=True)
                    | ~models.Q(merged_into_id=models.F("pk"))
                ),
                name="hyd_person_not_self_merge",
            ),
        )

    def __str__(self):
        return f"{self.hydra_id} — {self.passport_name}"

    def clean(self):
        super().clean()
        for field_name in ("passport_name", "first_name", "last_name"):
            value = getattr(self, field_name, "")
            setattr(self, field_name, " ".join(value.split()))
        self.citizenship = self.citizenship.strip().upper()
        self.email = self.email.strip().lower()
        self.phone = self.phone.strip()
        self.whatsapp_viber = self.whatsapp_viber.strip()

    def save(self, *args, **kwargs):
        if self.pk and self.merged_into_id and not kwargs.pop("merge_transition", False):
            raise TypeError("A merged Person alias is immutable.")
        if not self.hydra_id:
            self.hydra_id = f"HYD-{self.uuid.hex[:16].upper()}"
        from hydra_people.identity import populate_person_fingerprints

        populate_person_fingerprints(self)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = tuple(
                dict.fromkeys(
                    tuple(kwargs["update_fields"])
                    + (
                        "identity_fingerprint",
                        "passport_dob_fingerprint",
                        "email_fingerprint",
                        "phone_fingerprint",
                        "messenger_fingerprint",
                    )
                )
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("hydra-person-detail", kwargs={"person_uuid": self.uuid})


class PersonDuplicateSuggestion(HydraModel):
    class State(models.TextChoices):
        OPEN = "open", _("Open")
        DISMISSED = "dismissed", _("Dismissed")
        STALE = "stale", _("No longer matches")
        MERGED = "merged", _("Merged")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person_low = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="duplicate_suggestions_as_low",
    )
    person_high = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="duplicate_suggestions_as_high",
    )
    score = models.PositiveSmallIntegerField()
    match_reasons = models.JSONField(default=list)
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.OPEN,
    )
    last_evaluated_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hydra_duplicate_suggestions_resolved",
    )
    resolution_reason = models.CharField(max_length=500, blank=True)
    merge_event = models.OneToOneField(
        "PersonMergeEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="suggestion",
    )

    class Meta:
        ordering = ("-score", "created_at", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("person_low", "person_high"),
                name="hyd_person_dup_pair_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(person_low_id__lt=models.F("person_high_id")),
                name="hyd_person_dup_pair_order",
            ),
            models.CheckConstraint(
                check=models.Q(score__gte=1, score__lte=100),
                name="hyd_person_dup_score_range",
            ),
        )

    def __str__(self):
        return f"{self.person_low.hydra_id} / {self.person_high.hydra_id}"


class AppendOnlyPersonMergeQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Person merge evidence is append-only.")

    def delete(self):
        raise TypeError("Person merge evidence is append-only.")


class PersonMergeEvent(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    survivor = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="merge_events_as_survivor",
    )
    duplicate = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="merge_event_as_duplicate",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_person_merge_events",
    )
    reason = models.CharField(max_length=500)
    match_reasons = models.JSONField()
    field_decisions = models.JSONField()
    moved_reference_counts = models.JSONField()
    preserved_source_identifiers = models.JSONField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyPersonMergeQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_personmergeevent", "Can view Person merge evidence"),
        )
        indexes = (
            models.Index(
                fields=("survivor", "occurred_at"),
                name="hyd_person_merge_time_idx",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Person merge evidence is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Person merge evidence is append-only.")


class PersonMergeReference(models.Model):
    event = models.ForeignKey(
        PersonMergeEvent,
        on_delete=models.PROTECT,
        related_name="moved_references",
    )
    relation_kind = models.CharField(max_length=40)
    object_id = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyPersonMergeQuerySet.as_manager()

    class Meta:
        ordering = ("relation_kind", "object_id", "pk")
        default_permissions = ()
        constraints = (
            models.UniqueConstraint(
                fields=("event", "relation_kind", "object_id"),
                name="hyd_person_merge_ref_uniq",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Person merge references are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Person merge references are append-only.")


class AppendOnlyConversionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Employee conversion history is append-only.")

    def delete(self):
        raise TypeError("Employee conversion history is append-only.")


class EmployeeConversion(models.Model):
    class Source(models.TextChoices):
        HYDRA_OPERATOR = "hydra_operator", _("Hydra operator")
        HYDRA_ONBOARDING = "hydra_onboarding", _("Hydra onboarding")

    person = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="employee_conversion",
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_employee_conversion",
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.PROTECT,
        related_name="hydra_conversion",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_employee_conversions",
    )
    source = models.CharField(max_length=24, choices=Source.choices)
    source_snapshot = models.JSONField()
    field_decisions = models.JSONField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyConversionQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_employeeconversion", "Can view employee conversion history"),
        )
        indexes = (
            models.Index(fields=("occurred_at",), name="hyd_people_conv_time_idx"),
        )

    def __str__(self):
        return f"{self.person.hydra_id} -> {self.employee}"

    def clean(self):
        super().clean()
        if self.person_id and self.employee_id:
            if self.person.employee_id != self.employee_id:
                raise ValidationError(
                    {"employee": _("The employee must be linked to this Person.")}
                )
        if self.candidate_id and self.person_id:
            try:
                linked_person_id = self.candidate.hydra_person_link.person_id
            except PersonApplication.DoesNotExist as error:
                raise ValidationError(
                    {"candidate": _("The application must be linked to a Person.")}
                ) from error
            if linked_person_id != self.person_id:
                raise ValidationError(
                    {"candidate": _("The application belongs to another Person.")}
                )
        if self.candidate_id and self.employee_id:
            if self.candidate.converted_employee_id_id != self.employee_id:
                raise ValidationError(
                    {"candidate": _("The application must reference this employee.")}
                )
        if not self.source_snapshot or not self.field_decisions:
            raise ValidationError(_("Conversion audit data cannot be empty."))

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Employee conversion history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Employee conversion history is append-only.")


class RecruitmentStageTransitionRule(HydraModel):
    """Configurable contract for one directed recruitment-stage transition."""

    recruitment = models.ForeignKey(
        Recruitment,
        on_delete=models.PROTECT,
        related_name="hydra_transition_rules",
    )
    from_stage = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        related_name="hydra_transition_rules_from",
    )
    to_stage = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        related_name="hydra_transition_rules_to",
    )
    requires_reason = models.BooleanField(default=False)
    requires_schedule_date = models.BooleanField(default=False)
    requires_joining_date = models.BooleanField(default=False)
    allow_override = models.BooleanField(default=True)

    class Meta:
        ordering = ("recruitment_id", "from_stage__sequence", "to_stage__sequence")
        constraints = (
            models.UniqueConstraint(
                fields=("recruitment", "from_stage", "to_stage"),
                name="hyd_people_rule_pair_uniq",
            ),
        )
        permissions = (
            (
                "override_recruitment_transition",
                "Can override recruitment transition requirements",
            ),
        )

    def __str__(self):
        return f"{self.from_stage} -> {self.to_stage}"

    def clean(self):
        super().clean()
        errors = {}
        if self.from_stage_id and self.to_stage_id:
            if self.from_stage_id == self.to_stage_id:
                errors["to_stage"] = _("A transition must change the stage.")
            if self.recruitment_id:
                if self.from_stage.recruitment_id_id != self.recruitment_id:
                    errors["from_stage"] = _(
                        "The source stage must belong to this recruitment."
                    )
                if self.to_stage.recruitment_id_id != self.recruitment_id:
                    errors["to_stage"] = _(
                        "The target stage must belong to this recruitment."
                    )
        if errors:
            raise ValidationError(errors)


class AppendOnlyStageTransitionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Candidate stage transition history is append-only.")

    def delete(self):
        raise TypeError("Candidate stage transition history is append-only.")


class CandidateStageTransition(models.Model):
    """Immutable evidence emitted by the controlled transition service."""

    class Source(models.TextChoices):
        HYDRA = "hydra", _("Hydra")
        HYDRA_PIPELINE = "hydra_pipeline", _("Hydra pipeline")

    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_stage_transitions",
    )
    from_stage = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        related_name="hydra_candidate_transitions_from",
    )
    to_stage = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        related_name="hydra_candidate_transitions_to",
    )
    rule = models.ForeignKey(
        RecruitmentStageTransitionRule,
        on_delete=models.PROTECT,
        related_name="transition_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_candidate_stage_transitions",
    )
    source = models.CharField(max_length=24, choices=Source.choices)
    reason = models.TextField(blank=True)
    override = models.BooleanField(default=False)
    requirements_snapshot = models.JSONField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyStageTransitionQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ("view",)
        indexes = (
            models.Index(
                fields=("candidate", "occurred_at"),
                name="hyd_people_trans_time_idx",
            ),
        )

    def __str__(self):
        return f"{self.candidate}: {self.from_stage} -> {self.to_stage}"

    def clean(self):
        super().clean()
        errors = {}
        if self.from_stage_id and self.to_stage_id:
            if self.from_stage_id == self.to_stage_id:
                errors["to_stage"] = _("A transition must change the stage.")
            if self.candidate_id:
                recruitment_id = self.candidate.recruitment_id_id
                if self.from_stage.recruitment_id_id != recruitment_id:
                    errors["from_stage"] = _(
                        "The source stage must belong to the application recruitment."
                    )
                if self.to_stage.recruitment_id_id != recruitment_id:
                    errors["to_stage"] = _(
                        "The target stage must belong to the application recruitment."
                    )
        if self.rule_id and self.from_stage_id and self.to_stage_id:
            if (
                self.rule.from_stage_id != self.from_stage_id
                or self.rule.to_stage_id != self.to_stage_id
            ):
                errors["rule"] = _("The rule must match the recorded transition.")
        if self.override and not self.reason.strip():
            errors["reason"] = _("An override requires a reason.")
        if not self.requirements_snapshot:
            errors["requirements_snapshot"] = _(
                "The transition requirements snapshot cannot be empty."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Candidate stage transition history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Candidate stage transition history is append-only.")


class PersonApplication(HydraModel):
    class LinkSource(models.TextChoices):
        MANUAL = "manual", _("Manual link")
        HYDRA_INTAKE = "hydra_intake", _("Hydra intake")
        BACKFILL = "backfill", _("Backfill")

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name=_("Person"),
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_person_link",
        verbose_name=_("Candidate application"),
    )
    link_source = models.CharField(
        max_length=16,
        choices=LinkSource.choices,
        default=LinkSource.MANUAL,
        verbose_name=_("Link source"),
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = _("Person application link")
        verbose_name_plural = _("Person application links")

    def __str__(self):
        return f"{self.person.hydra_id} ↔ {self.candidate}"
