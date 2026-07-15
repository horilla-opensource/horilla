from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from hydra_documents.models import PrivateDocument
from hydra_legalization.models import LegalizationCase, LegalizationCaseDocument
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import people_for_user


def legalization_cases_for_user(*, user, query="", status="") -> QuerySet[LegalizationCase]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationcase"
    ):
        return LegalizationCase.objects.none()
    queryset = LegalizationCase.objects.select_related("person", "responsible")
    if not user.is_superuser:
        queryset = queryset.filter(person__in=people_for_user(user=user))
    query = query.strip()
    if query:
        queryset = queryset.filter(
            Q(person__hydra_id__icontains=query)
            | Q(person__passport_name__icontains=query)
            | Q(reference_number__icontains=query)
        )
    valid_statuses = {value for value, _label in LegalizationCase.Status.choices}
    if status in valid_statuses:
        queryset = queryset.filter(status=status)
    return queryset.distinct()


def legalization_case_for_user(*, user, case_uuid) -> LegalizationCase:
    return get_object_or_404(
        legalization_cases_for_user(user=user),
        uuid=case_uuid,
    )


def visible_private_documents_for_case(*, user, case) -> QuerySet[PrivateDocument]:
    if not user.has_perm("hydra_documents.view_privatedocument"):
        return PrivateDocument.objects.none()
    candidates = linked_candidates_for_user(user=user).filter(
        hydra_person_link__person=case.person
    )
    return PrivateDocument.objects.filter(
        person=case.person, candidate__in=candidates
    ).select_related("candidate", "person")


def case_document_links_for_user(*, user, case) -> QuerySet[LegalizationCaseDocument]:
    documents = visible_private_documents_for_case(user=user, case=case)
    return LegalizationCaseDocument.objects.filter(
        case=case, document__in=documents
    ).select_related("document", "created_by")


def available_private_documents_for_case(*, user, case) -> QuerySet[PrivateDocument]:
    linked_ids = case.document_links.values_list("document_id", flat=True)
    return visible_private_documents_for_case(user=user, case=case).exclude(
        pk__in=linked_ids
    )
