from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from hydra_arrivals.models import (
    ArrivalPlan,
    OnboardingHandoff,
    OnboardingHandoffEvent,
)
from hydra_arrivals.selectors import (
    ARRIVAL_VIEW_PERMISSIONS,
    arrival_plans_for_user,
)
from hydra_coordination.models import PersonAssignment
from hydra_people.models import EmployeeConversion, Person, PersonApplication
from hydra_notifications.models import NotificationKind, NotificationTargetKind
from hydra_notifications.services import send_hydra_notification
from onboarding.models import CandidateTask, OnboardingTask
from onboarding.services import ensure_candidate_onboarding
from recruitment.models import Candidate


User = get_user_model()

HANDOFF_START_PERMISSIONS = ARRIVAL_VIEW_PERMISSIONS + (
    "hydra_arrivals.view_onboardinghandoff",
    "hydra_arrivals.initiate_onboardinghandoff",
    "hydra_people.change_person",
    "recruitment.change_candidate",
    "onboarding.view_onboardingstage",
    "onboarding.view_onboardingtask",
    "onboarding.view_candidatestage",
    "onboarding.view_candidatetask",
    "onboarding.add_candidatestage",
    "onboarding.add_candidatetask",
)

HANDOFF_RECONCILE_PERMISSIONS = ARRIVAL_VIEW_PERMISSIONS + (
    "hydra_arrivals.view_onboardinghandoff",
    "hydra_arrivals.reconcile_onboardinghandoff",
)

HANDOFF_TASK_UPDATE_PERMISSIONS = ARRIVAL_VIEW_PERMISSIONS + (
    "hydra_arrivals.view_onboardinghandoff",
    "onboarding.view_candidatetask",
    "onboarding.change_candidatetask",
)


@dataclass(frozen=True)
class HandoffReconciliationResult:
    handoffs_selected: int
    handoffs_updated: int
    handoffs_completed: int


def _require_permissions(actor, permissions):
    if not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def _event_source(actor):
    if actor is None:
        return OnboardingHandoffEvent.Source.SYSTEM, None
    return OnboardingHandoffEvent.Source.USER, actor


def _snapshot(handoff):
    task_counts = CandidateTask._base_manager.filter(
        candidate_id=handoff.candidate_id
    ).aggregate(
        total=Count("pk"),
        completed=Count("pk", filter=Q(status="done")),
    )
    return {
        "handoff_id": handoff.pk,
        "arrival_id": handoff.arrival_id,
        "person_id": handoff.person_id,
        "candidate_id": handoff.candidate_id,
        "candidate_stage_id": handoff.candidate_stage_id,
        "employee_conversion_id": handoff.employee_conversion_id,
        "person_assignment_id": handoff.person_assignment_id,
        "status": handoff.status,
        "task_count": task_counts["total"],
        "completed_task_count": task_counts["completed"],
    }


def _record_event(*, handoff, event_type, actor, conversion=None, assignment=None):
    if OnboardingHandoffEvent.objects.filter(
        handoff=handoff,
        event_type=event_type,
    ).exists():
        return False
    source, event_actor = _event_source(actor)
    event = OnboardingHandoffEvent(
        handoff=handoff,
        event_type=event_type,
        source=source,
        actor=event_actor,
        employee_conversion=conversion,
        person_assignment=assignment,
        snapshot=_snapshot(handoff),
    )
    event.full_clean()
    event.save(force_insert=True)
    return True


def _current_destination_assignment(*, handoff, day):
    return (
        PersonAssignment.objects.select_for_update(of=("self",))
        .select_related("team__section__location")
        .filter(
            person_id=handoff.person_id,
            team__section__location_id=handoff.arrival.destination_location_id,
            is_primary=True,
            is_active=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .order_by("-valid_from", "-pk")
        .first()
    )


@transaction.atomic
def reconcile_onboarding_handoff(*, handoff, actor=None, authorize=False):
    if authorize:
        if actor is None:
            raise PermissionDenied
        _require_permissions(actor, HANDOFF_RECONCILE_PERMISSIONS)
        if not arrival_plans_for_user(user=actor).filter(
            pk=handoff.arrival_id
        ).exists():
            raise PermissionDenied

    locked = (
        OnboardingHandoff.objects.select_for_update(of=("self",))
        .select_related(
            "arrival",
            "arrival__destination_location",
            "candidate",
            "candidate_stage__onboarding_stage_id",
            "employee_conversion",
            "person_assignment__team__section__location",
        )
        .get(pk=handoff.pk)
    )
    previous_status = locked.status

    if locked.employee_conversion_id is None:
        conversion = EmployeeConversion.objects.filter(
            person_id=locked.person_id,
            candidate_id=locked.candidate_id,
        ).first()
        if conversion is None:
            conversion = EmployeeConversion.objects.filter(
                person_id=locked.person_id,
            ).first()
        if conversion is not None:
            locked.employee_conversion = conversion
            locked.status = OnboardingHandoff.Status.CONVERTED
            _record_event(
                handoff=locked,
                event_type=OnboardingHandoffEvent.EventType.CONVERSION_RECORDED,
                actor=actor,
                conversion=conversion,
            )

    if locked.employee_conversion_id and locked.person_assignment_id is None:
        assignment = _current_destination_assignment(
            handoff=locked,
            day=timezone.localdate(),
        )
        if assignment is not None:
            locked.person_assignment = assignment
            _record_event(
                handoff=locked,
                event_type=OnboardingHandoffEvent.EventType.ASSIGNMENT_RECORDED,
                actor=actor,
                conversion=locked.employee_conversion,
                assignment=assignment,
            )

    incomplete_tasks_exist = CandidateTask._base_manager.filter(
        candidate_id=locked.candidate_id
    ).exclude(status="done").exists()
    if locked.employee_conversion_id and locked.person_assignment_id:
        if incomplete_tasks_exist:
            locked.status = OnboardingHandoff.Status.ASSIGNED
            locked.completed_at = None
        else:
            locked.status = OnboardingHandoff.Status.COMPLETED
            if locked.completed_at is None:
                locked.completed_at = timezone.now()
    elif locked.employee_conversion_id:
        locked.status = OnboardingHandoff.Status.CONVERTED
        locked.completed_at = None
    else:
        locked.status = OnboardingHandoff.Status.STARTED
        locked.completed_at = None

    locked.last_reconciled_at = timezone.now()
    locked.full_clean()
    locked.save(
        update_fields=(
            "employee_conversion",
            "person_assignment",
            "status",
            "last_reconciled_at",
            "completed_at",
        )
    )
    if (
        locked.status == OnboardingHandoff.Status.COMPLETED
        and previous_status != OnboardingHandoff.Status.COMPLETED
    ):
        _record_event(
            handoff=locked,
            event_type=OnboardingHandoffEvent.EventType.COMPLETED,
            actor=actor,
            conversion=locked.employee_conversion,
            assignment=locked.person_assignment,
        )
    from hydra_onboarding.services import apply_course_rules_for_person

    apply_course_rules_for_person(person=locked.person, handoff=locked)
    return locked


def _eligible_manager_users(*, candidate, arrival):
    employee_ids = set()
    candidate_stage = candidate.onboarding_stage
    employee_ids.update(candidate_stage.onboarding_stage_id.employee_id.values_list("pk", flat=True))
    employee_ids.update(
        OnboardingTask._base_manager.filter(
            stage_id__recruitment_id=candidate.recruitment_id_id
        ).values_list("employee_id", flat=True)
    )
    user_ids = User.objects.filter(
        employee_get__pk__in=employee_ids,
        is_active=True,
    ).values_list("pk", flat=True)
    recipients = []
    for recipient in User.objects.filter(pk__in=user_ids).order_by("pk"):
        if not recipient.has_perm("hydra_arrivals.view_onboardinghandoff"):
            continue
        if arrival_plans_for_user(user=recipient).filter(pk=arrival.pk).exists():
            recipients.append(recipient)
    return recipients


@transaction.atomic
def start_onboarding_handoff(*, plan_uuid, actor):
    _require_permissions(actor, HANDOFF_START_PERMISSIONS)
    if not arrival_plans_for_user(user=actor).filter(uuid=plan_uuid).exists():
        raise PermissionDenied

    arrival = (
        ArrivalPlan.objects.select_for_update(of=("self",))
        .select_related(
            "person",
            "candidate__recruitment_id",
            "destination_location",
        )
        .get(uuid=plan_uuid)
    )
    existing = OnboardingHandoff.objects.select_for_update().filter(
        arrival=arrival
    ).first()
    if existing is not None:
        return reconcile_onboarding_handoff(handoff=existing, actor=actor)

    person = Person.objects.select_for_update().get(pk=arrival.person_id)
    candidate = (
        Candidate._base_manager.select_for_update(of=("self",))
        .select_related("recruitment_id")
        .get(pk=arrival.candidate_id)
    )
    if arrival.status != ArrivalPlan.Status.CONFIRMED:
        raise ValidationError(
            {"arrival": _("Confirm the arrival before starting onboarding.")}
        )
    if not candidate.is_active or candidate.canceled:
        raise ValidationError(
            {"candidate": _("Only an active application can enter onboarding.")}
        )
    if not candidate.hired:
        raise ValidationError(
            {"candidate": _("Mark the application as hired before onboarding.")}
        )
    if person.lifecycle_state == Person.LifecycleState.INACTIVE:
        raise ValidationError(
            {"person": _("An inactive Person cannot enter onboarding.")}
        )
    try:
        linked_person_id = candidate.hydra_person_link.person_id
    except PersonApplication.DoesNotExist as error:
        raise ValidationError(
            {"candidate": _("The application must be linked to a Hydra Person.")}
        ) from error
    if linked_person_id != person.pk:
        raise ValidationError(
            {"candidate": _("The application belongs to another Person.")}
        )

    lifecycle_before = person.lifecycle_state
    candidate_stage, created_tasks = ensure_candidate_onboarding(
        candidate=candidate,
        actor=actor,
    )
    if person.lifecycle_state != Person.LifecycleState.EMPLOYEE:
        person.lifecycle_state = Person.LifecycleState.ONBOARDING
        person.modified_by = actor
        person.save(update_fields=("lifecycle_state", "modified_by"))

    task_count = CandidateTask._base_manager.filter(candidate_id=candidate).count()
    handoff = OnboardingHandoff(
        arrival=arrival,
        person=person,
        candidate=candidate,
        candidate_stage=candidate_stage,
        initiated_by=actor,
        started_snapshot={
            "arrival_status": arrival.status,
            "actual_arrived_at": arrival.actual_arrived_at.isoformat(),
            "destination_location_id": arrival.destination_location_id,
            "recruitment_id": candidate.recruitment_id_id,
            "candidate_hired": candidate.hired,
            "person_lifecycle_before": lifecycle_before,
            "candidate_stage_id": candidate_stage.pk,
            "task_count": task_count,
            "tasks_created": len(created_tasks),
        },
    )
    handoff.full_clean()
    handoff.save(force_insert=True)
    _record_event(
        handoff=handoff,
        event_type=OnboardingHandoffEvent.EventType.STARTED,
        actor=actor,
    )

    for recipient in _eligible_manager_users(candidate=candidate, arrival=arrival):
        send_hydra_notification(
            actor=handoff,
            recipient=recipient,
            kind=NotificationKind.ONBOARDING_READY,
            target_kind=NotificationTargetKind.ONBOARDING_HANDOFF,
            target_uuid=handoff.uuid,
            redirect_path=reverse("hydra-arrival-detail", args=(arrival.uuid,)),
            idempotency_key=f"onboarding-ready:{handoff.uuid}:{recipient.pk}",
        )

    return reconcile_onboarding_handoff(handoff=handoff, actor=actor)


@transaction.atomic
def update_onboarding_task_status(*, handoff, candidate_task_id, status, actor):
    _require_permissions(actor, HANDOFF_TASK_UPDATE_PERMISSIONS)
    if not arrival_plans_for_user(user=actor).filter(
        pk=handoff.arrival_id
    ).exists():
        raise PermissionDenied

    locked = (
        OnboardingHandoff.objects.select_for_update(of=("self",))
        .select_related("arrival", "candidate", "candidate_stage__onboarding_stage_id")
        .get(pk=handoff.pk)
    )
    if locked.status == OnboardingHandoff.Status.COMPLETED:
        raise ValidationError(
            {"status": _("A completed onboarding handoff cannot be changed.")}
        )
    valid_statuses = {value for value, _label in CandidateTask.choice}
    if status not in valid_statuses:
        raise ValidationError({"status": _("Choose a valid onboarding task status.")})

    candidate_task = (
        CandidateTask._base_manager.select_for_update(of=("self",))
        .select_related("onboarding_task_id", "stage_id")
        .get(pk=candidate_task_id)
    )
    if candidate_task.candidate_id_id != locked.candidate_id:
        raise PermissionDenied

    if not actor.is_superuser:
        try:
            employee_id = actor.employee_get.pk
        except ObjectDoesNotExist as error:
            raise PermissionDenied from error
        is_task_manager = candidate_task.onboarding_task_id.employee_id.filter(
            pk=employee_id
        ).exists()
        is_stage_manager = locked.candidate_stage.onboarding_stage_id.employee_id.filter(
            pk=employee_id
        ).exists()
        if not (is_task_manager or is_stage_manager):
            raise PermissionDenied

    if candidate_task.status != status:
        candidate_task.status = status
        candidate_task.save(update_fields=("status",))
        history_id = (
            candidate_task.history.order_by("-history_date", "-history_id")
            .values_list("history_id", flat=True)
            .first()
        )
        for recipient in _eligible_manager_users(
            candidate=locked.candidate,
            arrival=locked.arrival,
        ):
            send_hydra_notification(
                actor=actor,
                recipient=recipient,
                kind=NotificationKind.ONBOARDING_TASK_CHANGED,
                target_kind=NotificationTargetKind.ONBOARDING_HANDOFF,
                target_uuid=locked.uuid,
                redirect_path=reverse(
                    "hydra-arrival-detail",
                    args=(locked.arrival.uuid,),
                ),
                idempotency_key=(
                    f"onboarding-task:{locked.uuid}:{candidate_task.pk}:"
                    f"{history_id}:{recipient.pk}"
                ),
            )
    reconciled = reconcile_onboarding_handoff(handoff=locked, actor=actor)
    candidate_task.refresh_from_db()
    return candidate_task, reconciled


def reconcile_person_onboarding_handoff(*, person, actor=None):
    handoffs = OnboardingHandoff.objects.filter(person=person).exclude(
        status=OnboardingHandoff.Status.COMPLETED
    )
    return tuple(
        reconcile_onboarding_handoff(handoff=handoff, actor=actor)
        for handoff in handoffs.order_by("pk")
    )


@transaction.atomic
def reconcile_open_onboarding_handoffs(*, batch_size=200):
    try:
        batch_size = int(batch_size)
    except (TypeError, ValueError) as error:
        raise ValidationError({"batch_size": _("Use a positive batch size.")}) from error
    if batch_size <= 0:
        raise ValidationError({"batch_size": _("Use a positive batch size.")})

    handoffs = list(
        OnboardingHandoff.objects.select_for_update(skip_locked=True)
        .exclude(status=OnboardingHandoff.Status.COMPLETED)
        .order_by("last_reconciled_at", "pk")[:batch_size]
    )
    updated = 0
    completed = 0
    for handoff in handoffs:
        before = (
            handoff.status,
            handoff.employee_conversion_id,
            handoff.person_assignment_id,
        )
        result = reconcile_onboarding_handoff(handoff=handoff)
        after = (
            result.status,
            result.employee_conversion_id,
            result.person_assignment_id,
        )
        if after != before:
            updated += 1
        if result.status == OnboardingHandoff.Status.COMPLETED:
            completed += 1
    return HandoffReconciliationResult(
        handoffs_selected=len(handoffs),
        handoffs_updated=updated,
        handoffs_completed=completed,
    )
