from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from hydra_tasks.models import TaskTargetKind


@dataclass(frozen=True, slots=True)
class TaskTarget:
    kind: str
    uuid: UUID
    label: str
    url: str

    @property
    def value(self):
        return f"{self.kind}:{self.uuid}"


def parse_target_reference(value) -> tuple[str, UUID]:
    try:
        kind, raw_uuid = str(value).split(":", 1)
        target_uuid = UUID(raw_uuid)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValidationError(_("Select a valid task target.")) from error
    if kind not in TaskTargetKind.values:
        raise ValidationError(_("This task target type is not approved."))
    return kind, target_uuid


def _person_target(*, person):
    return TaskTarget(
        kind=TaskTargetKind.PERSON,
        uuid=person.uuid,
        label=str(person.hydra_id),
        url=person.get_absolute_url(),
    )


def _legalization_target(case):
    identifier = case.reference_number or str(case.uuid)[:8]
    return TaskTarget(
        kind=TaskTargetKind.LEGALIZATION_CASE,
        uuid=case.uuid,
        label=f"Legalization / {identifier}",
        url=case.get_absolute_url(),
    )


def _arrival_target(plan):
    return TaskTarget(
        kind=TaskTargetKind.ARRIVAL_PLAN,
        uuid=plan.uuid,
        label=(
            f"Arrival / {plan.planned_at:%Y-%m-%d %H:%M} / "
            f"{plan.destination_location.name}"
        ),
        url=plan.get_absolute_url(),
    )


def _housing_target(assignment):
    bed = assignment.bed
    return TaskTarget(
        kind=TaskTargetKind.HOUSING_ASSIGNMENT,
        uuid=assignment.uuid,
        label=(
            f"Housing / {bed.room.facility.name} / {bed.room.name} / {bed.label}"
        ),
        url=assignment.person.get_absolute_url(),
    )


def _handoff_target(handoff):
    return TaskTarget(
        kind=TaskTargetKind.ONBOARDING_HANDOFF,
        uuid=handoff.uuid,
        label=f"Onboarding / {str(handoff.uuid)[:8]}",
        url=handoff.get_absolute_url(),
    )


def targets_for_user(*, user, person, company) -> list[TaskTarget]:
    """Return only approved domain objects visible at their authoritative source."""

    targets = [_person_target(person=person)]

    from hydra_arrivals.models import OnboardingHandoff
    from hydra_arrivals.selectors import arrival_plans_for_user
    from hydra_housing.selectors import housing_assignments_for_user
    from hydra_legalization.selectors import legalization_cases_for_user

    legal_cases = legalization_cases_for_user(user=user).filter(
        person=person,
        company=company,
    ).order_by("-pk")[:100]
    targets.extend(_legalization_target(case) for case in legal_cases)

    arrival_plans = arrival_plans_for_user(user=user).filter(
        person=person,
        destination_location__company=company,
    ).order_by("-pk")[:100]
    arrival_ids = []
    for plan in arrival_plans:
        arrival_ids.append(plan.pk)
        targets.append(_arrival_target(plan))

    assignments = housing_assignments_for_user(user=user).filter(
        person=person,
        bed__room__facility__location__company=company,
    )[:100]
    targets.extend(_housing_target(assignment) for assignment in assignments)

    if user.has_perm("hydra_arrivals.view_onboardinghandoff") and arrival_ids:
        handoffs = (
            OnboardingHandoff.objects.filter(
                person=person,
                arrival_id__in=arrival_ids,
            )
            .select_related("arrival__destination_location", "person")[:100]
        )
        targets.extend(_handoff_target(handoff) for handoff in handoffs)

    return targets


def resolve_target_for_user(*, user, person, company, target_reference) -> TaskTarget:
    kind, target_uuid = parse_target_reference(target_reference)
    if kind == TaskTargetKind.PERSON:
        if target_uuid == person.uuid:
            return _person_target(person=person)
    elif kind == TaskTargetKind.LEGALIZATION_CASE:
        from hydra_legalization.selectors import legalization_cases_for_user

        case = legalization_cases_for_user(user=user).filter(
            uuid=target_uuid,
            person=person,
            company=company,
        ).first()
        if case is not None:
            return _legalization_target(case)
    elif kind == TaskTargetKind.ARRIVAL_PLAN:
        from hydra_arrivals.selectors import arrival_plans_for_user

        plan = arrival_plans_for_user(user=user).filter(
            uuid=target_uuid,
            person=person,
            destination_location__company=company,
        ).first()
        if plan is not None:
            return _arrival_target(plan)
    elif kind == TaskTargetKind.HOUSING_ASSIGNMENT:
        from hydra_housing.selectors import housing_assignments_for_user

        assignment = housing_assignments_for_user(user=user).filter(
            uuid=target_uuid,
            person=person,
            bed__room__facility__location__company=company,
        ).first()
        if assignment is not None:
            return _housing_target(assignment)
    elif kind == TaskTargetKind.ONBOARDING_HANDOFF:
        from hydra_arrivals.models import OnboardingHandoff
        from hydra_arrivals.selectors import arrival_plans_for_user

        if user.has_perm("hydra_arrivals.view_onboardinghandoff"):
            handoff = OnboardingHandoff.objects.filter(
                uuid=target_uuid,
                person=person,
                arrival__in=arrival_plans_for_user(user=user),
                arrival__destination_location__company=company,
            ).first()
            if handoff is not None:
                return _handoff_target(handoff)
    raise ValidationError(_("The task target is outside your current scope."))


def stored_target_is_valid(task) -> bool:
    """Check persisted target integrity without using a user's permissions."""

    if task.target_kind == TaskTargetKind.PERSON:
        return task.target_uuid == task.person.uuid

    if task.target_kind == TaskTargetKind.LEGALIZATION_CASE:
        from hydra_legalization.models import LegalizationCase

        return LegalizationCase._base_manager.filter(
            uuid=task.target_uuid,
            person=task.person,
            company=task.company,
        ).exists()
    if task.target_kind == TaskTargetKind.ARRIVAL_PLAN:
        from hydra_arrivals.models import ArrivalPlan

        return ArrivalPlan._base_manager.filter(
            uuid=task.target_uuid,
            person=task.person,
            destination_location__company=task.company,
        ).exists()
    if task.target_kind == TaskTargetKind.HOUSING_ASSIGNMENT:
        from hydra_housing.models import HousingAssignment

        return HousingAssignment._base_manager.filter(
            uuid=task.target_uuid,
            person=task.person,
            bed__room__facility__location__company=task.company,
        ).exists()
    if task.target_kind == TaskTargetKind.ONBOARDING_HANDOFF:
        from hydra_arrivals.models import OnboardingHandoff

        return OnboardingHandoff.objects.filter(
            uuid=task.target_uuid,
            person=task.person,
            arrival__destination_location__company=task.company,
        ).exists()
    return False


def target_url_for_user(*, user, task) -> str:
    try:
        target = resolve_target_for_user(
            user=user,
            person=task.person,
            company=task.company,
            target_reference=f"{task.target_kind}:{task.target_uuid}",
        )
    except ValidationError:
        return ""
    return target.url
