from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra.models import HorillaModel
from hydra_coordination.models import Location
from hydra_people.models import Person, PersonApplication
from recruitment.models import Candidate

from hydra_arrivals.storage import portal_email_storage


def portal_email_attachment_path(instance, filename):
    identifier = instance.uuid.hex
    return f"portal-email/{identifier[:2]}/{identifier}.payload"


class ArrivalPlan(HorillaModel):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        CONFIRMED = "confirmed", _("Confirmed")
        NO_SHOW = "no_show", _("No-show")

    class TransportType(models.TextChoices):
        BUS = "bus", _("Bus")
        AIR = "air", _("Air")
        TRAIN = "train", _("Train")
        CAR = "car", _("Car")
        OTHER = "other", _("Other")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="arrival_plans",
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_arrival_plans",
    )
    destination_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="arrival_plans",
    )
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coordinated_arrival_plans",
    )
    planned_at = models.DateTimeField()
    transport_type = models.CharField(
        max_length=16,
        choices=TransportType.choices,
        default=TransportType.BUS,
    )
    transport_reference = models.CharField(max_length=100, blank=True)
    pickup_point = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True, max_length=1000)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNED,
        editable=False,
    )
    actual_arrived_at = models.DateTimeField(null=True, blank=True, editable=False)
    no_show_reason = models.CharField(max_length=255, blank=True, editable=False)

    class Meta:
        ordering = ("planned_at", "person__passport_name", "pk")
        permissions = (
            ("assign_arrivalplan", "Can assign arrival coordinators"),
            ("transition_arrivalplan", "Can confirm or mark no-show arrivals"),
            (
                "receive_arrival_escalations",
                "Can receive scoped overdue arrival escalations",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("candidate",),
                condition=Q(status="planned"),
                name="hyd_arr_active_candidate_uniq",
            ),
        )
        indexes = (
            models.Index(
                fields=("destination_location", "status", "planned_at"),
                name="hyd_arr_location_status_idx",
            ),
            models.Index(
                fields=("coordinator", "status", "planned_at"),
                name="hyd_arr_coord_status_idx",
            ),
            models.Index(
                fields=("person", "status"),
                name="hyd_arr_person_status_idx",
            ),
        )

    def __str__(self):
        return f"{self.person.hydra_id} — {self.planned_at:%Y-%m-%d %H:%M}"

    def get_absolute_url(self):
        return reverse("hydra-arrival-detail", kwargs={"plan_uuid": self.uuid})

    @property
    def is_overdue(self):
        return self.status == self.Status.PLANNED and self.planned_at < timezone.now()

    def clean(self):
        super().clean()
        self.transport_reference = " ".join(self.transport_reference.split())
        self.pickup_point = " ".join(self.pickup_point.split())
        self.notes = self.notes.strip()
        self.no_show_reason = " ".join(self.no_show_reason.split())

        if self.person_id and self.candidate_id:
            try:
                linked_person_id = self.candidate.hydra_person_link.person_id
            except PersonApplication.DoesNotExist as error:
                raise ValidationError(
                    {"candidate": _("The application must be linked to a Hydra Person.")}
                ) from error
            if linked_person_id != self.person_id:
                raise ValidationError(
                    {"candidate": _("The application must belong to this Person.")}
                )

        if self.candidate_id and self.destination_location_id:
            recruitment = self.candidate.recruitment_id
            if (
                recruitment is None
                or recruitment.company_id_id != self.destination_location.company_id
            ):
                raise ValidationError(
                    {
                        "destination_location": _(
                            "The destination must belong to the recruitment company."
                        )
                    }
                )

        if self.status == self.Status.PLANNED:
            if self.actual_arrived_at or self.no_show_reason:
                raise ValidationError(_("A planned arrival cannot have an outcome."))
        elif self.status == self.Status.CONFIRMED:
            if not self.actual_arrived_at:
                raise ValidationError(
                    {"actual_arrived_at": _("Confirmed arrivals require an actual time.")}
                )
            if self.no_show_reason:
                raise ValidationError(_("A confirmed arrival cannot have a no-show reason."))
        elif self.status == self.Status.NO_SHOW:
            if self.actual_arrived_at:
                raise ValidationError(_("A no-show cannot have an actual arrival time."))
            if not self.no_show_reason:
                raise ValidationError(
                    {"no_show_reason": _("No-show requires a reason.")}
                )


class AppendOnlyArrivalQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Arrival history is append-only.")

    def delete(self):
        raise TypeError("Arrival history is append-only.")


class ArrivalStatusHistory(models.Model):
    plan = models.ForeignKey(
        ArrivalPlan,
        on_delete=models.PROTECT,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=16,
        choices=ArrivalPlan.Status.choices,
        blank=True,
    )
    to_status = models.CharField(max_length=16, choices=ArrivalPlan.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="arrival_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyArrivalQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_arrivalstatushistory", "Can view arrival status history"),
        )
        indexes = (
            models.Index(
                fields=("plan", "occurred_at"),
                name="hyd_arr_history_idx",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Arrival history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Arrival history is append-only.")


class ArrivalAutomationEventQuerySet(models.QuerySet):
    DELIVERY_FIELDS = {
        "notification_status",
        "notification_attempts",
        "notification_last_attempt_at",
        "notification_error_code",
        "notification",
    }

    def update(self, **kwargs):
        if set(kwargs) - self.DELIVERY_FIELDS:
            raise TypeError("Arrival automation event facts are append-only.")
        return super().update(**kwargs)

    def delete(self):
        raise TypeError("Arrival automation events are append-only.")


class ArrivalAutomationEvent(models.Model):
    class EventType(models.TextChoices):
        UPCOMING = "upcoming", _("Upcoming arrival")
        OVERDUE = "overdue", _("Overdue arrival")

    class NotificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    plan = models.ForeignKey(
        ArrivalPlan,
        on_delete=models.PROTECT,
        related_name="automation_events",
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    planned_at = models.DateTimeField()
    threshold_minutes = models.PositiveIntegerField(default=0)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_arrival_automation_events",
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
        related_name="hydra_arrival_automation_events",
        null=True,
        blank=True,
    )

    objects = ArrivalAutomationEventQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            (
                "view_arrivalautomationevent",
                "Can view arrival automation events",
            ),
        )
        indexes = (
            models.Index(
                fields=("notification_status", "occurred_at"),
                name="hyd_arr_auto_notify_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "plan",
                    "event_type",
                    "planned_at",
                    "threshold_minutes",
                    "recipient",
                ),
                name="hyd_arr_auto_event_uniq",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(event_type="upcoming", threshold_minutes__gt=0)
                    | models.Q(event_type="overdue", threshold_minutes=0)
                ),
                name="hyd_arr_auto_threshold",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(notification_status="sent")
                    | models.Q(notification__isnull=False)
                ),
                name="hyd_arr_auto_sent_record",
            ),
        )

    CORE_FIELDS = (
        "plan_id",
        "event_type",
        "planned_at",
        "threshold_minutes",
        "recipient_id",
        "occurred_at",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.values(*self.CORE_FIELDS).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.CORE_FIELDS):
                raise TypeError("Arrival automation event facts are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Arrival automation events are append-only.")


class OnboardingHandoff(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", _("Started")
        CONVERTED = "converted", _("Employee converted")
        ASSIGNED = "assigned", _("Team assigned; tasks pending")
        COMPLETED = "completed", _("Completed")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    arrival = models.OneToOneField(
        ArrivalPlan,
        on_delete=models.PROTECT,
        related_name="onboarding_handoff",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="onboarding_handoffs",
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_onboarding_handoff",
    )
    candidate_stage = models.OneToOneField(
        "onboarding.CandidateStage",
        on_delete=models.PROTECT,
        related_name="hydra_handoff",
    )
    employee_conversion = models.ForeignKey(
        "hydra_people.EmployeeConversion",
        on_delete=models.PROTECT,
        related_name="onboarding_handoffs",
        null=True,
        blank=True,
    )
    person_assignment = models.ForeignKey(
        "hydra_coordination.PersonAssignment",
        on_delete=models.PROTECT,
        related_name="onboarding_handoffs",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.STARTED,
        editable=False,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_onboarding_handoffs",
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    last_reconciled_at = models.DateTimeField(null=True, blank=True, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    started_snapshot = models.JSONField(editable=False)

    class Meta:
        ordering = ("-initiated_at", "-pk")
        default_permissions = ("view",)
        permissions = (
            (
                "initiate_onboardinghandoff",
                "Can initiate a confirmed-arrival onboarding handoff",
            ),
            (
                "reconcile_onboardinghandoff",
                "Can reconcile onboarding handoff milestones",
            ),
        )
        indexes = (
            models.Index(
                fields=("status", "last_reconciled_at"),
                name="hyd_arr_handoff_state_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=(
                    Q(
                        status="started",
                        employee_conversion__isnull=True,
                        person_assignment__isnull=True,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status="converted",
                        employee_conversion__isnull=False,
                        person_assignment__isnull=True,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status="assigned",
                        employee_conversion__isnull=False,
                        person_assignment__isnull=False,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status="completed",
                        employee_conversion__isnull=False,
                        person_assignment__isnull=False,
                        completed_at__isnull=False,
                    )
                ),
                name="hyd_arr_handoff_state_shape",
            ),
        )

    def __str__(self):
        return f"{self.person.hydra_id} / {self.get_status_display()}"

    def get_absolute_url(self):
        return self.arrival.get_absolute_url()

    def clean(self):
        super().clean()
        if self.arrival_id:
            if self.arrival.status != ArrivalPlan.Status.CONFIRMED:
                raise ValidationError(
                    {"arrival": _("Only a confirmed arrival can enter onboarding.")}
                )
            if self.person_id and self.arrival.person_id != self.person_id:
                raise ValidationError({"person": _("Arrival and handoff Person differ.")})
            if self.candidate_id and self.arrival.candidate_id != self.candidate_id:
                raise ValidationError(
                    {"candidate": _("Arrival and handoff application differ.")}
                )
        if self.candidate_stage_id and self.candidate_id:
            if self.candidate_stage.candidate_id_id != self.candidate_id:
                raise ValidationError(
                    {"candidate_stage": _("The onboarding stage belongs to another candidate.")}
                )
            if (
                self.candidate_stage.onboarding_stage_id.recruitment_id_id
                != self.candidate.recruitment_id_id
            ):
                raise ValidationError(
                    {"candidate_stage": _("The onboarding stage belongs to another recruitment.")}
                )
        if self.employee_conversion_id:
            if self.employee_conversion.person_id != self.person_id:
                raise ValidationError(
                    {"employee_conversion": _("The conversion belongs to another handoff subject.")}
                )
        if self.person_assignment_id:
            if self.person_assignment.person_id != self.person_id:
                raise ValidationError(
                    {"person_assignment": _("The assignment belongs to another Person.")}
                )
            if (
                self.person_assignment.team.section.location_id
                != self.arrival.destination_location_id
            ):
                raise ValidationError(
                    {"person_assignment": _("The assignment does not match the arrival location.")}
                )
        if not self.started_snapshot:
            raise ValidationError(
                {"started_snapshot": _("The handoff start snapshot cannot be empty.")}
            )


class AppendOnlyHandoffEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Onboarding handoff events are append-only.")

    def delete(self):
        raise TypeError("Onboarding handoff events are append-only.")


class OnboardingHandoffEvent(models.Model):
    class EventType(models.TextChoices):
        STARTED = "started", _("Handoff started")
        CONVERSION_RECORDED = "conversion", _("Employee conversion recorded")
        ASSIGNMENT_RECORDED = "assignment", _("Team assignment recorded")
        COMPLETED = "completed", _("Handoff completed")

    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

    handoff = models.ForeignKey(
        OnboardingHandoff,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    source = models.CharField(max_length=12, choices=Source.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="onboarding_handoff_events",
        null=True,
        blank=True,
    )
    employee_conversion = models.ForeignKey(
        "hydra_people.EmployeeConversion",
        on_delete=models.PROTECT,
        related_name="onboarding_handoff_events",
        null=True,
        blank=True,
    )
    person_assignment = models.ForeignKey(
        "hydra_coordination.PersonAssignment",
        on_delete=models.PROTECT,
        related_name="onboarding_handoff_events",
        null=True,
        blank=True,
    )
    snapshot = models.JSONField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyHandoffEventQuerySet.as_manager()

    class Meta:
        ordering = ("occurred_at", "pk")
        default_permissions = ()
        permissions = (
            ("view_onboardinghandoffevent", "Can view onboarding handoff events"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("handoff", "event_type"),
                name="hyd_arr_handoff_event_uniq",
            ),
            models.CheckConstraint(
                check=(
                    Q(source="user", actor__isnull=False)
                    | Q(source="system", actor__isnull=True)
                ),
                name="hyd_arr_handoff_event_actor",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        event_type="started",
                        employee_conversion__isnull=True,
                        person_assignment__isnull=True,
                    )
                    | Q(
                        event_type="conversion",
                        employee_conversion__isnull=False,
                        person_assignment__isnull=True,
                    )
                    | Q(
                        event_type="assignment",
                        person_assignment__isnull=False,
                    )
                    | Q(
                        event_type="completed",
                        employee_conversion__isnull=False,
                        person_assignment__isnull=False,
                    )
                ),
                name="hyd_arr_handoff_event_shape",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Onboarding handoff events are append-only.")
        if not self.snapshot:
            raise ValidationError({"snapshot": _("Event snapshot cannot be empty.")})
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Onboarding handoff events are append-only.")


class OnboardingPortalDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENDING = "sending", _("Sending")
        RETRY = "retry", _("Waiting for retry")
        SENT = "sent", _("Sent")
        DEAD = "dead", _("Retries exhausted")
        CANCELLED = "cancelled", _("Cancelled")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name="hydra_portal_deliveries",
    )
    portal = models.ForeignKey(
        "onboarding.OnboardingPortal",
        on_delete=models.PROTECT,
        related_name="hydra_deliveries",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_onboarding_portal_deliveries",
    )
    email_configuration = models.ForeignKey(
        "base.DynamicEmailConfiguration",
        on_delete=models.PROTECT,
        related_name="hydra_portal_deliveries",
        null=True,
        blank=True,
        editable=False,
    )
    idempotency_key = models.CharField(max_length=64, unique=True, editable=False)
    portal_token = models.CharField(max_length=200, editable=False)
    recipient = models.EmailField(max_length=254, editable=False)
    sender = models.CharField(max_length=320, editable=False)
    reply_to = models.EmailField(max_length=254, editable=False)
    subject = models.CharField(max_length=255, editable=False)
    body_html = models.TextField(editable=False)
    payload_sha256 = models.CharField(max_length=64, editable=False)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        editable=False,
    )
    attempts = models.PositiveSmallIntegerField(default=0, editable=False)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True, editable=False)
    lease_token = models.UUIDField(null=True, blank=True, editable=False)
    lease_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    onboarding_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_error_code = models.CharField(max_length=80, blank=True, editable=False)
    onboarding_error_code = models.CharField(max_length=80, blank=True, editable=False)
    payload_purged_at = models.DateTimeField(null=True, blank=True, editable=False)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-requested_at", "-pk")
        default_permissions = ("view",)
        permissions = (
            ("retry_onboardingportaldelivery", "Can retry portal email delivery"),
        )
        indexes = (
            models.Index(
                fields=("status", "next_attempt_at"),
                name="hyd_arr_portal_due_idx",
            ),
            models.Index(
                fields=("candidate", "requested_at"),
                name="hyd_arr_portal_cand_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("candidate",),
                condition=Q(status__in=("pending", "retry", "sending")),
                name="hyd_arr_portal_one_active",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        status="pending",
                        sent_at__isnull=True,
                        lease_token__isnull=True,
                        lease_expires_at__isnull=True,
                    )
                    | Q(
                        status="retry",
                        sent_at__isnull=True,
                        lease_token__isnull=True,
                        lease_expires_at__isnull=True,
                    )
                    | Q(
                        status="sending",
                        sent_at__isnull=True,
                        lease_token__isnull=False,
                        lease_expires_at__isnull=False,
                    )
                    | Q(
                        status="sent",
                        sent_at__isnull=False,
                        lease_token__isnull=True,
                        lease_expires_at__isnull=True,
                    )
                    | Q(
                        status__in=("dead", "cancelled"),
                        sent_at__isnull=True,
                        lease_token__isnull=True,
                        lease_expires_at__isnull=True,
                    )
                ),
                name="hyd_arr_portal_state_shape",
            ),
            models.CheckConstraint(
                check=Q(attempts__gte=0),
                name="hyd_arr_portal_attempts_nonneg",
            ),
        )

    def __str__(self):
        return f"{self.uuid} / {self.get_status_display()}"


class OnboardingPortalDeliveryAttachment(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    delivery = models.ForeignKey(
        OnboardingPortalDelivery,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    file = models.FileField(
        storage=portal_email_storage,
        upload_to=portal_email_attachment_path,
        max_length=255,
        blank=True,
    )
    original_filename = models.CharField(max_length=255, editable=False)
    content_type = models.CharField(max_length=50, editable=False)
    size = models.PositiveBigIntegerField(editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    purged_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("pk",)
        default_permissions = ()
        constraints = (
            models.CheckConstraint(
                check=Q(size__gt=0),
                name="hyd_arr_portal_att_size_pos",
            ),
        )

    def __str__(self):
        return f"{self.delivery_id} / {self.original_filename}"


class AppendOnlyPortalDeliveryEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Portal delivery events are append-only.")

    def delete(self):
        raise TypeError("Portal delivery events are append-only.")


class OnboardingPortalDeliveryEvent(models.Model):
    class EventType(models.TextChoices):
        QUEUED = "queued", _("Queued")
        CLAIMED = "claimed", _("Claimed for delivery")
        RETRY_SCHEDULED = "retry", _("Retry scheduled")
        SENT = "sent", _("Sent")
        DEAD = "dead", _("Retries exhausted")
        CANCELLED = "cancelled", _("Cancelled")
        MANUAL_RETRY = "manual_retry", _("Manual retry")
        ONBOARDING_STARTED = "onboarding", _("Onboarding started")
        ONBOARDING_FAILED = "onboarding_failed", _("Onboarding start failed")
        PAYLOAD_PURGED = "purged", _("Payload purged")

    delivery = models.ForeignKey(
        OnboardingPortalDelivery,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="onboarding_portal_delivery_events",
        null=True,
        blank=True,
    )
    error_code = models.CharField(max_length=80, blank=True)
    attempt = models.PositiveSmallIntegerField(default=0)
    snapshot = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyPortalDeliveryEventQuerySet.as_manager()

    class Meta:
        ordering = ("occurred_at", "pk")
        default_permissions = ()
        permissions = (
            (
                "view_onboardingportaldeliveryevent",
                "Can view portal delivery events",
            ),
        )
        indexes = (
            models.Index(
                fields=("delivery", "occurred_at"),
                name="hyd_arr_portal_event_idx",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Portal delivery events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Portal delivery events are append-only.")
