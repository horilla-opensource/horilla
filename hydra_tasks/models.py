from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra.models import HydraModel
from hydra_people.models import Person


class TaskTargetKind(models.TextChoices):
    PERSON = "person", _("Person")
    LEGALIZATION_CASE = "legalization_case", _("Legalization case")
    ARRIVAL_PLAN = "arrival_plan", _("Arrival plan")
    HOUSING_ASSIGNMENT = "housing_assignment", _("Housing assignment")
    ONBOARDING_HANDOFF = "onboarding_handoff", _("Onboarding handoff")


class ProtectedTaskQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Hydra tasks must be changed through the task services.")

    def delete(self):
        raise TypeError("Hydra tasks cannot be hard-deleted.")


class HydraTask(HydraModel):
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        NORMAL = "normal", _("Normal")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    request_key = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_tasks",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="hydra_tasks",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_hydra_tasks",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True, max_length=2000)
    priority = models.CharField(
        max_length=12,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        editable=False,
    )
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    cancelled_at = models.DateTimeField(null=True, blank=True, editable=False)
    resolution_reason = models.CharField(
        max_length=500,
        blank=True,
        editable=False,
    )
    target_kind = models.CharField(
        max_length=32,
        choices=TaskTargetKind.choices,
        default=TaskTargetKind.PERSON,
        editable=False,
    )
    target_uuid = models.UUIDField(editable=False)
    target_label = models.CharField(max_length=255, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)

    objects = ProtectedTaskQuerySet.as_manager()

    IMMUTABLE_FIELDS = (
        "uuid",
        "request_key",
        "company_id",
        "person_id",
        "target_kind",
        "target_uuid",
        "target_label",
        "is_active",
        "created_by_id",
        "created_at",
    )
    SERVICE_FIELDS = (
        "assignee_id",
        "title",
        "description",
        "priority",
        "status",
        "due_at",
        "completed_at",
        "cancelled_at",
        "resolution_reason",
        "version",
        "modified_by_id",
    )

    class Meta:
        ordering = ("status", "due_at", "-created_at", "pk")
        default_permissions = ("add", "change", "view")
        permissions = (
            ("assign_hydratask", "Can assign Hydra tasks"),
            ("transition_hydratask", "Can transition Hydra tasks"),
            ("reopen_hydratask", "Can reopen completed or cancelled Hydra tasks"),
            ("view_all_hydratask", "Can view all Hydra tasks in current scope"),
        )
        indexes = (
            models.Index(
                fields=("company", "status", "due_at"),
                name="hyd_task_company_state_idx",
            ),
            models.Index(
                fields=("assignee", "status", "due_at"),
                name="hyd_task_assignee_state_idx",
            ),
            models.Index(
                fields=("person", "status"),
                name="hyd_task_person_state_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=Q(version__gte=1),
                name="hyd_task_version_positive",
            ),
            models.CheckConstraint(
                check=Q(is_active=True, created_by__isnull=False),
                name="hyd_task_active_creator_shape",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        status="completed",
                        completed_at__isnull=False,
                        cancelled_at__isnull=True,
                    )
                    | Q(
                        status="cancelled",
                        completed_at__isnull=True,
                        cancelled_at__isnull=False,
                    )
                    | Q(
                        status__in=("open", "in_progress"),
                        completed_at__isnull=True,
                        cancelled_at__isnull=True,
                    )
                ),
                name="hyd_task_terminal_timestamp_shape",
            ),
            models.CheckConstraint(
                check=(
                    Q(status__in=("completed", "cancelled"), resolution_reason__gt="")
                    | Q(status__in=("open", "in_progress"), resolution_reason="")
                ),
                name="hyd_task_resolution_reason_shape",
            ),
        )

    def __str__(self):
        return f"{self.person.hydra_id} / {self.title}"

    def get_absolute_url(self):
        return reverse("hydra-task-detail", kwargs={"task_uuid": self.uuid})

    @property
    def is_overdue(self):
        return (
            self.status in (self.Status.OPEN, self.Status.IN_PROGRESS)
            and self.due_at is not None
            and self.due_at < timezone.now()
        )

    def clean(self):
        super().clean()
        self.title = " ".join(self.title.split())
        self.description = self.description.strip()
        self.target_label = " ".join(self.target_label.split())
        self.resolution_reason = " ".join(self.resolution_reason.split())
        if self.person_id and self.person.merged_into_id:
            raise ValidationError({"person": _("Tasks require the canonical Person record.")})
        if self.target_kind == TaskTargetKind.PERSON and self.person_id:
            if self.target_uuid != self.person.uuid:
                raise ValidationError(
                    {"target_uuid": _("A Person task must target the same Person.")}
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
                raise TypeError("Hydra task identity and target are immutable.")
            if not service_update and any(
                original[field] != getattr(self, field) for field in self.SERVICE_FIELDS
            ):
                raise TypeError("Hydra tasks must be changed through the task services.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra tasks cannot be hard-deleted.")


class AppendOnlyTaskEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Hydra task events are append-only.")

    def delete(self):
        raise TypeError("Hydra task events are append-only.")


class HydraTaskEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        UPDATED = "updated", _("Updated")
        REASSIGNED = "reassigned", _("Reassigned")
        STATUS_CHANGED = "status_changed", _("Status changed")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")
        REOPENED = "reopened", _("Reopened")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    task = models.ForeignKey(
        HydraTask,
        on_delete=models.PROTECT,
        related_name="events",
    )
    sequence = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_task_events",
        null=True,
        blank=True,
    )
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    from_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_task_events_assigned_from",
        null=True,
        blank=True,
    )
    to_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_task_events_assigned_to",
        null=True,
        blank=True,
    )
    from_due_at = models.DateTimeField(null=True, blank=True)
    to_due_at = models.DateTimeField(null=True, blank=True)
    from_priority = models.CharField(max_length=12, blank=True)
    to_priority = models.CharField(max_length=12, blank=True)
    changed_fields = models.JSONField(default=list)
    reason = models.CharField(max_length=500, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = AppendOnlyTaskEventQuerySet.as_manager()

    class Meta:
        ordering = ("sequence", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("task", "sequence"),
                name="hyd_task_event_sequence_uniq",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_task_event_sequence_positive",
            ),
        )

    def __str__(self):
        return f"{self.task_id}:{self.sequence}:{self.action}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Hydra task events are append-only.")
        self.reason = " ".join(self.reason.split())
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra task events are append-only.")


class TaskDeliveryQuerySet(models.QuerySet):
    MUTABLE_FIELDS = {
        "notification",
        "notification_id",
        "status",
        "attempts",
        "last_attempt_at",
        "error_code",
    }

    def update(self, **kwargs):
        if not set(kwargs).issubset(self.MUTABLE_FIELDS):
            raise TypeError("Hydra task delivery identity is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Hydra task notification deliveries are durable evidence.")


class HydraTaskNotificationDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    task = models.ForeignKey(
        HydraTask,
        on_delete=models.PROTECT,
        related_name="notification_deliveries",
    )
    event = models.ForeignKey(
        HydraTaskEvent,
        on_delete=models.PROTECT,
        related_name="notification_deliveries",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_task_notification_deliveries",
    )
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TaskDeliveryQuerySet.as_manager()

    IMMUTABLE_FIELDS = (
        "uuid",
        "task_id",
        "event_id",
        "recipient_id",
        "created_at",
    )

    class Meta:
        ordering = ("created_at", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("event", "recipient"),
                name="hyd_task_delivery_event_recipient_uniq",
            ),
        )

    def __str__(self):
        return f"{self.event_id}:{self.recipient_id}:{self.status}"

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self)._base_manager.values(*self.IMMUTABLE_FIELDS).get(
                pk=self.pk
            )
            if any(
                original[field] != getattr(self, field)
                for field in self.IMMUTABLE_FIELDS
            ):
                raise TypeError("Hydra task delivery identity is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Hydra task notification deliveries are durable evidence.")
