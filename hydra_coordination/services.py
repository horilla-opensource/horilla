from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from employee.models import EmployeeWorkInformation

from hydra_coordination.models import (
    Location,
    OrganizationAccessEvent,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
    TerminationMode,
)
from hydra_coordination.selectors import (
    grant_covers_target,
    grants_covering_target,
)
from hydra_people.models import Person
from hydra_people.identity import ensure_canonical_person
from hydra_notifications.models import (
    NotificationKind,
    NotificationTargetKind,
)
from hydra_notifications.services import send_hydra_notification


def _require_permissions(actor, *permissions):
    if not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def _stamp(instance, actor):
    if instance._state.adding:
        instance.created_by = actor
    instance.modified_by = actor


def _target_kwargs(grant):
    return {
        name: getattr(grant, name)
        for name in ("company", "department", "location", "section", "team")
        if getattr(grant, f"{name}_id")
    }


def _notification_kind(event):
    return {
        OrganizationAccessEvent.Action.SCOPE_REVOKED: (
            NotificationKind.ORGANIZATION_SCOPE_REVOKED
        ),
        OrganizationAccessEvent.Action.SCOPE_END_SCHEDULED: (
            NotificationKind.ORGANIZATION_SCOPE_END
        ),
        OrganizationAccessEvent.Action.ASSIGNMENT_ENDED: (
            NotificationKind.ORGANIZATION_ASSIGNMENT_ENDED
        ),
        OrganizationAccessEvent.Action.ASSIGNMENT_END_SCHEDULED: (
            NotificationKind.ORGANIZATION_ASSIGNMENT_END
        ),
    }[event.action]


def dispatch_organization_access_event(event_id):
    """Deliver one durable organization event to Horilla notifications."""

    try:
        with transaction.atomic():
            event = OrganizationAccessEvent.objects.select_for_update(
                of=("self",)
            ).select_related(
                "actor",
                "subject_user",
                "scope_grant",
                "person_assignment__person",
            ).get(pk=event_id)
            if event.notification_status in (
                OrganizationAccessEvent.NotificationStatus.SENT,
                OrganizationAccessEvent.NotificationStatus.NOT_APPLICABLE,
            ):
                return True
            if event.subject_user_id is None:
                event.notification_status = (
                    OrganizationAccessEvent.NotificationStatus.NOT_APPLICABLE
                )
                event.notification_last_attempt_at = timezone.now()
                event.notification_error_code = ""
                event.save(
                    update_fields=(
                        "notification_status",
                        "notification_last_attempt_at",
                        "notification_error_code",
                    )
                )
                return True

            notification = send_hydra_notification(
                actor=event.actor,
                recipient=event.subject_user,
                kind=_notification_kind(event),
                target_kind=NotificationTargetKind.ORGANIZATION,
                redirect_path=reverse("hydra-organization"),
                idempotency_key=f"organization-access:{event.uuid}",
            )
            event.notification = notification
            event.notification_status = OrganizationAccessEvent.NotificationStatus.SENT
            event.notification_attempts += 1
            event.notification_last_attempt_at = timezone.now()
            event.notification_error_code = ""
            event.save(
                update_fields=(
                    "notification",
                    "notification_status",
                    "notification_attempts",
                    "notification_last_attempt_at",
                    "notification_error_code",
                )
            )
            return True
    except Exception as error:
        OrganizationAccessEvent.objects.filter(pk=event_id).update(
            notification_status=OrganizationAccessEvent.NotificationStatus.FAILED,
            notification_attempts=F("notification_attempts") + 1,
            notification_last_attempt_at=timezone.now(),
            notification_error_code=type(error).__name__[:80],
        )
        return False


def dispatch_pending_organization_notifications(*, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    from django.conf import settings

    event_ids = list(
        OrganizationAccessEvent.objects.filter(
            notification_status__in=(
                OrganizationAccessEvent.NotificationStatus.PENDING,
                OrganizationAccessEvent.NotificationStatus.FAILED,
            ),
            notification_attempts__lt=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        )
        .order_by("occurred_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = 0
    for event_id in event_ids:
        if dispatch_organization_access_event(event_id):
            sent += 1
        else:
            failed += 1
    return sent, failed, len(event_ids)


def _create_access_event(
    *, actor, scope_grant=None, person_assignment=None, action, reason, last_day
):
    subject_user = None
    if scope_grant is not None:
        subject_user = scope_grant.user
    elif (
        person_assignment.person.employee_id
        and person_assignment.person.employee.employee_user_id_id
    ):
        subject_user = person_assignment.person.employee.employee_user_id
    event = OrganizationAccessEvent(
        scope_grant=scope_grant,
        person_assignment=person_assignment,
        action=action,
        actor=actor,
        subject_user=subject_user,
        reason=reason,
        effective_until=last_day,
        notification_status=(
            OrganizationAccessEvent.NotificationStatus.PENDING
            if subject_user is not None
            else OrganizationAccessEvent.NotificationStatus.NOT_APPLICABLE
        ),
    )
    event.full_clean()
    event.save()
    if subject_user is not None:
        transaction.on_commit(lambda: dispatch_organization_access_event(event.pk))
    return event


def _apply_termination(*, instance, action, last_day, reason, actor):
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError({"reason": "A termination reason is required."})
    today = timezone.localdate()

    if (
        action == "schedule"
        and instance.termination_mode == TerminationMode.SCHEDULED
        and instance.valid_until == last_day
        and instance.termination_reason == reason
    ):
        return False
    if (
        action == "immediate"
        and instance.termination_mode == TerminationMode.IMMEDIATE
        and not instance.is_active
        and instance.termination_reason == reason
    ):
        return False
    if not instance.can_terminate:
        raise ValidationError("This access record has already ended.")

    if action == "schedule":
        if last_day is None:
            raise ValidationError({"last_day": "Choose the last day of access."})
        if last_day < today:
            raise ValidationError({"last_day": "The last day cannot be in the past."})
        if last_day < instance.valid_from:
            raise ValidationError(
                {"last_day": "The last day cannot precede the start date."}
            )
        if instance.valid_until is not None and last_day > instance.valid_until:
            raise ValidationError(
                {"last_day": "This end action cannot extend existing access."}
            )
        instance.valid_until = last_day
        instance.termination_mode = TerminationMode.SCHEDULED
    elif action == "immediate":
        instance.is_active = False
        instance.termination_mode = TerminationMode.IMMEDIATE
        last_day = None
    else:
        raise ValidationError({"action": "Choose a valid end action."})

    instance.termination_reason = reason[:255]
    instance.termination_recorded_at = timezone.now()
    instance.termination_recorded_by = actor
    _stamp(instance, actor)
    instance.full_clean()
    instance.save()
    return last_day


@transaction.atomic
def end_scope_grant(*, grant_id, action, last_day, reason, actor) -> ScopeGrant:
    _require_permissions(
        actor,
        "hydra_coordination.view_scopegrant",
        "hydra_coordination.change_scopegrant",
    )
    grant = ScopeGrant.objects.select_for_update(of=("self",)).select_related(
        "user", "company", "department", "location", "section", "team"
    ).get(pk=grant_id)
    if not actor.is_superuser and not grant_covers_target(
        user=actor, **_target_kwargs(grant)
    ):
        raise PermissionDenied
    applied_last_day = _apply_termination(
        instance=grant,
        action=action,
        last_day=last_day,
        reason=reason,
        actor=actor,
    )
    if applied_last_day is False:
        return grant
    _create_access_event(
        actor=actor,
        scope_grant=grant,
        action=(
            OrganizationAccessEvent.Action.SCOPE_END_SCHEDULED
            if action == "schedule"
            else OrganizationAccessEvent.Action.SCOPE_REVOKED
        ),
        reason=grant.termination_reason,
        last_day=applied_last_day,
    )
    return grant


@transaction.atomic
def end_person_assignment(
    *, assignment_id, action, last_day, reason, actor
) -> PersonAssignment:
    _require_permissions(
        actor,
        "hydra_people.view_person",
        "hydra_coordination.change_personassignment",
        "hydra_coordination.assign_person",
    )
    assignment = PersonAssignment.objects.select_for_update(of=("self",)).select_related(
        "person__employee__employee_user_id",
        "team__section__location__company",
        "department",
    ).get(pk=assignment_id)

    from hydra_people.selectors import people_for_user

    if not actor.is_superuser and not people_for_user(user=actor).filter(
        pk=assignment.person_id
    ).exists():
        raise PermissionDenied
    if not grant_covers_target(user=actor, team=assignment.team):
        raise PermissionDenied
    applied_last_day = _apply_termination(
        instance=assignment,
        action=action,
        last_day=last_day,
        reason=reason,
        actor=actor,
    )
    if applied_last_day is False:
        return assignment
    _create_access_event(
        actor=actor,
        person_assignment=assignment,
        action=(
            OrganizationAccessEvent.Action.ASSIGNMENT_END_SCHEDULED
            if action == "schedule"
            else OrganizationAccessEvent.Action.ASSIGNMENT_ENDED
        ),
        reason=assignment.termination_reason,
        last_day=applied_last_day,
    )
    return assignment


@transaction.atomic
def save_location(*, location: Location, actor) -> Location:
    permission = "add_location" if location._state.adding else "change_location"
    _require_permissions(actor, f"hydra_coordination.{permission}")
    if not grant_covers_target(user=actor, company=location.company):
        raise PermissionDenied
    _stamp(location, actor)
    location.full_clean()
    location.save()
    return location


@transaction.atomic
def save_section(*, section: Section, actor) -> Section:
    permission = "add_section" if section._state.adding else "change_section"
    _require_permissions(actor, f"hydra_coordination.{permission}")
    if not grant_covers_target(user=actor, location=section.location):
        raise PermissionDenied
    _stamp(section, actor)
    section.full_clean()
    section.save()
    return section


@transaction.atomic
def save_team(*, team: Team, actor) -> Team:
    permission = "add_team" if team._state.adding else "change_team"
    _require_permissions(actor, f"hydra_coordination.{permission}")
    if not grant_covers_target(user=actor, section=team.section):
        raise PermissionDenied
    _stamp(team, actor)
    team.full_clean()
    team.save()
    return team


@transaction.atomic
def save_scope_grant(*, grant: ScopeGrant, actor) -> ScopeGrant:
    permission = "add_scopegrant" if grant._state.adding else "change_scopegrant"
    _require_permissions(actor, f"hydra_coordination.{permission}")
    grant.full_clean()

    if not actor.is_superuser:
        covering = grants_covering_target(user=actor, **_target_kwargs(grant)).filter(
            valid_from__lte=grant.valid_from
        )
        if grant.valid_until is None:
            covering = covering.filter(valid_until__isnull=True)
        else:
            covering = covering.filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=grant.valid_until)
            )
        if not covering.exists():
            raise PermissionDenied

    _stamp(grant, actor)
    grant.save()
    return grant


@transaction.atomic
def assign_person(*, assignment: PersonAssignment, actor) -> PersonAssignment:
    permission = (
        "add_personassignment"
        if assignment._state.adding
        else "change_personassignment"
    )
    _require_permissions(
        actor,
        f"hydra_coordination.{permission}",
        "hydra_coordination.assign_person",
        "hydra_people.view_person",
    )

    from hydra_people.selectors import people_for_user

    locked_person = Person.objects.select_for_update().get(pk=assignment.person_id)
    ensure_canonical_person(locked_person)
    if not actor.is_superuser and not people_for_user(user=actor).filter(
        pk=locked_person.pk
    ).exists():
        raise PermissionDenied
    if not grant_covers_target(user=actor, team=assignment.team):
        raise PermissionDenied

    assignment.person = locked_person
    assignment.full_clean()
    if assignment.is_primary and assignment.is_active:
        overlap = PersonAssignment.objects.select_for_update().filter(
            person=locked_person,
            is_primary=True,
            is_active=True,
        )
        if assignment.pk:
            overlap = overlap.exclude(pk=assignment.pk)
        if assignment.valid_until:
            overlap = overlap.filter(valid_from__lte=assignment.valid_until)
        overlap = overlap.filter(
            Q(valid_until__isnull=True)
            | Q(valid_until__gte=assignment.valid_from)
        )
        if overlap.exists():
            raise ValidationError(
                {"valid_from": "Primary assignments cannot overlap."}
            )

    _stamp(assignment, actor)
    assignment.save()
    return assignment


def _synchronize_employee_work_information(*, person, team, department, actor):
    """Project the current Hydra assignment into Horilla employee work data."""

    work_info = EmployeeWorkInformation._base_manager.select_for_update().get(
        employee_id=person.employee_id
    )
    work_info.company_id = team.section.location.company
    work_info.department_id = department
    work_info.location = team.section.location.name

    if (
        work_info.job_position_id_id
        and work_info.job_position_id.department_id_id != department.pk
    ):
        work_info.job_position_id = None
        work_info.job_role_id = None

    work_info._history_user = actor
    work_info.full_clean()
    work_info.save()
    return work_info


@transaction.atomic
def assign_employee_to_team(
    *, person: Person, team: Team, valid_from, actor
) -> PersonAssignment:
    """Move a converted Person to a Team and keep Horilla work data aligned.

    ``PersonAssignment`` remains the source of truth. The current Horilla work
    information is a compatibility projection for existing employee screens.
    """

    _require_permissions(
        actor,
        "hydra_coordination.add_personassignment",
        "hydra_coordination.assign_person",
        "hydra_people.view_person",
        "employee.view_employee",
        "employee.change_employeeworkinformation",
    )

    from hydra_people.selectors import people_for_user

    locked_person = Person.objects.select_for_update().get(pk=person.pk)
    ensure_canonical_person(locked_person)
    if not actor.is_superuser and not people_for_user(user=actor).filter(
        pk=locked_person.pk
    ).exists():
        raise PermissionDenied
    if not locked_person.employee_id:
        raise ValidationError(
            {"person": "Convert the Person to an Employee before team assignment."}
        )

    locked_team_id = Team.objects.select_for_update().only("pk").get(pk=team.pk).pk
    locked_team = Team.objects.select_related(
        "section__location__company", "section__department"
    ).get(pk=locked_team_id)
    if not grant_covers_target(user=actor, team=locked_team):
        raise PermissionDenied
    if not (
        locked_team.is_active
        and locked_team.section.is_active
        and locked_team.section.location.is_active
    ):
        raise ValidationError({"team": "Choose an active organization team."})

    department = locked_team.section.department
    if department is None:
        raise ValidationError(
            {"team": "The team section must have a department before assignment."}
        )

    valid_from = valid_from or timezone.localdate()
    if valid_from > timezone.localdate():
        raise ValidationError(
            {"valid_from": "Employee team assignment cannot start in the future."}
        )

    overlaps = PersonAssignment.objects.select_for_update().filter(
        person=locked_person,
        is_primary=True,
        is_active=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from))

    same_current = overlaps.filter(
        team=locked_team,
        department=department,
        valid_from__lte=timezone.localdate(),
    ).first()
    if same_current is not None and same_current.is_current():
        _synchronize_employee_work_information(
            person=locked_person,
            team=locked_team,
            department=department,
            actor=actor,
        )
        from hydra_arrivals.onboarding import reconcile_person_onboarding_handoff

        reconcile_person_onboarding_handoff(person=locked_person, actor=actor)
        return same_current

    for previous in overlaps:
        _stamp(previous, actor)
        if previous.valid_from < valid_from:
            previous.valid_until = valid_from - timedelta(days=1)
        else:
            previous.is_active = False
        previous.full_clean()
        previous.save()

    assignment = PersonAssignment(
        person=locked_person,
        team=locked_team,
        department=department,
        valid_from=valid_from,
        is_primary=True,
        is_active=True,
    )
    _stamp(assignment, actor)
    assignment.full_clean()
    assignment.save()
    _synchronize_employee_work_information(
        person=locked_person,
        team=locked_team,
        department=department,
        actor=actor,
    )
    from hydra_arrivals.onboarding import reconcile_person_onboarding_handoff

    reconcile_person_onboarding_handoff(person=locked_person, actor=actor)
    return assignment
