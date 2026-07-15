from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from hydra_imports.models import CandidateImportSession
from hydra_people.recruitment_selectors import recruitments_for_user


def candidate_import_sessions_for_user(*, user) -> QuerySet[CandidateImportSession]:
    if not user.is_authenticated or not user.has_perms(
        (
            "hydra_imports.view_candidateimportsession",
            "hydra_imports.import_candidate",
        )
    ):
        return CandidateImportSession.objects.none()

    queryset = CandidateImportSession.objects.select_related(
        "created_by",
        "applied_by",
        "recruitment__company_id",
        "job_position",
    )
    if user.is_superuser:
        return queryset
    return queryset.filter(
        created_by=user,
        recruitment__in=recruitments_for_user(
            user=user,
            permission="view_recruitment",
        ),
    ).distinct()


def candidate_import_session_for_user(*, user, session_uuid) -> CandidateImportSession:
    return get_object_or_404(
        candidate_import_sessions_for_user(user=user),
        uuid=session_uuid,
    )
