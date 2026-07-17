from django.db.models import Q, QuerySet

from hydra_coordination.selectors import company_ids_for_user
from hydra_documents.models import PrivateDocument, PrivateDocumentType
from hydra_people.recruitment_selectors import linked_candidate_for_user


def document_types_for_user(
    *, user, include_inactive=False
) -> QuerySet[PrivateDocumentType]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_documents.view_privatedocumenttype"
    ):
        return PrivateDocumentType.objects.none()
    queryset = PrivateDocumentType.objects.select_related("company")
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(company__isnull=True) | Q(company_id__in=company_ids_for_user(user=user))
        )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def document_types_for_candidate(*, user, candidate):
    company_id = getattr(candidate.recruitment_id, "company_id_id", None)
    return document_types_for_user(user=user).filter(
        Q(company__isnull=True) | Q(company_id=company_id)
    )


def documents_for_candidate(*, user, candidate_id) -> QuerySet[PrivateDocument]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_documents.view_privatedocument"
    ):
        return PrivateDocument.objects.none()
    candidate = linked_candidate_for_user(user=user, candidate_id=candidate_id)
    return (
        PrivateDocument.objects.filter(candidate=candidate)
        .select_related(
            "person",
            "candidate",
            "created_by",
            "document_type__company",
            "replaces",
            "replaced_by",
        )
        .order_by("document_type__name", "lineage_uuid", "-version_number")
    )


def current_documents_for_candidate(*, user, candidate_id):
    return documents_for_candidate(user=user, candidate_id=candidate_id).filter(
        replaced_by__isnull=True,
        deleted_at__isnull=True,
    )
