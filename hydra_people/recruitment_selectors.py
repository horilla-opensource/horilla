from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from hydra_coordination.selectors import active_grants_for_user, company_ids_for_user
from hydra_people.selectors import people_for_user
from recruitment.models import Candidate, Recruitment


def recruitments_for_user(*, user, permission="view_recruitment") -> QuerySet[Recruitment]:
    if not user.is_authenticated or not user.has_perm(f"recruitment.{permission}"):
        return Recruitment._base_manager.none()
    queryset = Recruitment._base_manager.select_related("company_id").prefetch_related(
        "open_positions"
    )
    if user.is_superuser:
        return queryset
    return queryset.filter(company_id__in=company_ids_for_user(user=user)).distinct()


def linked_candidates_for_user(*, user, query="") -> QuerySet[Candidate]:
    if not user.is_authenticated or not user.has_perm("recruitment.view_candidate"):
        return Candidate._base_manager.none()

    queryset = Candidate._base_manager.filter(
        hydra_person_link__isnull=False
    ).select_related(
        "recruitment_id__company_id",
        "job_position_id",
        "stage_id",
        "hydra_person_link__person",
    )
    if not user.is_superuser:
        visible_people = people_for_user(user=user)
        queryset = queryset.filter(
            recruitment_id__company_id__in=company_ids_for_user(user=user),
            hydra_person_link__person__in=visible_people,
        )
    query = query.strip()
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(hydra_person_link__person__hydra_id__icontains=query)
            | Q(hydra_person_link__person__passport_name__icontains=query)
        )
    return queryset.distinct().order_by("name", "pk")


def unlinked_candidates_for_user(*, user) -> QuerySet[Candidate]:
    if not user.is_authenticated or not user.has_perm("recruitment.view_candidate"):
        return Candidate._base_manager.none()
    queryset = Candidate._base_manager.filter(
        hydra_person_link__isnull=True
    ).select_related("recruitment_id__company_id", "job_position_id", "stage_id")
    if user.is_superuser:
        return queryset.order_by("name", "pk")
    direct_company_ids = active_grants_for_user(user=user).filter(
        company__isnull=False
    ).values_list("company_id", flat=True)
    return queryset.filter(
        recruitment_id__company_id__in=direct_company_ids
    ).distinct().order_by("name", "pk")


def linked_candidate_for_user(*, user, candidate_id) -> Candidate:
    return get_object_or_404(
        linked_candidates_for_user(user=user),
        pk=candidate_id,
    )


def conversion_candidates_for_user(*, user, person) -> QuerySet[Candidate]:
    return (
        linked_candidates_for_user(user=user)
        .filter(
            hydra_person_link__person=person,
            hired=True,
            canceled=False,
            is_active=True,
        )
        .select_related(
            "converted_employee_id__employee_work_info",
            "recruitment_id__company_id",
            "job_position_id__department_id",
        )
        .order_by("-joining_date", "name", "pk")
    )


def unlinked_candidate_for_user(*, user, candidate_id) -> Candidate:
    return get_object_or_404(
        unlinked_candidates_for_user(user=user),
        pk=candidate_id,
    )
