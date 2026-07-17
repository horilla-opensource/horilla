from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from hydra_housing.models import (
    HousingAssignment,
    HousingAssignmentEvent,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.selectors import (
    HOUSING_VIEW_PERMISSIONS,
    eligible_people_for_housing_period,
    housing_assignments_for_user,
    housing_beds_for_user,
    housing_buildings_for_user,
    housing_facilities_for_user,
    housing_floors_for_user,
    housing_locations_for_user,
    housing_rooms_for_user,
)
from hydra_people.models import Person
from hydra_people.identity import ensure_canonical_person


def _require_permissions(actor, *permissions):
    required = HOUSING_VIEW_PERMISSIONS + permissions
    if not actor.is_authenticated or not actor.has_perms(required):
        raise PermissionDenied


def _stamp(instance, actor):
    if instance._state.adding:
        instance.created_by = actor
    instance.modified_by = actor


def _normalized_reason(reason):
    normalized = " ".join((reason or "").split())
    if not normalized:
        raise ValidationError({"reason": _("A reason is required.")})
    if len(normalized) > 255:
        raise ValidationError({"reason": _("The reason cannot exceed 255 characters.")})
    return normalized


def _record_assignment_event(
    *,
    assignment,
    action,
    actor,
    effective_on,
    reason,
    related_assignment=None,
    scheduled_until=None,
):
    event = HousingAssignmentEvent(
        assignment=assignment,
        related_assignment=related_assignment,
        action=action,
        actor=actor,
        source=(
            HousingAssignmentEvent.Source.USER
            if actor is not None
            else HousingAssignmentEvent.Source.SYSTEM
        ),
        effective_on=effective_on,
        scheduled_until=scheduled_until,
        reason=reason,
    )
    event.full_clean()
    event.save()
    return event


@dataclass(frozen=True)
class HousingReservationExpiryResult:
    selected: int
    expired: int


def _reservation_start_at(valid_from):
    start_at = datetime.combine(valid_from, time.min)
    if timezone.is_aware(timezone.now()):
        return timezone.make_aware(start_at, timezone.get_current_timezone())
    return start_at


def _validate_reservation_expiry(*, valid_from, expires_at, now=None):
    if expires_at is None:
        return
    now = now or timezone.now()
    if valid_from <= timezone.localdate(now):
        raise ValidationError(
            {
                "reservation_expires_at": _(
                    "Only a future housing reservation can have a temporary hold."
                )
            }
        )
    if expires_at <= now:
        raise ValidationError(
            {"reservation_expires_at": _("The temporary hold must expire in the future.")}
        )
    if expires_at > _reservation_start_at(valid_from):
        raise ValidationError(
            {
                "reservation_expires_at": _(
                    "The temporary hold must expire no later than the reservation start."
                )
            }
        )


def _lock_assignment_graph(*, assignment_uuid, extra_bed_ids=()):
    snapshot = HousingAssignment._base_manager.only(
        "pk", "person_id", "bed_id"
    ).get(uuid=assignment_uuid)
    Person._base_manager.select_for_update().get(pk=snapshot.person_id)
    bed_ids = sorted({snapshot.bed_id, *extra_bed_ids})
    beds = {
        bed.pk: bed
        for bed in HousingBed._base_manager.select_for_update()
        .select_related("room__facility__location")
        .filter(pk__in=bed_ids)
        .order_by("pk")
    }
    if len(beds) != len(bed_ids):
        raise HousingBed.DoesNotExist
    assignment = (
        HousingAssignment._base_manager.select_for_update()
        .select_related("person", "bed__room__facility__location")
        .get(pk=snapshot.pk)
    )
    return assignment, beds


def _assignment_conflicts(*, person, bed, valid_from, valid_until, exclude_ids=()):
    end = valid_until or date.max
    overlapping = (
        HousingAssignment._base_manager.select_for_update()
        .filter(is_active=True, valid_from__lte=end)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from))
    )
    if exclude_ids:
        overlapping = overlapping.exclude(pk__in=exclude_ids)
    errors = {}
    if overlapping.filter(bed=bed).exists():
        errors["bed"] = _("This bed is already assigned during the selected period.")
    if overlapping.filter(person=person).exists():
        errors["person"] = _("This Person already has housing during the selected period.")
    return errors


def _require_assignment_scope(*, actor, assignment):
    if not housing_assignments_for_user(user=actor).filter(pk=assignment.pk).exists():
        raise PermissionDenied


def _require_bed_and_person_scope(*, actor, person, bed, valid_from, allow_planned_arrival):
    if not housing_beds_for_user(user=actor).filter(
        pk=bed.pk,
        is_active=True,
        room__is_active=True,
        room__facility__is_active=True,
    ).filter(
        Q(room__floor_unit__isnull=True)
        | Q(
            room__floor_unit__is_active=True,
            room__floor_unit__building__is_active=True,
        )
    ).exists():
        raise PermissionDenied
    if not eligible_people_for_housing_period(
        user=actor,
        location=bed.room.facility.location,
        valid_from=valid_from,
        allow_planned_arrival=allow_planned_arrival,
    ).filter(pk=person.pk).exists():
        raise PermissionDenied


@transaction.atomic
def save_housing_facility(*, facility: HousingFacility, actor) -> HousingFacility:
    permission = "add_housingfacility" if facility._state.adding else "change_housingfacility"
    _require_permissions(actor, f"hydra_housing.{permission}")
    if not housing_locations_for_user(user=actor).filter(pk=facility.location_id).exists():
        raise PermissionDenied
    if not facility._state.adding:
        current = HousingFacility._base_manager.select_for_update().get(pk=facility.pk)
        if not housing_facilities_for_user(user=actor).filter(pk=current.pk).exists():
            raise PermissionDenied
        if current.location_id != facility.location_id:
            raise ValidationError({"location": _("A facility location cannot be changed.")})
        facility.created_by = current.created_by
    _stamp(facility, actor)
    facility.full_clean()
    facility.save()
    return facility


@transaction.atomic
def save_housing_building(*, building: HousingBuilding, actor) -> HousingBuilding:
    permission = "add_housingbuilding" if building._state.adding else "change_housingbuilding"
    _require_permissions(actor, f"hydra_housing.{permission}")
    if not housing_facilities_for_user(user=actor).filter(
        pk=building.facility_id,
        is_active=True,
    ).exists():
        raise PermissionDenied
    if not building._state.adding:
        current = HousingBuilding._base_manager.select_for_update().get(pk=building.pk)
        if not housing_buildings_for_user(user=actor).filter(pk=current.pk).exists():
            raise PermissionDenied
        if current.facility_id != building.facility_id:
            raise ValidationError({"facility": _("A building facility cannot be changed.")})
        building.created_by = current.created_by
    _stamp(building, actor)
    building.full_clean()
    building.save()
    return building


@transaction.atomic
def save_housing_floor(*, floor: HousingFloor, actor) -> HousingFloor:
    permission = "add_housingfloor" if floor._state.adding else "change_housingfloor"
    _require_permissions(actor, f"hydra_housing.{permission}")
    if not housing_buildings_for_user(user=actor).filter(
        pk=floor.building_id,
        is_active=True,
        facility__is_active=True,
    ).exists():
        raise PermissionDenied
    if not floor._state.adding:
        current = HousingFloor._base_manager.select_for_update().get(pk=floor.pk)
        if not housing_floors_for_user(user=actor).filter(pk=current.pk).exists():
            raise PermissionDenied
        if current.building_id != floor.building_id:
            raise ValidationError({"building": _("A floor building cannot be changed.")})
        floor.created_by = current.created_by
    _stamp(floor, actor)
    floor.full_clean()
    floor.save()
    return floor


@transaction.atomic
def save_housing_room(*, room: HousingRoom, actor) -> HousingRoom:
    permission = "add_housingroom" if room._state.adding else "change_housingroom"
    _require_permissions(actor, f"hydra_housing.{permission}")
    if not housing_facilities_for_user(user=actor).filter(pk=room.facility_id, is_active=True).exists():
        raise PermissionDenied
    if room.floor_unit_id and not housing_floors_for_user(user=actor).filter(
        pk=room.floor_unit_id,
        is_active=True,
        building__is_active=True,
        building__facility_id=room.facility_id,
    ).exists():
        raise PermissionDenied
    if not room._state.adding:
        current = HousingRoom._base_manager.select_for_update().get(pk=room.pk)
        if not housing_rooms_for_user(user=actor).filter(pk=current.pk).exists():
            raise PermissionDenied
        if current.facility_id != room.facility_id:
            raise ValidationError({"facility": _("A room facility cannot be changed.")})
        room.created_by = current.created_by
    _stamp(room, actor)
    room.full_clean()
    room.save()
    return room


@transaction.atomic
def save_housing_bed(*, bed: HousingBed, actor) -> HousingBed:
    permission = "add_housingbed" if bed._state.adding else "change_housingbed"
    _require_permissions(actor, f"hydra_housing.{permission}")
    if not housing_rooms_for_user(user=actor).filter(
        pk=bed.room_id,
        is_active=True,
        facility__is_active=True,
    ).exists():
        raise PermissionDenied
    if not bed._state.adding:
        current = HousingBed._base_manager.select_for_update().get(pk=bed.pk)
        if not housing_beds_for_user(user=actor).filter(pk=current.pk).exists():
            raise PermissionDenied
        if current.room_id != bed.room_id:
            raise ValidationError({"room": _("A bed room cannot be changed.")})
        bed.created_by = current.created_by
    _stamp(bed, actor)
    bed.full_clean()
    bed.save()
    return bed


@transaction.atomic
def assign_housing(*, assignment: HousingAssignment, actor) -> HousingAssignment:
    _require_permissions(actor, "hydra_housing.add_housingassignment")
    if not assignment._state.adding:
        raise ValidationError(_("A new housing assignment was expected."))

    reservation = assignment.valid_from > timezone.localdate()
    if reservation:
        _require_permissions(actor, "hydra_housing.reserve_housingassignment")
        _validate_reservation_expiry(
            valid_from=assignment.valid_from,
            expires_at=assignment.reservation_expires_at,
        )
    elif assignment.reservation_expires_at is not None:
        raise ValidationError(
            {
                "reservation_expires_at": _(
                    "Only a future housing reservation can have a temporary hold."
                )
            }
        )

    person = Person._base_manager.select_for_update().get(pk=assignment.person_id)
    ensure_canonical_person(person)
    bed = HousingBed._base_manager.select_for_update().select_related(
        "room__facility__location"
    ).get(pk=assignment.bed_id)
    _require_bed_and_person_scope(
        actor=actor,
        person=person,
        bed=bed,
        valid_from=assignment.valid_from,
        allow_planned_arrival=reservation,
    )

    assignment.person = person
    assignment.bed = bed
    assignment.is_active = True
    assignment.created_by = actor
    assignment.modified_by = actor
    assignment.full_clean(validate_constraints=False)

    errors = _assignment_conflicts(
        person=person,
        bed=bed,
        valid_from=assignment.valid_from,
        valid_until=assignment.valid_until,
    )
    if errors:
        raise ValidationError(errors)
    assignment.save()
    _record_assignment_event(
        assignment=assignment,
        action=(
            HousingAssignmentEvent.Action.RESERVED
            if reservation
            else HousingAssignmentEvent.Action.ASSIGNED
        ),
        actor=actor,
        effective_on=assignment.valid_from,
        scheduled_until=assignment.valid_until,
        reason=(
            _("Housing reservation created.")
            if reservation
            else _("Housing assignment created.")
        ),
    )
    return assignment


@transaction.atomic
def end_housing_assignment(*, assignment_uuid, valid_until, reason, actor) -> HousingAssignment:
    _require_permissions(actor, "hydra_housing.change_housingassignment")
    reason = _normalized_reason(reason)
    assignment, _beds = _lock_assignment_graph(assignment_uuid=assignment_uuid)
    _require_assignment_scope(actor=actor, assignment=assignment)
    terminal = assignment.events.filter(
        action__in=HousingAssignmentEvent.TERMINAL_ACTIONS
    ).first()
    if terminal:
        if (
            terminal.action == HousingAssignmentEvent.Action.ENDED
            and terminal.effective_on == valid_until
            and terminal.reason == reason
        ):
            return assignment
        raise ValidationError(_("This housing assignment already has a terminal event."))
    if assignment.valid_from > timezone.localdate():
        raise ValidationError(_("Cancel a future reservation instead of ending a stay."))
    if assignment.valid_until is not None:
        if assignment.valid_until != valid_until:
            raise ValidationError(_("This housing assignment is already ended."))
    if valid_until < assignment.valid_from:
        raise ValidationError({"valid_until": _("The end date cannot be before the start date.")})
    if valid_until > timezone.localdate():
        raise ValidationError({"valid_until": _("End a stay today or on a past date.")})
    if assignment.valid_until is None:
        assignment.valid_until = valid_until
        assignment.modified_by = actor
        assignment.full_clean(validate_constraints=False)
        assignment.save(
            housing_transition=True,
            update_fields=("valid_until", "modified_by"),
        )
    _record_assignment_event(
        assignment=assignment,
        action=HousingAssignmentEvent.Action.ENDED,
        actor=actor,
        effective_on=valid_until,
        scheduled_until=valid_until,
        reason=reason,
    )
    return assignment


@transaction.atomic
def cancel_housing_reservation(*, assignment_uuid, reason, actor) -> HousingAssignment:
    _require_permissions(
        actor,
        "hydra_housing.change_housingassignment",
        "hydra_housing.cancel_housingreservation",
    )
    reason = _normalized_reason(reason)
    assignment, _beds = _lock_assignment_graph(assignment_uuid=assignment_uuid)
    _require_assignment_scope(actor=actor, assignment=assignment)
    terminal = assignment.events.filter(
        action__in=HousingAssignmentEvent.TERMINAL_ACTIONS
    ).first()
    if terminal:
        if (
            terminal.action == HousingAssignmentEvent.Action.CANCELLED
            and terminal.reason == reason
        ):
            return assignment
        raise ValidationError(_("This housing assignment already has a terminal event."))
    if not assignment.is_active or assignment.valid_from <= timezone.localdate():
        raise ValidationError(_("Only a future active housing reservation can be cancelled."))
    if (
        assignment.reservation_expires_at is not None
        and assignment.reservation_expires_at <= timezone.now()
    ):
        raise ValidationError(_("This temporary reservation has already expired."))
    assignment.is_active = False
    assignment.modified_by = actor
    assignment.save(
        housing_transition=True,
        update_fields=("is_active", "modified_by"),
    )
    _record_assignment_event(
        assignment=assignment,
        action=HousingAssignmentEvent.Action.CANCELLED,
        actor=actor,
        effective_on=assignment.valid_from,
        scheduled_until=assignment.valid_until,
        reason=reason,
    )
    return assignment


@transaction.atomic
def renew_housing_reservation(
    *,
    assignment_uuid,
    reservation_expires_at,
    reason,
    actor,
) -> HousingAssignment:
    _require_permissions(
        actor,
        "hydra_housing.change_housingassignment",
        "hydra_housing.reserve_housingassignment",
        "hydra_housing.renew_housingreservation",
    )
    reason = _normalized_reason(reason)
    assignment, _beds = _lock_assignment_graph(assignment_uuid=assignment_uuid)
    _require_assignment_scope(actor=actor, assignment=assignment)
    if (
        not assignment.is_active
        or assignment.valid_from <= timezone.localdate()
        or assignment.reservation_expires_at is None
    ):
        raise ValidationError(_("Only an active temporary reservation can be renewed."))
    if assignment.reservation_expires_at <= timezone.now():
        raise ValidationError(_("This temporary reservation has already expired."))
    previous = assignment.reservation_expires_at
    if reservation_expires_at == previous:
        repeated = assignment.events.filter(
            action=HousingAssignmentEvent.Action.RENEWED,
            reason=reason,
            effective_on=timezone.localdate(reservation_expires_at),
        ).exists()
        if repeated:
            return assignment
    _validate_reservation_expiry(
        valid_from=assignment.valid_from,
        expires_at=reservation_expires_at,
    )
    if reservation_expires_at <= previous:
        raise ValidationError(
            {
                "reservation_expires_at": _(
                    "A renewal must extend the current temporary hold."
                )
            }
        )
    assignment.reservation_expires_at = reservation_expires_at
    assignment.modified_by = actor
    assignment.full_clean(validate_constraints=False)
    assignment.save(
        housing_transition=True,
        update_fields=("reservation_expires_at", "modified_by"),
    )
    _record_assignment_event(
        assignment=assignment,
        action=HousingAssignmentEvent.Action.RENEWED,
        actor=actor,
        effective_on=timezone.localdate(reservation_expires_at),
        scheduled_until=assignment.valid_until,
        reason=reason,
    )
    return assignment


@transaction.atomic
def confirm_housing_reservation(*, assignment_uuid, reason, actor) -> HousingAssignment:
    _require_permissions(
        actor,
        "hydra_housing.change_housingassignment",
        "hydra_housing.reserve_housingassignment",
        "hydra_housing.confirm_housingreservation",
    )
    reason = _normalized_reason(reason)
    assignment, _beds = _lock_assignment_graph(assignment_uuid=assignment_uuid)
    _require_assignment_scope(actor=actor, assignment=assignment)
    confirmed = assignment.events.filter(
        action=HousingAssignmentEvent.Action.CONFIRMED
    ).first()
    if assignment.reservation_expires_at is None:
        if confirmed and confirmed.reason == reason:
            return assignment
        raise ValidationError(_("This reservation is not a temporary hold."))
    if not assignment.is_active or assignment.valid_from <= timezone.localdate():
        raise ValidationError(_("Only an active future reservation can be confirmed."))
    if assignment.reservation_expires_at <= timezone.now():
        raise ValidationError(_("This temporary reservation has already expired."))
    assignment.reservation_expires_at = None
    assignment.modified_by = actor
    assignment.save(
        housing_transition=True,
        update_fields=("reservation_expires_at", "modified_by"),
    )
    _record_assignment_event(
        assignment=assignment,
        action=HousingAssignmentEvent.Action.CONFIRMED,
        actor=actor,
        effective_on=timezone.localdate(),
        scheduled_until=assignment.valid_until,
        reason=reason,
    )
    return assignment


def expire_due_housing_reservations(*, now=None, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    now = now or timezone.now()
    assignment_uuids = list(
        HousingAssignment._base_manager.filter(
            is_active=True,
            reservation_expires_at__isnull=False,
            reservation_expires_at__lte=now,
        )
        .order_by("reservation_expires_at", "pk")
        .values_list("uuid", flat=True)[:limit]
    )
    expired = 0
    for assignment_uuid in assignment_uuids:
        with transaction.atomic():
            assignment, _beds = _lock_assignment_graph(
                assignment_uuid=assignment_uuid
            )
            if (
                not assignment.is_active
                or assignment.reservation_expires_at is None
                or assignment.reservation_expires_at > now
            ):
                continue
            terminal = assignment.events.filter(
                action__in=HousingAssignmentEvent.TERMINAL_ACTIONS
            ).first()
            if terminal:
                continue
            expires_at = assignment.reservation_expires_at
            assignment.is_active = False
            assignment.save(
                housing_transition=True,
                update_fields=("is_active",),
            )
            _record_assignment_event(
                assignment=assignment,
                action=HousingAssignmentEvent.Action.EXPIRED,
                actor=None,
                effective_on=timezone.localdate(expires_at),
                scheduled_until=assignment.valid_until,
                reason=_("Temporary housing reservation expired."),
            )
            expired += 1
    return HousingReservationExpiryResult(
        selected=len(assignment_uuids),
        expired=expired,
    )


@transaction.atomic
def move_housing_assignment(
    *,
    assignment_uuid,
    destination_bed_id,
    effective_on,
    reason,
    actor,
) -> HousingAssignment:
    _require_permissions(
        actor,
        "hydra_housing.add_housingassignment",
        "hydra_housing.change_housingassignment",
        "hydra_housing.move_housingassignment",
    )
    if effective_on > timezone.localdate():
        _require_permissions(actor, "hydra_housing.reserve_housingassignment")
    reason = _normalized_reason(reason)
    assignment, beds = _lock_assignment_graph(
        assignment_uuid=assignment_uuid,
        extra_bed_ids=(destination_bed_id,),
    )
    _require_assignment_scope(actor=actor, assignment=assignment)
    destination_bed = beds[destination_bed_id]

    previous_move = assignment.events.filter(
        action=HousingAssignmentEvent.Action.MOVED_OUT
    ).select_related("related_assignment__bed").first()
    if previous_move:
        if (
            previous_move.related_assignment.bed_id == destination_bed_id
            and previous_move.effective_on == effective_on
            and previous_move.reason == reason
        ):
            return previous_move.related_assignment
        raise ValidationError(_("This assignment was already moved with different facts."))

    if assignment.bed_id == destination_bed_id:
        raise ValidationError({"destination_bed": _("Choose a different destination bed.")})
    if not assignment.is_active:
        raise ValidationError(_("An inactive housing assignment cannot be moved."))
    if (
        assignment.reservation_expires_at is not None
        and assignment.reservation_expires_at <= timezone.now()
    ):
        raise ValidationError(_("An expired temporary reservation cannot be moved."))
    today = timezone.localdate()
    if effective_on < today:
        raise ValidationError({"effective_on": _("A move cannot be backdated.")})
    if effective_on < assignment.valid_from:
        raise ValidationError({"effective_on": _("A move cannot precede the source assignment.")})
    old_until = assignment.valid_until
    if old_until is not None and effective_on > old_until:
        raise ValidationError({"effective_on": _("The source assignment ends before this move.")})
    same_start_reservation = effective_on == assignment.valid_from and assignment.is_reservation
    if effective_on == assignment.valid_from and not same_start_reservation:
        raise ValidationError(
            {"effective_on": _("A current stay can move only after its first recorded day.")}
        )

    _require_bed_and_person_scope(
        actor=actor,
        person=assignment.person,
        bed=destination_bed,
        valid_from=effective_on,
        allow_planned_arrival=effective_on > today,
    )
    errors = _assignment_conflicts(
        person=assignment.person,
        bed=destination_bed,
        valid_from=effective_on,
        valid_until=old_until,
        exclude_ids=(assignment.pk,),
    )
    if errors:
        if "bed" in errors:
            errors["destination_bed"] = errors.pop("bed")
        raise ValidationError(errors)

    destination = HousingAssignment(
        person=assignment.person,
        bed=destination_bed,
        valid_from=effective_on,
        valid_until=old_until,
        reservation_expires_at=assignment.reservation_expires_at,
        notes="",
        created_by=actor,
        modified_by=actor,
        is_active=True,
    )
    if same_start_reservation:
        assignment.is_active = False
        assignment.modified_by = actor
        assignment.save(
            housing_transition=True,
            update_fields=("is_active", "modified_by"),
        )
    else:
        assignment.valid_until = effective_on - timedelta(days=1)
        assignment.modified_by = actor
        assignment.full_clean(validate_constraints=False)
        assignment.save(
            housing_transition=True,
            update_fields=("valid_until", "modified_by"),
        )

    destination.full_clean(validate_constraints=False)
    destination.save()
    _record_assignment_event(
        assignment=assignment,
        related_assignment=destination,
        action=HousingAssignmentEvent.Action.MOVED_OUT,
        actor=actor,
        effective_on=effective_on,
        scheduled_until=old_until,
        reason=reason,
    )
    _record_assignment_event(
        assignment=destination,
        related_assignment=assignment,
        action=HousingAssignmentEvent.Action.MOVED_IN,
        actor=actor,
        effective_on=effective_on,
        scheduled_until=old_until,
        reason=reason,
    )
    return destination
