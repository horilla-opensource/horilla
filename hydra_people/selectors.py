from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from hydra_people.models import EmployeeConversion, Person


def people_for_user(*, user, permission: str = "view_person") -> QuerySet[Person]:
    """Return permission and organization-scope intersected people."""

    if not user.is_authenticated or not user.has_perm(
        f"hydra_people.{permission}"
    ):
        return Person.objects.none()
    queryset = Person.objects.select_related("employee")
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
    ).distinct()


def person_for_user(*, user, person_uuid, permission: str = "view_person") -> Person:
    return get_object_or_404(
        people_for_user(user=user, permission=permission), uuid=person_uuid
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
