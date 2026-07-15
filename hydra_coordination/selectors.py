from django.db.models import Q, QuerySet
from django.utils import timezone

from base.models import Company, Department
from hydra_coordination.models import Location, ScopeGrant, Section, Team


def active_grants_for_user(*, user, day=None) -> QuerySet[ScopeGrant]:
    if not user.is_authenticated:
        return ScopeGrant.objects.none()
    day = day or timezone.localdate()
    return (
        ScopeGrant.objects.filter(
            user=user,
            is_active=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .select_related("company", "department", "location", "section", "team")
    )


def _scope_ids(*, user, day=None):
    grants = active_grants_for_user(user=user, day=day)
    return {
        field_name: set(
            grants.exclude(**{f"{field_name}__isnull": True}).values_list(
                f"{field_name}_id", flat=True
            )
        )
        for field_name in ("company", "department", "location", "section", "team")
    }


def company_ids_for_user(*, user, day=None) -> set[int]:
    """Resolve every active Hydra grant to its containing legal company."""

    if not user.is_authenticated:
        return set()
    if user.is_superuser:
        return set(Company._base_manager.values_list("pk", flat=True))

    company_ids = set()
    for grant in active_grants_for_user(user=user, day=day):
        if grant.company_id:
            company_ids.add(grant.company_id)
        elif grant.department_id:
            company_ids.update(
                grant.department.company_id.values_list("pk", flat=True)
            )
        elif grant.location_id:
            company_ids.add(grant.location.company_id)
        elif grant.section_id:
            company_ids.add(grant.section.location.company_id)
        elif grant.team_id:
            company_ids.add(grant.team.section.location.company_id)
    return company_ids


def grants_covering_target(
    *, user, company=None, department=None, location=None, section=None, team=None
) -> QuerySet[ScopeGrant]:
    """Return actor grants whose hierarchy contains exactly one supplied target."""

    if not user.is_authenticated:
        return ScopeGrant.objects.none()

    supplied = [value for value in (company, department, location, section, team) if value]
    if len(supplied) != 1:
        return ScopeGrant.objects.none()

    if company:
        scope_q = Q(company=company)
    elif department:
        scope_q = Q(department=department) | Q(company__in=department.company_id.all())
    elif location:
        scope_q = Q(location=location) | Q(company=location.company)
    elif section:
        scope_q = (
            Q(section=section)
            | Q(location=section.location)
            | Q(company=section.location.company)
        )
        if section.department_id:
            scope_q |= Q(department=section.department)
    else:
        scope_q = (
            Q(team=team)
            | Q(section=team.section)
            | Q(location=team.section.location)
            | Q(company=team.section.location.company)
        )
        if team.section.department_id:
            scope_q |= Q(department=team.section.department)

    return ScopeGrant.objects.filter(user=user, is_active=True).filter(scope_q)


def grant_covers_target(
    *, user, company=None, department=None, location=None, section=None, team=None, day=None
) -> bool:
    if user.is_superuser:
        return True
    day = day or timezone.localdate()
    return (
        grants_covering_target(
            user=user,
            company=company,
            department=department,
            location=location,
            section=section,
            team=team,
        )
        .filter(valid_from__lte=day)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .exists()
    )


def person_scope_q(*, user, day=None) -> Q:
    """Build the explicit organization predicate used by every Person read."""

    day = day or timezone.localdate()
    scope = _scope_ids(user=user, day=day)
    hierarchy_q = (
        Q(coordination_assignments__team__section__location__company_id__in=scope["company"])
        | Q(coordination_assignments__department_id__in=scope["department"])
        | Q(coordination_assignments__team__section__location_id__in=scope["location"])
        | Q(coordination_assignments__team__section_id__in=scope["section"])
        | Q(coordination_assignments__team_id__in=scope["team"])
    )
    current_assignment_q = (
        Q(coordination_assignments__is_active=True)
        & Q(coordination_assignments__valid_from__lte=day)
        & (
            Q(coordination_assignments__valid_until__isnull=True)
            | Q(coordination_assignments__valid_until__gte=day)
        )
    )
    creator_of_never_assigned_q = Q(
        created_by=user,
        coordination_assignments__isnull=True,
    )
    return creator_of_never_assigned_q | (current_assignment_q & hierarchy_q)


def locations_for_user(*, user, permission="view_location", day=None):
    if not user.is_authenticated or not user.has_perm(
        f"hydra_coordination.{permission}"
    ):
        return Location.objects.none()
    queryset = Location.objects.select_related("company")
    if user.is_superuser:
        return queryset
    scope = _scope_ids(user=user, day=day)
    return queryset.filter(
        Q(company_id__in=scope["company"])
        | Q(pk__in=scope["location"])
        | Q(sections__department_id__in=scope["department"])
        | Q(sections__pk__in=scope["section"])
        | Q(sections__teams__pk__in=scope["team"])
    ).distinct()


def sections_for_user(*, user, permission="view_section", day=None):
    if not user.is_authenticated or not user.has_perm(
        f"hydra_coordination.{permission}"
    ):
        return Section.objects.none()
    queryset = Section.objects.select_related("location__company", "department")
    if user.is_superuser:
        return queryset
    scope = _scope_ids(user=user, day=day)
    return queryset.filter(
        Q(location__company_id__in=scope["company"])
        | Q(department_id__in=scope["department"])
        | Q(location_id__in=scope["location"])
        | Q(pk__in=scope["section"])
        | Q(teams__pk__in=scope["team"])
    ).distinct()


def teams_for_user(*, user, permission="view_team", day=None):
    if not user.is_authenticated or not user.has_perm(
        f"hydra_coordination.{permission}"
    ):
        return Team.objects.none()
    queryset = Team.objects.select_related(
        "section__location__company", "section__department"
    )
    if user.is_superuser:
        return queryset
    scope = _scope_ids(user=user, day=day)
    return queryset.filter(
        Q(section__location__company_id__in=scope["company"])
        | Q(section__department_id__in=scope["department"])
        | Q(section__location_id__in=scope["location"])
        | Q(section_id__in=scope["section"])
        | Q(pk__in=scope["team"])
    ).distinct()


def departments_for_user(*, user, day=None):
    if not user.is_authenticated:
        return Department.objects.none()
    if user.is_superuser:
        return Department._base_manager.all().order_by("department")
    scope = _scope_ids(user=user, day=day)
    return (
        Department._base_manager.filter(
            Q(company_id__pk__in=scope["company"])
            | Q(pk__in=scope["department"])
            | Q(hydra_sections__location_id__in=scope["location"])
            | Q(hydra_sections__pk__in=scope["section"])
            | Q(hydra_sections__teams__pk__in=scope["team"])
        )
        .distinct()
        .order_by("department")
    )
