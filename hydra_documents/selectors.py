from django.db.models import QuerySet

from hydra_documents.models import PrivateDocument
from hydra_people.recruitment_selectors import linked_candidate_for_user


def documents_for_candidate(*, user, candidate_id) -> QuerySet[PrivateDocument]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_documents.view_privatedocument"
    ):
        return PrivateDocument.objects.none()
    candidate = linked_candidate_for_user(user=user, candidate_id=candidate_id)
    return PrivateDocument.objects.filter(candidate=candidate).select_related(
        "person", "candidate", "created_by"
    )
