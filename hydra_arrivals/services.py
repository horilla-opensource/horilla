from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from hydra_arrivals.models import ArrivalPlan, ArrivalStatusHistory
from hydra_arrivals.selectors import (
    ARRIVAL_VIEW_PERMISSIONS,
    arrival_locations_for_user,
    arrival_plans_for_user,
)
from hydra_people.models import Person
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import people_for_user
from recruitment.models import Candidate


def _require_permissions(actor, *permissions):
    required = ARRIVAL_VIEW_PERMISSIONS + permissions
    if not actor.is_authenticated or not actor.has_perms(required):
        raise PermissionDenied


def _validate_destination(*, actor, location):
    if not arrival_locations_for_user(user=actor).filter(pk=location.pk).exists():
        raise PermissionDenied


def _validate_coordinator(*, coordinator, location):
    required = ARRIVAL_VIEW_PERMISSIONS + (
        "hydra_arrivals.transition_arrivalplan",
    )
    if not coordinator.is_active or not coordinator.has_perms(required):
        raise ValidationError(
            {"coordinator": _("The coordinator lacks required permissions.")}
        )
    if not arrival_locations_for_user(user=coordinator).filter(pk=location.pk).exists():
        raise ValidationError(
            {"coordinator": _("The coordinator cannot access this location.")}
        )


def _validate_subject(*, plan, actor, require_person_scope):
    if require_person_scope and not people_for_user(user=actor).filter(
        pk=plan.person_id
    ).exists():
        raise PermissionDenied

    if require_person_scope and not linked_candidates_for_user(user=actor).filter(
        pk=plan.candidate_id,
        hydra_person_link__person_id=plan.person_id,
    ).exists():
        raise PermissionDenied

    plan.full_clean(validate_constraints=False)


def _validate_assignment_change(*, actor, coordinator_id, current_id=None):
    changed = current_id is None or coordinator_id != current_id
    if (
        changed
        and coordinator_id != actor.pk
        and not actor.has_perm("hydra_arrivals.assign_arrivalplan")
    ):
        raise PermissionDenied


@transaction.atomic
def create_arrival_plan(*, plan: ArrivalPlan, actor) -> ArrivalPlan:
    _require_permissions(actor, "hydra_arrivals.add_arrivalplan")
    if not plan._state.adding:
        raise ValidationError(_("A new arrival plan was expected."))
    if plan.planned_at <= timezone.now():
        raise ValidationError({"planned_at": _("Plan an arrival in the future.")})

    plan.person = Person.objects.select_for_update().get(pk=plan.person_id)
    plan.candidate = Candidate._base_manager.select_for_update().get(
        pk=plan.candidate_id
    )
    _validate_destination(actor=actor, location=plan.destination_location)
    _validate_assignment_change(actor=actor, coordinator_id=plan.coordinator_id)
    _validate_coordinator(
        coordinator=plan.coordinator,
        location=plan.destination_location,
    )
    _validate_subject(plan=plan, actor=actor, require_person_scope=True)

    if ArrivalPlan.objects.select_for_update().filter(
        candidate=plan.candidate,
        status=ArrivalPlan.Status.PLANNED,
    ).exists():
        raise ValidationError(
            {"candidate": _("This application already has a planned arrival.")}
        )

    plan.status = ArrivalPlan.Status.PLANNED
    plan.actual_arrived_at = None
    plan.no_show_reason = ""
    plan.created_by = actor
    plan.modified_by = actor
    plan.save()
    ArrivalStatusHistory.objects.create(
        plan=plan,
        from_status="",
        to_status=ArrivalPlan.Status.PLANNED,
        actor=actor,
    )
    return plan


@transaction.atomic
def update_arrival_plan(*, plan: ArrivalPlan, actor) -> ArrivalPlan:
    _require_permissions(actor, "hydra_arrivals.change_arrivalplan")
    if plan._state.adding:
        raise ValidationError(_("An existing arrival plan was expected."))

    current = ArrivalPlan.objects.select_for_update().get(pk=plan.pk)
    if not arrival_plans_for_user(user=actor).filter(pk=current.pk).exists():
        raise PermissionDenied
    if current.status != ArrivalPlan.Status.PLANNED:
        raise ValidationError(_("A completed arrival plan cannot be edited."))
    if (
        current.coordinator_id != actor.pk
        and not actor.has_perm("hydra_arrivals.assign_arrivalplan")
    ):
        raise PermissionDenied
    if plan.person_id != current.person_id or plan.candidate_id != current.candidate_id:
        raise ValidationError(_("Person and application cannot be changed."))
    if plan.planned_at <= timezone.now():
        raise ValidationError({"planned_at": _("Plan an arrival in the future.")})

    _validate_destination(actor=actor, location=plan.destination_location)
    _validate_assignment_change(
        actor=actor,
        coordinator_id=plan.coordinator_id,
        current_id=current.coordinator_id,
    )
    _validate_coordinator(
        coordinator=plan.coordinator,
        location=plan.destination_location,
    )
    plan.status = current.status
    plan.actual_arrived_at = current.actual_arrived_at
    plan.no_show_reason = current.no_show_reason
    _validate_subject(plan=plan, actor=actor, require_person_scope=False)
    plan.created_by = current.created_by
    plan.modified_by = actor
    plan.save()
    return plan


@transaction.atomic
def transition_arrival_plan(
    *, plan_uuid, target_status, actor, actual_arrived_at=None, reason=""
) -> ArrivalPlan:
    _require_permissions(actor, "hydra_arrivals.transition_arrivalplan")
    if target_status not in {
        ArrivalPlan.Status.CONFIRMED,
        ArrivalPlan.Status.NO_SHOW,
    }:
        raise ValidationError({"target_status": _("Choose a valid arrival outcome.")})

    plan = ArrivalPlan.objects.select_for_update().get(uuid=plan_uuid)
    if not arrival_plans_for_user(user=actor).filter(pk=plan.pk).exists():
        raise PermissionDenied
    if plan.status == target_status:
        return plan
    if plan.status != ArrivalPlan.Status.PLANNED:
        raise ValidationError(_("This arrival already has a different outcome."))
    if (
        plan.coordinator_id != actor.pk
        and not actor.has_perm("hydra_arrivals.assign_arrivalplan")
    ):
        raise PermissionDenied

    now = timezone.now()
    reason = " ".join(reason.split())
    if target_status == ArrivalPlan.Status.CONFIRMED:
        actual_arrived_at = actual_arrived_at or now
        if actual_arrived_at > now + timedelta(minutes=5):
            raise ValidationError(
                {"actual_arrived_at": _("Actual arrival time cannot be in the future.")}
            )
        plan.actual_arrived_at = actual_arrived_at
        plan.no_show_reason = ""
    else:
        if now < plan.planned_at:
            raise ValidationError(
                {"target_status": _("No-show cannot be recorded before the planned time.")}
            )
        if not reason:
            raise ValidationError({"reason": _("No-show requires a reason.")})
        plan.actual_arrived_at = None
        plan.no_show_reason = reason

    previous = plan.status
    plan.status = target_status
    plan.modified_by = actor
    plan.full_clean()
    plan.save(
        update_fields=(
            "status",
            "actual_arrived_at",
            "no_show_reason",
            "modified_by",
        )
    )
    ArrivalStatusHistory.objects.create(
        plan=plan,
        from_status=previous,
        to_status=target_status,
        actor=actor,
        reason=reason,
    )
    return plan
