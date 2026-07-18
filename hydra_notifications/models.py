from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra_people.models import Person


class NotificationKind(models.TextChoices):
    LEGACY = "legacy", _("Hydra notification")
    ORGANIZATION_SCOPE_END = "organization_scope_end", _("Scope end scheduled")
    ORGANIZATION_SCOPE_REVOKED = "organization_scope_revoked", _("Scope revoked")
    ORGANIZATION_ASSIGNMENT_END = (
        "organization_assignment_end",
        _("Assignment end scheduled"),
    )
    ORGANIZATION_ASSIGNMENT_ENDED = (
        "organization_assignment_ended",
        _("Assignment ended"),
    )
    ARRIVAL_UPCOMING = "arrival_upcoming", _("Arrival approaching")
    ARRIVAL_OVERDUE = "arrival_overdue", _("Arrival overdue")
    LEGALIZATION_DEADLINE = "legalization_deadline", _("Legalization deadline")
    LEGALIZATION_OVERDUE = "legalization_overdue", _("Legalization overdue")
    LEGALIZATION_VALIDITY = "legalization_validity", _("Validity ending")
    LEGALIZATION_EXPIRED = "legalization_expired", _("Legalization expired")
    LEGALIZATION_ASSIGNED = "legalization_assigned", _("Responsibility assigned")
    LEGALIZATION_TRANSFERRED = (
        "legalization_transferred",
        _("Responsibility transferred"),
    )
    LEGALIZATION_DEPUTY = "legalization_deputy", _("Deputy appointed")
    LEGALIZATION_DEPUTY_REVOKED = (
        "legalization_deputy_revoked",
        _("Deputy appointment revoked"),
    )
    TASK_ASSIGNED = "task_assigned", _("Task assigned")
    TASK_UPDATED = "task_updated", _("Task updated")
    TASK_REASSIGNED = "task_reassigned", _("Task reassigned")
    TASK_STATUS_CHANGED = "task_status_changed", _("Task status changed")
    TASK_COMPLETED = "task_completed", _("Task completed")
    TASK_CANCELLED = "task_cancelled", _("Task cancelled")
    TASK_REOPENED = "task_reopened", _("Task reopened")
    ONBOARDING_READY = "onboarding_ready", _("Onboarding ready")
    ONBOARDING_TASK_CHANGED = (
        "onboarding_task_changed",
        _("Onboarding task changed"),
    )


class NotificationCategory(models.TextChoices):
    LEGACY = "legacy", _("Hydra")
    ORGANIZATION = "organization", _("Organization")
    ARRIVALS = "arrivals", _("Arrivals")
    LEGALIZATION = "legalization", _("Legalization")
    TASKS = "tasks", _("Tasks")
    ONBOARDING = "onboarding", _("Onboarding")


class NotificationSeverity(models.TextChoices):
    INFO = "info", _("Information")
    SUCCESS = "success", _("Success")
    WARNING = "warning", _("Warning")
    ERROR = "error", _("Urgent")


class NotificationTargetKind(models.TextChoices):
    GENERAL = "general", _("General")
    ORGANIZATION = "organization", _("Organization")
    PERSON = "person", _("Person")
    LEGALIZATION_CASE = "legalization_case", _("Legalization case")
    ARRIVAL_PLAN = "arrival_plan", _("Arrival plan")
    ONBOARDING_HANDOFF = "onboarding_handoff", _("Onboarding handoff")
    HYDRA_TASK = "hydra_task", _("Hydra task")


class EnvelopeQuerySet(models.QuerySet):
    MUTABLE_FIELDS = {"read_at", "archived_at", "version"}

    def update(self, **kwargs):
        if not set(kwargs).issubset(self.MUTABLE_FIELDS):
            raise TypeError("Hydra notification identity is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Hydra notification envelopes are durable evidence.")


class HydraNotificationEnvelope(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=180, unique=True, editable=False)
    notification = models.OneToOneField(
        "notifications.Notification",
        on_delete=models.PROTECT,
        related_name="hydra_envelope",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_notification_envelopes",
    )
    kind = models.CharField(max_length=48, choices=NotificationKind.choices)
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    severity = models.CharField(max_length=12, choices=NotificationSeverity.choices)
    target_kind = models.CharField(
        max_length=24,
        choices=NotificationTargetKind.choices,
        default=NotificationTargetKind.GENERAL,
    )
    target_uuid = models.UUIDField(null=True, blank=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_notification_envelopes",
        null=True,
        blank=True,
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="hydra_notification_envelopes",
        null=True,
        blank=True,
    )
    redirect_path = models.CharField(max_length=500, blank=True, editable=False)
    occurred_at = models.DateTimeField(db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True, editable=False)
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        editable=False,
    )
    version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EnvelopeQuerySet.as_manager()

    IMMUTABLE_FIELDS = (
        "uuid",
        "idempotency_key",
        "notification_id",
        "recipient_id",
        "kind",
        "category",
        "severity",
        "target_kind",
        "target_uuid",
        "company_id",
        "person_id",
        "redirect_path",
        "occurred_at",
        "created_at",
    )
    SERVICE_FIELDS = ("read_at", "archived_at", "version")

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ("view",)
        indexes = (
            models.Index(
                fields=("recipient", "archived_at", "read_at", "occurred_at"),
                name="hyd_not_rec_state_time_idx",
            ),
            models.Index(
                fields=("target_kind", "target_uuid"),
                name="hyd_not_target_idx",
            ),
            models.Index(
                fields=("recipient", "category", "severity"),
                name="hyd_not_rec_cat_sev_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=Q(version__gte=1),
                name="hyd_not_version_positive",
            ),
            models.CheckConstraint(
                check=~Q(idempotency_key=""),
                name="hyd_not_idempotency_nonempty",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        target_kind__in=("general", "organization"),
                        target_uuid__isnull=True,
                    )
                    | Q(
                        target_kind__in=(
                            "person",
                            "legalization_case",
                            "arrival_plan",
                            "onboarding_handoff",
                            "hydra_task",
                        ),
                        target_uuid__isnull=False,
                    )
                ),
                name="hyd_not_target_shape",
            ),
        )

    def __str__(self):
        return f"{self.recipient_id}:{self.kind}:{self.uuid}"

    def clean(self):
        super().clean()
        self.idempotency_key = self.idempotency_key.strip()
        self.redirect_path = self.redirect_path.strip()
        if self.redirect_path and (
            not self.redirect_path.startswith("/")
            or self.redirect_path.startswith("//")
            or any(ord(character) < 32 for character in self.redirect_path)
        ):
            raise ValidationError(
                {"redirect_path": _("Notification redirects must be safe local paths.")}
            )

    def save(self, *args, **kwargs):
        service_update = kwargs.pop("service_update", False)
        if self.pk:
            original = type(self)._base_manager.values(
                *(self.IMMUTABLE_FIELDS + self.SERVICE_FIELDS)
            ).get(pk=self.pk)
            if any(
                original[field] != getattr(self, field)
                for field in self.IMMUTABLE_FIELDS
            ):
                raise TypeError("Hydra notification identity is immutable.")
            if not service_update and any(
                original[field] != getattr(self, field)
                for field in self.SERVICE_FIELDS
            ):
                raise TypeError(
                    "Hydra notification state must be changed through services."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra notification envelopes are durable evidence.")


class AppendOnlyNotificationEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Hydra notification state events are append-only.")

    def delete(self):
        raise TypeError("Hydra notification state events are append-only.")


class HydraNotificationStateEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        IMPORTED = "imported", _("Imported from Hydra")
        READ = "read", _("Marked as read")
        UNREAD = "unread", _("Marked as unread")
        OPENED = "opened", _("Opened")
        ARCHIVED = "archived", _("Archived")
        RESTORED = "restored", _("Restored")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    envelope = models.ForeignKey(
        HydraNotificationEnvelope,
        on_delete=models.PROTECT,
        related_name="state_events",
    )
    sequence = models.PositiveIntegerField()
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_notification_state_events",
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyNotificationEventQuerySet.as_manager()

    class Meta:
        ordering = ("sequence", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("envelope", "sequence"),
                name="hyd_not_event_sequence_uniq",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_not_event_sequence_positive",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Hydra notification state events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra notification state events are append-only.")


class NotificationPreferenceQuerySet(models.QuerySet):
    MUTABLE_FIELDS = {
        "email_enabled",
        "email_min_severity",
        "browser_sound_enabled",
        "version",
        "modified_at",
        "modified_by",
        "modified_by_id",
    }

    def update(self, **kwargs):
        if not set(kwargs).issubset(self.MUTABLE_FIELDS):
            raise TypeError("Hydra notification preference identity is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Hydra notification preferences cannot be hard-deleted.")


class HydraNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_notification_preference",
    )
    email_enabled = models.BooleanField(default=False)
    email_min_severity = models.CharField(
        max_length=12,
        choices=NotificationSeverity.choices,
        default=NotificationSeverity.WARNING,
    )
    browser_sound_enabled = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modified_hydra_notification_preferences",
        null=True,
        blank=True,
        editable=False,
    )

    objects = NotificationPreferenceQuerySet.as_manager()

    class Meta:
        default_permissions = ()
        constraints = (
            models.CheckConstraint(
                check=Q(version__gte=1),
                name="hyd_not_pref_version_positive",
            ),
        )

    def save(self, *args, **kwargs):
        service_update = kwargs.pop("service_update", False)
        if self.pk and not service_update:
            original = type(self)._base_manager.values(
                "user_id",
                "email_enabled",
                "email_min_severity",
                "browser_sound_enabled",
                "version",
                "modified_by_id",
            ).get(pk=self.pk)
            if original["user_id"] != self.user_id:
                raise TypeError("Hydra notification preference identity is immutable.")
            if any(
                original[field] != getattr(self, field)
                for field in (
                    "email_enabled",
                    "email_min_severity",
                    "browser_sound_enabled",
                    "version",
                    "modified_by_id",
                )
            ):
                raise TypeError(
                    "Hydra notification preferences must be changed through services."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra notification preferences cannot be hard-deleted.")


class EmailDeliveryQuerySet(models.QuerySet):
    MUTABLE_FIELDS = {
        "status",
        "attempts",
        "next_attempt_at",
        "lease_expires_at",
        "last_attempt_at",
        "sent_at",
        "error_code",
    }

    def update(self, **kwargs):
        if not set(kwargs).issubset(self.MUTABLE_FIELDS):
            raise TypeError("Hydra notification email-delivery identity is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Hydra notification email deliveries are durable evidence.")


class HydraNotificationEmailDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENDING = "sending", _("Sending")
        FAILED = "failed", _("Waiting for retry")
        SENT = "sent", _("Sent")
        DEAD = "dead", _("Retries exhausted")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    envelope = models.OneToOneField(
        HydraNotificationEnvelope,
        on_delete=models.PROTECT,
        related_name="email_delivery",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_notification_email_deliveries",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EmailDeliveryQuerySet.as_manager()

    IMMUTABLE_FIELDS = ("uuid", "envelope_id", "recipient_id", "created_at")

    class Meta:
        ordering = ("created_at", "pk")
        default_permissions = ("view",)
        indexes = (
            models.Index(
                fields=("status", "next_attempt_at", "created_at"),
                name="hyd_not_email_queue_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=(
                    Q(
                        status="pending",
                        attempts=0,
                        lease_expires_at__isnull=True,
                        sent_at__isnull=True,
                    )
                    | Q(
                        status="sending",
                        attempts__gte=1,
                        lease_expires_at__isnull=False,
                        sent_at__isnull=True,
                    )
                    | Q(
                        status="failed",
                        attempts__gte=1,
                        lease_expires_at__isnull=True,
                        next_attempt_at__isnull=False,
                        sent_at__isnull=True,
                    )
                    | Q(
                        status="sent",
                        attempts__gte=1,
                        lease_expires_at__isnull=True,
                        sent_at__isnull=False,
                    )
                    | Q(
                        status__in=("dead", "not_applicable"),
                        lease_expires_at__isnull=True,
                        sent_at__isnull=True,
                    )
                ),
                name="hyd_not_email_state_shape",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self)._base_manager.values(*self.IMMUTABLE_FIELDS).get(
                pk=self.pk
            )
            if any(
                original[field] != getattr(self, field)
                for field in self.IMMUTABLE_FIELDS
            ):
                raise TypeError("Hydra notification email-delivery identity is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra notification email deliveries are durable evidence.")
