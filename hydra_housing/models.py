from datetime import date, datetime, time
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra.models import HydraModel
from hydra_coordination.models import Location
from hydra_people.models import Person


class HousingFacility(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="housing_facilities",
        verbose_name=_("Location"),
    )
    name = models.CharField(max_length=120, verbose_name=_("Facility"))
    address = models.CharField(max_length=255, verbose_name=_("Address"))
    notes = models.TextField(blank=True, max_length=1000, verbose_name=_("Notes"))

    class Meta:
        ordering = ("location__company__company", "location__name", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("location", "name"),
                name="hyd_house_facility_location_name_uniq",
            ),
        )

    def __str__(self):
        return f"{self.location} / {self.name}"

    def get_absolute_url(self):
        return reverse("hydra-housing-facility-detail", kwargs={"facility_uuid": self.uuid})

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.address = " ".join(self.address.split())
        self.notes = self.notes.strip()


class HousingBuilding(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    facility = models.ForeignKey(
        HousingFacility,
        on_delete=models.PROTECT,
        related_name="buildings",
        verbose_name=_("Facility"),
    )
    name = models.CharField(max_length=120, verbose_name=_("Building"))
    notes = models.TextField(blank=True, max_length=500, verbose_name=_("Notes"))

    class Meta:
        ordering = ("facility__name", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("facility", "name"),
                name="hyd_house_building_facility_name_uniq",
            ),
        )

    def __str__(self):
        return f"{self.facility.name} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.notes = self.notes.strip()


class HousingFloor(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    building = models.ForeignKey(
        HousingBuilding,
        on_delete=models.PROTECT,
        related_name="floors",
        verbose_name=_("Building"),
    )
    name = models.CharField(max_length=60, verbose_name=_("Floor"))
    sort_order = models.SmallIntegerField(default=0, verbose_name=_("Sort order"))

    class Meta:
        ordering = ("building__facility__name", "building__name", "sort_order", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("building", "name"),
                name="hyd_house_floor_building_name_uniq",
            ),
        )

    def __str__(self):
        return f"{self.building.name} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())


class HousingRoom(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    facility = models.ForeignKey(
        HousingFacility,
        on_delete=models.PROTECT,
        related_name="rooms",
        verbose_name=_("Facility"),
    )
    name = models.CharField(max_length=80, verbose_name=_("Room"))
    floor = models.CharField(max_length=40, blank=True, verbose_name=_("Floor"))
    floor_unit = models.ForeignKey(
        HousingFloor,
        on_delete=models.PROTECT,
        related_name="rooms",
        null=True,
        blank=True,
        verbose_name=_("Building / floor"),
    )

    class Meta:
        ordering = ("facility__name", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("facility", "name"),
                name="hyd_house_room_facility_name_uniq",
            ),
        )

    def __str__(self):
        return f"{self.facility.name} / {self.name}"

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        self.floor = " ".join(self.floor.split())
        if (
            self.facility_id
            and self.floor_unit_id
            and self.floor_unit.building.facility_id != self.facility_id
        ):
            raise ValidationError(
                {"floor_unit": _("Choose a floor inside the room facility.")}
            )

    @property
    def hierarchy_label(self):
        if self.floor_unit_id:
            return str(self.floor_unit)
        return self.floor


class HousingBed(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    room = models.ForeignKey(
        HousingRoom,
        on_delete=models.PROTECT,
        related_name="beds",
        verbose_name=_("Room"),
    )
    label = models.CharField(max_length=60, verbose_name=_("Bed"))

    class Meta:
        ordering = ("room__facility__name", "room__name", "label")
        constraints = (
            models.UniqueConstraint(
                fields=("room", "label"),
                name="hyd_house_bed_room_label_uniq",
            ),
        )

    def __str__(self):
        return f"{self.room} / {self.label}"

    def clean(self):
        super().clean()
        self.label = " ".join(self.label.split())


class HousingAssignmentQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Housing assignments must be changed through the housing services.")

    def delete(self):
        raise TypeError("Housing assignments cannot be deleted.")


class HousingAssignment(HydraModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="housing_assignments",
        verbose_name=_("Person"),
    )
    bed = models.ForeignKey(
        HousingBed,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name=_("Bed"),
    )
    valid_from = models.DateField(default=timezone.localdate, verbose_name=_("Valid from"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Valid until"))
    reservation_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Temporary reservation expires at"),
    )
    notes = models.TextField(blank=True, max_length=500, verbose_name=_("Notes"))

    objects = HousingAssignmentQuerySet.as_manager()

    class Meta:
        ordering = ("-valid_from", "-pk")
        permissions = (
            ("reserve_housingassignment", "Can reserve housing"),
            ("renew_housingreservation", "Can renew housing reservations"),
            ("confirm_housingreservation", "Can confirm housing reservations"),
            ("cancel_housingreservation", "Can cancel housing reservations"),
            ("move_housingassignment", "Can move housing assignments"),
        )
        constraints = (
            models.CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gte=F("valid_from")),
                name="hyd_house_assignment_valid_dates",
            ),
            models.UniqueConstraint(
                fields=("bed",),
                condition=Q(is_active=True, valid_until__isnull=True),
                name="hyd_house_open_bed_uniq",
            ),
            models.UniqueConstraint(
                fields=("person",),
                condition=Q(is_active=True, valid_until__isnull=True),
                name="hyd_house_open_person_uniq",
            ),
        )
        indexes = (
            models.Index(fields=("bed", "valid_from", "valid_until"), name="hyd_house_bed_dates_idx"),
            models.Index(fields=("person", "valid_from", "valid_until"), name="hyd_house_person_dates_idx"),
        )

    def __str__(self):
        return f"{self.person} / {self.bed}"

    def is_current(self, day=None):
        day = day or timezone.localdate()
        return self.is_active and self.reservation_expires_at is None and self.valid_from <= day and (
            self.valid_until is None or self.valid_until >= day
        )

    @property
    def is_reservation(self):
        return self.is_active and self.valid_from > timezone.localdate()

    @property
    def is_temporary_reservation(self):
        return self.is_reservation and self.reservation_expires_at is not None

    @property
    def can_move(self):
        today = timezone.localdate()
        return (
            self.is_active
            and (
                self.reservation_expires_at is None
                or self.reservation_expires_at > timezone.now()
            )
            and (self.valid_until is None or self.valid_until >= today)
        )

    @property
    def can_cancel_reservation(self):
        return self.is_reservation and (
            self.reservation_expires_at is None
            or self.reservation_expires_at > timezone.now()
        )

    @property
    def state_label(self):
        day = timezone.localdate()
        if not self.is_active:
            terminal_action = None
            if self.pk:
                terminal_action = self.events.filter(
                    action__in=self.events.model.TERMINAL_ACTIONS
                ).values_list("action", flat=True).first()
            if terminal_action == HousingAssignmentEvent.Action.EXPIRED:
                return _("Expired")
            if terminal_action == HousingAssignmentEvent.Action.CANCELLED:
                return _("Cancelled")
            if terminal_action == HousingAssignmentEvent.Action.MOVED_OUT:
                return _("Moved")
            return _("Inactive")
        if (
            self.reservation_expires_at is not None
            and self.reservation_expires_at <= timezone.now()
        ):
            return _("Expired")
        if self.valid_from > day:
            if self.reservation_expires_at is not None:
                return _("Temporary hold")
            return _("Scheduled")
        if self.valid_until is not None and self.valid_until < day:
            return _("Ended")
        return _("Current")

    def clean(self):
        super().clean()
        self.notes = self.notes.strip()
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValidationError(
                {"valid_until": _("The end date cannot be before the start date.")}
            )
        if self.reservation_expires_at is not None:
            reservation_start = datetime.combine(self.valid_from, time.min)
            if timezone.is_aware(self.reservation_expires_at):
                reservation_start = timezone.make_aware(
                    reservation_start,
                    timezone.get_current_timezone(),
                )
            if self.reservation_expires_at > reservation_start:
                raise ValidationError(
                    {
                        "reservation_expires_at": _(
                            "A temporary hold must expire no later than the reservation start."
                        )
                    }
                )

        if not self.person_id or not self.bed_id:
            return
        end = self.valid_until or date.max
        overlapping = HousingAssignment._base_manager.filter(
            is_active=True,
            valid_from__lte=end,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=self.valid_from))
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        errors = {}
        if overlapping.filter(bed_id=self.bed_id).exists():
            errors["bed"] = _("This bed is already assigned during the selected period.")
        if overlapping.filter(person_id=self.person_id).exists():
            errors["person"] = _("This Person already has housing during the selected period.")
        if errors:
            raise ValidationError(errors)

    IMMUTABLE_FIELDS = (
        "uuid",
        "person_id",
        "bed_id",
        "valid_from",
        "notes",
        "created_by_id",
        "created_at",
    )

    def save(self, *args, **kwargs):
        housing_transition = kwargs.pop("housing_transition", False)
        if self.pk:
            original = type(self)._base_manager.values(
                *self.IMMUTABLE_FIELDS,
                "valid_until",
                "is_active",
                "reservation_expires_at",
            ).get(pk=self.pk)
            if any(original[field] != getattr(self, field) for field in self.IMMUTABLE_FIELDS):
                raise TypeError("Housing assignment facts cannot be rewritten.")
            old_until = original["valid_until"]
            if old_until is not None and (
                self.valid_until is None or self.valid_until > old_until
            ):
                raise TypeError("A housing assignment end date can only be narrowed.")
            if not original["is_active"] and self.is_active:
                raise TypeError("A cancelled housing assignment cannot be reactivated.")
            if (
                original["valid_until"] != self.valid_until
                or original["is_active"] != self.is_active
                or original["reservation_expires_at"] != self.reservation_expires_at
            ) and not housing_transition:
                raise TypeError("Housing assignment lifecycle must use the housing services.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Housing assignments cannot be deleted.")


class HousingAssignmentEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Housing assignment events are append-only.")

    def delete(self):
        raise TypeError("Housing assignment events are append-only.")


class HousingAssignmentEvent(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "assigned", _("Housing assigned")
        RESERVED = "reserved", _("Housing reserved")
        ENDED = "ended", _("Stay ended")
        CANCELLED = "cancelled", _("Reservation cancelled")
        RENEWED = "renewed", _("Reservation renewed")
        CONFIRMED = "confirmed", _("Reservation confirmed")
        EXPIRED = "expired", _("Reservation expired")
        MOVED_OUT = "moved_out", _("Moved out")
        MOVED_IN = "moved_in", _("Moved in")

    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

    ORIGIN_ACTIONS = (Action.ASSIGNED, Action.RESERVED, Action.MOVED_IN)
    TERMINAL_ACTIONS = (
        Action.ENDED,
        Action.CANCELLED,
        Action.EXPIRED,
        Action.MOVED_OUT,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    assignment = models.ForeignKey(
        HousingAssignment,
        on_delete=models.PROTECT,
        related_name="events",
    )
    related_assignment = models.ForeignKey(
        HousingAssignment,
        on_delete=models.PROTECT,
        related_name="related_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="housing_assignment_events",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.USER)
    effective_on = models.DateField()
    scheduled_until = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=255)
    occurred_at = models.DateTimeField(auto_now_add=True)

    objects = HousingAssignmentEventQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_housingassignmentevent", "Can view housing assignment events"),
        )
        indexes = (
            models.Index(
                fields=("assignment", "occurred_at"),
                name="hyd_house_evt_assign_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                check=~Q(reason=""),
                name="hyd_house_evt_reason",
            ),
            models.CheckConstraint(
                check=(
                    Q(source="user", actor__isnull=False)
                    | Q(source="system", actor__isnull=True)
                ),
                name="hyd_house_evt_source_actor",
            ),
            models.CheckConstraint(
                check=(
                    Q(action__in=("moved_out", "moved_in"), related_assignment__isnull=False)
                    | (
                        ~Q(action__in=("moved_out", "moved_in"))
                        & Q(related_assignment__isnull=True)
                    )
                ),
                name="hyd_house_evt_action_shape",
            ),
            models.CheckConstraint(
                check=Q(related_assignment__isnull=True)
                | ~Q(assignment=F("related_assignment")),
                name="hyd_house_evt_distinct_link",
            ),
            models.UniqueConstraint(
                fields=("assignment",),
                condition=Q(action__in=("assigned", "reserved", "moved_in")),
                name="hyd_house_evt_origin_uniq",
            ),
            models.UniqueConstraint(
                fields=("assignment",),
                condition=Q(
                    action__in=("ended", "cancelled", "expired", "moved_out")
                ),
                name="hyd_house_evt_terminal_uniq",
            ),
            models.UniqueConstraint(
                fields=("assignment",),
                condition=Q(action="confirmed"),
                name="hyd_house_evt_confirmed_uniq",
            ),
        )

    def clean(self):
        super().clean()
        self.reason = " ".join(self.reason.split())
        if not self.reason:
            raise ValidationError({"reason": _("A housing event requires a reason.")})
        moved = self.action in (self.Action.MOVED_OUT, self.Action.MOVED_IN)
        if moved != bool(self.related_assignment_id):
            raise ValidationError(
                {"related_assignment": _("Only move events require a related assignment.")}
            )
        if self.related_assignment_id == self.assignment_id:
            raise ValidationError(
                {"related_assignment": _("A move must link two different assignments.")}
            )
        if self.source == self.Source.USER and not self.actor_id:
            raise ValidationError({"actor": _("A user event requires an actor.")})
        if self.source == self.Source.SYSTEM and self.actor_id:
            raise ValidationError({"actor": _("A system event cannot impersonate a user.")})

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Housing assignment events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Housing assignment events are append-only.")

    def __str__(self):
        return f"{self.assignment} / {self.get_action_display()}"
