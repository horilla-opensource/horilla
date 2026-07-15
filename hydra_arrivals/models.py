from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from horilla.models import HorillaModel
from hydra_coordination.models import Location
from hydra_people.models import Person, PersonApplication
from recruitment.models import Candidate


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
