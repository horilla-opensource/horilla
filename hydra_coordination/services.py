from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from employee.models import EmployeeWorkInformation

from hydra_coordination.models import (
    Location,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
)
from hydra_coordination.selectors import (
    grant_covers_target,
    grants_covering_target,
)
from hydra_people.models import Person


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
    return assignment
