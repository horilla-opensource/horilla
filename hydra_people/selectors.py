from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from hydra_people.models import (
    EmployeeConversion,
    Person,
    PersonDuplicateSuggestion,
    PersonMergeEvent,
)


def company_ids_for_person(*, person, day=None) -> set[int]:
    """Resolve explicit Company relationships without guessing from identity data."""

    day = day or timezone.localdate()
    company_ids = set(
        person.coordination_assignments.filter(
            is_active=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .values_list("team__section__location__company_id", flat=True)
    )
    company_ids.update(
        person.applications.values_list(
            "candidate__recruitment_id__company_id",
            flat=True,
        )
    )
    if person.employee_id:
        employee_company_id = getattr(
            getattr(person.employee, "employee_work_info", None),
            "company_id_id",
            None,
        )
        if employee_company_id:
            company_ids.add(employee_company_id)
    company_ids.discard(None)
    return company_ids


def people_for_user(*, user, permission: str = "view_person") -> QuerySet[Person]:
    """Return permission and organization-scope intersected people."""

    if not user.is_authenticated or not user.has_perm(
        f"hydra_people.{permission}"
    ):
        return Person.objects.none()
    queryset = Person.objects.filter(merged_into__isnull=True).select_related("employee")
    if user.is_superuser:
        return queryset

    from hydra_coordination.selectors import person_scope_q

    return queryset.filter(person_scope_q(user=user)).distinct()


def search_people(*, user, query: str = "") -> QuerySet[Person]:
    queryset = people_for_user(user=user)
    query = query.strip()
    if not query:
        return queryset
    return queryset.filter(
        Q(hydra_id__icontains=query)
        | Q(passport_name__icontains=query)
        | Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
        | Q(merged_sources__hydra_id__icontains=query)
    ).distinct()


def person_for_user(
    *,
    user,
    person_uuid,
    permission: str = "view_person",
    include_merged_alias: bool = False,
) -> Person:
    person = people_for_user(user=user, permission=permission).filter(
        uuid=person_uuid
    ).first()
    if person is not None:
        return person
    if include_merged_alias:
        alias = Person.objects.select_related("merged_into").filter(
            uuid=person_uuid,
            merged_into__isnull=False,
        ).first()
        if alias is not None and people_for_user(
            user=user, permission=permission
        ).filter(pk=alias.merged_into_id).exists():
            return alias
    raise Http404


def duplicate_suggestions_for_user(*, user, state=PersonDuplicateSuggestion.State.OPEN):
    if not user.is_authenticated or not user.has_perms(
        ("hydra_people.view_person", "hydra_people.review_person_duplicates")
    ):
        return PersonDuplicateSuggestion.objects.none()
    visible_people = people_for_user(user=user)
    queryset = PersonDuplicateSuggestion.objects.select_related(
        "person_low__employee",
        "person_high__employee",
        "resolved_by",
    ).filter(person_low__in=visible_people, person_high__in=visible_people)
    if state in PersonDuplicateSuggestion.State.values:
        queryset = queryset.filter(state=state)
    return queryset.distinct()


def duplicate_suggestion_for_user(*, user, suggestion_uuid):
    return get_object_or_404(
        duplicate_suggestions_for_user(user=user),
        uuid=suggestion_uuid,
    )


def person_merge_events_for_user(*, user, person):
    if not user.is_authenticated or not user.has_perm(
        "hydra_people.view_personmergeevent"
    ):
        return PersonMergeEvent.objects.none()
    if not people_for_user(user=user).filter(pk=person.pk).exists():
        return PersonMergeEvent.objects.none()
    return PersonMergeEvent.objects.filter(survivor=person).select_related(
        "duplicate", "actor"
    )


def employee_conversion_for_user(*, user, person):
    if not user.is_authenticated or not user.has_perm(
        "hydra_people.view_employeeconversion"
    ):
        return None
    if not people_for_user(user=user).filter(pk=person.pk).exists():
        return None
    return (
        EmployeeConversion.objects.select_related(
            "candidate__recruitment_id__company_id",
            "employee__employee_work_info",
            "actor",
        )
        .filter(person=person)
        .first()
    )
