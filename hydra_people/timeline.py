"""Scope-aware Person timeline composed from authoritative append-only facts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from hydra_people.models import (
    CandidateStageTransition,
    EmployeeConversion,
    Person,
    PersonApplication,
    PersonMergeEvent,
)
from hydra_people.selectors import people_for_user


MAX_TIMELINE_ITEMS = 200


@dataclass(frozen=True, slots=True)
class TimelineItem:
    """A safe display projection; source records remain authoritative."""

    source_key: str
    occurred_at: datetime
    category: str
    category_label: Any
    label: Any
    detail: Any = ""
    actor: Any = None


def _bounded_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 100
    return max(1, min(value, MAX_TIMELINE_ITEMS))


def _transition_detail(*, choices, from_value, to_value):
    labels = dict(choices)
    from_label = labels.get(from_value, from_value) if from_value else _("Initial")
    to_label = labels.get(to_value, to_value)
    return format_lazy("{} → {}", from_label, to_label)


def _person_audit_items(*, person, limit):
    content_type = ContentType.objects.get_for_model(
        Person,
        for_concrete_model=False,
    )
    labels = {
        LogEntry.Action.CREATE: _("Person record created"),
        LogEntry.Action.UPDATE: _("Person record updated"),
    }
    entries = (
        LogEntry.objects.filter(
            content_type=content_type,
            object_pk=str(person.pk),
            action__in=labels,
        )
        .select_related("actor")
        .order_by("-timestamp", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"auditlog.logentry:{entry.pk}",
            occurred_at=entry.timestamp,
            category="person",
            category_label=_("Person"),
            label=labels[entry.action],
            actor=entry.actor,
        )
        for entry in entries
    ]


def _visible_candidates(*, user, person):
    from hydra_coordination.selectors import company_ids_for_user
    from recruitment.models import Candidate

    if not user.has_perm("recruitment.view_candidate"):
        return Candidate._base_manager.none()
    return Candidate._base_manager.filter(
        hydra_person_link__person=person,
        recruitment_id__company_id_id__in=company_ids_for_user(user=user),
    ).distinct()


def _application_items(*, person, limit, visible_candidates):
    links = (
        PersonApplication.objects.filter(
            person=person,
            candidate__in=visible_candidates,
            created_at__isnull=False,
        )
        .select_related("created_by", "candidate__recruitment_id")
        .order_by("-created_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_people.personapplication:{link.pk}",
            occurred_at=link.created_at,
            category="recruitment",
            category_label=_("Recruitment"),
            label=_("Recruitment application linked"),
            detail=link.candidate.recruitment_id.title,
            actor=link.created_by,
        )
        for link in links
    ]


def _recruitment_transition_items(*, user, limit, visible_candidates):
    if not user.has_perm("hydra_people.view_candidatestagetransition"):
        return []
    transitions = (
        CandidateStageTransition.objects.filter(candidate__in=visible_candidates)
        .select_related("actor", "from_stage", "to_stage")
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_people.candidatestagetransition:{transition.pk}",
            occurred_at=transition.occurred_at,
            category="recruitment",
            category_label=_("Recruitment"),
            label=_("Recruitment stage changed"),
            detail=format_lazy(
                "{} в†’ {}",
                transition.from_stage.stage,
                transition.to_stage.stage,
            ),
            actor=transition.actor,
        )
        for transition in transitions
    ]


def _conversion_items(*, user, person):
    if not user.has_perm("hydra_people.view_employeeconversion"):
        return []
    conversion = (
        EmployeeConversion.objects.select_related("actor")
        .filter(person=person)
        .first()
    )
    if conversion is None:
        return []
    return [
        TimelineItem(
            source_key=f"hydra_people.employeeconversion:{conversion.pk}",
            occurred_at=conversion.occurred_at,
            category="employment",
            category_label=_("Employment"),
            label=_("Employee conversion recorded"),
            detail=conversion.get_source_display(),
            actor=conversion.actor,
        )
    ]


def _merge_items(*, user, person, limit):
    if not user.has_perm("hydra_people.view_personmergeevent"):
        return []
    events = (
        PersonMergeEvent.objects.filter(survivor=person)
        .select_related("actor", "duplicate")
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_people.personmergeevent:{event.uuid}",
            occurred_at=event.occurred_at,
            category="identity",
            category_label=_("Identity"),
            label=_("Duplicate Person merged"),
            detail=event.duplicate.hydra_id,
            actor=event.actor,
        )
        for event in events
    ]


def _organization_items(*, user, person, limit):
    from hydra_coordination.models import OrganizationAccessEvent, PersonAssignment
    from hydra_coordination.selectors import teams_for_user

    if not user.has_perm("hydra_coordination.view_personassignment"):
        return []
    assignments = (
        PersonAssignment.objects.filter(
            person=person,
            team__in=teams_for_user(user=user),
            created_at__isnull=False,
        )
        .select_related("created_by", "team")
        .order_by("-created_at", "-pk")
    )
    assignment_items = [
        TimelineItem(
            source_key=f"hydra_coordination.personassignment:{assignment.pk}",
            occurred_at=assignment.created_at,
            category="organization",
            category_label=_("Organization"),
            label=_("Organization assignment recorded"),
            detail=assignment.team.name,
            actor=assignment.created_by,
        )
        for assignment in assignments[:limit]
    ]
    if not user.has_perm("hydra_coordination.view_organizationaccessevent"):
        return assignment_items
    events = (
        OrganizationAccessEvent.objects.filter(person_assignment__in=assignments)
        .select_related("actor")
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return assignment_items + [
        TimelineItem(
            source_key=f"hydra_coordination.organizationaccessevent:{event.uuid}",
            occurred_at=event.occurred_at,
            category="organization",
            category_label=_("Organization"),
            label=event.get_action_display(),
            actor=event.actor,
        )
        for event in events
    ]


def _arrival_items(*, user, person, limit):
    from hydra_arrivals.models import (
        ArrivalPlan,
        ArrivalStatusHistory,
        OnboardingHandoffEvent,
    )
    from hydra_arrivals.selectors import arrival_plans_for_user

    plans = arrival_plans_for_user(user=user).filter(person=person)
    items = []
    if user.has_perm("hydra_arrivals.view_arrivalstatushistory"):
        histories = (
            ArrivalStatusHistory.objects.filter(plan__in=plans)
            .select_related("actor")
            .order_by("-occurred_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_arrivals.arrivalstatushistory:{history.pk}",
                occurred_at=history.occurred_at,
                category="arrival",
                category_label=_("Arrival"),
                label=_("Arrival status changed"),
                detail=_transition_detail(
                    choices=ArrivalPlan.Status.choices,
                    from_value=history.from_status,
                    to_value=history.to_status,
                ),
                actor=history.actor,
            )
            for history in histories
        )
    if user.has_perms(
        (
            "hydra_arrivals.view_onboardinghandoff",
            "hydra_arrivals.view_onboardinghandoffevent",
        )
    ):
        events = (
            OnboardingHandoffEvent.objects.filter(handoff__arrival__in=plans)
            .select_related("actor")
            .order_by("-occurred_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_arrivals.onboardinghandoffevent:{event.pk}",
                occurred_at=event.occurred_at,
                category="onboarding",
                category_label=_("Onboarding"),
                label=event.get_event_type_display(),
                actor=event.actor,
            )
            for event in events
        )
    return items


def _housing_items(*, user, person, limit):
    from hydra_housing.selectors import housing_assignment_events_for_user

    events = (
        housing_assignment_events_for_user(user=user)
        .filter(assignment__person=person)
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_housing.housingassignmentevent:{event.uuid}",
            occurred_at=event.occurred_at,
            category="housing",
            category_label=_("Housing"),
            label=event.get_action_display(),
            detail=event.assignment.bed.label,
            actor=event.actor,
        )
        for event in events
    ]


def _legalization_items(*, user, person, limit):
    from hydra_legalization.models import (
        LegalizationAuthorityEvent,
        LegalizationCase,
        LegalizationRenewalLink,
        LegalizationStatusHistory,
        LegalizationWorkEvent,
    )

    if not user.has_perm("hydra_legalization.view_legalizationcase"):
        return []
    cases = LegalizationCase.objects.filter(person=person)
    items = []
    if user.has_perm("hydra_legalization.view_legalizationstatushistory"):
        histories = (
            LegalizationStatusHistory.objects.filter(case__in=cases)
            .select_related("actor")
            .order_by("-occurred_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_legalization.legalizationstatushistory:{history.pk}",
                occurred_at=history.occurred_at,
                category="legalization",
                category_label=_("Legalization"),
                label=_("Legalization status changed"),
                detail=_transition_detail(
                    choices=LegalizationCase.Status.choices,
                    from_value=history.from_status,
                    to_value=history.to_status,
                ),
                actor=history.actor,
            )
            for history in histories
        )
    if user.has_perm("hydra_legalization.view_legalizationworkevent"):
        work_events = (
            LegalizationWorkEvent.objects.filter(case__in=cases)
            .select_related("actor")
            .order_by("-occurred_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_legalization.legalizationworkevent:{event.uuid}",
                occurred_at=event.occurred_at,
                category="legalization",
                category_label=_("Legalization"),
                label=event.get_action_display(),
                actor=event.actor,
            )
            for event in work_events
        )
    if user.has_perm("hydra_legalization.view_legalizationauthorityevent"):
        authority_events = (
            LegalizationAuthorityEvent.objects.filter(case__in=cases)
            .select_related("actor")
            .order_by("-recorded_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_legalization.legalizationauthorityevent:{event.uuid}",
                occurred_at=event.recorded_at,
                category="legalization",
                category_label=_("Legalization"),
                label=event.get_event_type_display(),
                actor=event.actor,
            )
            for event in authority_events
        )
    if user.has_perm("hydra_legalization.view_legalizationrenewallink"):
        renewal_links = (
            LegalizationRenewalLink.objects.filter(
                predecessor__person=person,
                successor__person=person,
            )
            .select_related("actor")
            .order_by("-created_at", "-pk")[:limit]
        )
        items.extend(
            TimelineItem(
                source_key=f"hydra_legalization.legalizationrenewallink:{link.uuid}",
                occurred_at=link.created_at,
                category="legalization",
                category_label=_("Legalization"),
                label=_("Legalization renewal linked"),
                detail=link.get_source_display(),
                actor=link.actor,
            )
            for link in renewal_links
        )
    return items


def _document_items(*, user, person, limit, visible_candidates):
    from hydra_documents.models import DocumentAccessLog

    required = (
        "hydra_documents.view_privatedocument",
        "hydra_documents.view_documentaccesslog",
    )
    if not user.has_perms(required):
        return []
    logs = (
        DocumentAccessLog.objects.filter(
            document__person=person,
            document__candidate__in=visible_candidates,
        )
        .select_related("actor")
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_documents.documentaccesslog:{log.pk}",
            occurred_at=log.occurred_at,
            category="documents",
            category_label=_("Documents"),
            label=log.get_action_display(),
            detail=log.get_outcome_display(),
            actor=log.actor,
        )
        for log in logs
    ]


def _task_items(*, user, person, limit):
    from hydra_tasks.models import HydraTaskEvent
    from hydra_tasks.selectors import tasks_for_user

    if not user.has_perms(
        (
            "hydra_tasks.view_hydratask",
            "hydra_tasks.view_hydrataskevent",
        )
    ):
        return []
    tasks = tasks_for_user(user=user).filter(person=person)
    events = (
        HydraTaskEvent.objects.filter(task__in=tasks)
        .select_related("task", "actor")
        .order_by("-occurred_at", "-pk")[:limit]
    )
    return [
        TimelineItem(
            source_key=f"hydra_tasks.hydrataskevent:{event.uuid}",
            occurred_at=event.occurred_at,
            category="tasks",
            category_label=_("Tasks"),
            label=event.get_action_display(),
            detail=event.task.target_label,
            actor=event.actor,
        )
        for event in events
    ]


def _onboarding_content_items(*, user, person, limit):
    from hydra_onboarding.selectors import (
        assignment_events_for_user,
        assignments_for_user,
    )

    if not user.has_perms(
        (
            "hydra_onboarding.view_courseassignment",
            "hydra_onboarding.view_courseassignmentevent",
        )
    ):
        return []
    assignments = assignments_for_user(user=user).filter(person=person)
    events = assignment_events_for_user(user=user).filter(
        assignment__in=assignments
    ).order_by("-occurred_at", "-pk")[:limit]
    return [
        TimelineItem(
            source_key=f"hydra_onboarding.courseassignmentevent:{event.uuid}",
            occurred_at=event.occurred_at,
            category="onboarding_content",
            category_label=_("Onboarding course"),
            label=event.get_action_display(),
            detail=format_lazy(
                "{} / {} v{}",
                event.assignment.course.code,
                event.assignment.course_version.language,
                event.assignment.course_version.version_number,
            ),
            actor=event.actor,
        )
        for event in events
    ]


def person_timeline_for_user(*, user, person, limit=100) -> list[TimelineItem]:
    """Return only safe timeline facts that the actor may see at source."""

    if not people_for_user(user=user).filter(pk=person.pk).exists():
        return []
    limit = _bounded_limit(limit)
    visible_candidates = _visible_candidates(user=user, person=person)
    items = _person_audit_items(person=person, limit=limit)
    items.extend(
        _application_items(
            person=person,
            limit=limit,
            visible_candidates=visible_candidates,
        )
    )
    items.extend(
        _recruitment_transition_items(
            user=user,
            limit=limit,
            visible_candidates=visible_candidates,
        )
    )
    items.extend(_conversion_items(user=user, person=person))
    items.extend(_merge_items(user=user, person=person, limit=limit))
    items.extend(_organization_items(user=user, person=person, limit=limit))
    items.extend(_arrival_items(user=user, person=person, limit=limit))
    items.extend(_housing_items(user=user, person=person, limit=limit))
    items.extend(_legalization_items(user=user, person=person, limit=limit))
    items.extend(_task_items(user=user, person=person, limit=limit))
    items.extend(_onboarding_content_items(user=user, person=person, limit=limit))
    items.extend(
        _document_items(
            user=user,
            person=person,
            limit=limit,
            visible_candidates=visible_candidates,
        )
    )
    items.sort(
        key=lambda item: (item.occurred_at, item.source_key),
        reverse=True,
    )
    return items[:limit]
