from datetime import timedelta

from django.db.models import F, Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_documents.models import PrivateDocument
from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationAuthorityEvent,
    LegalizationCase,
    LegalizationCaseDelegation,
    LegalizationCaseDocument,
    LegalizationRenewalLink,
    LegalizationProcedureRequirement,
    LegalizationProcedureType,
    LegalizationWorkEvent,
)
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import company_ids_for_person, people_for_user


def company_ids_for_legalization_person(*, person, day=None):
    """Resolve explicit companies linked to a Person without guessing."""

    return company_ids_for_person(person=person, day=day)


def legalization_companies_for_person(*, user, person):
    allowed = company_ids_for_user(user=user)
    linked = company_ids_for_legalization_person(person=person)
    return Company._base_manager.filter(pk__in=allowed.intersection(linked)).order_by(
        "company"
    )


def legalization_procedures_for_user(*, user, company=None, include_inactive=False):
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationproceduretype"
    ):
        return LegalizationProcedureType.objects.none()
    queryset = LegalizationProcedureType.objects.select_related("company").prefetch_related(
        "status_rules", "requirements__document_type", "authorities"
    )
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(company__isnull=True) | Q(company_id__in=company_ids_for_user(user=user))
        )
    if company is not None:
        queryset = queryset.filter(Q(company__isnull=True) | Q(company=company))
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset.distinct()


def legalization_authorities_for_user(*, user, company=None, include_inactive=False):
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationauthority"
    ):
        return LegalizationAuthority.objects.none()
    queryset = LegalizationAuthority.objects.select_related("company")
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(company__isnull=True) | Q(company_id__in=company_ids_for_user(user=user))
        )
    if company is not None:
        queryset = queryset.filter(Q(company__isnull=True) | Q(company=company))
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset.distinct()


def legalization_requirements_for_user(*, user, procedure=None, include_inactive=False):
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationprocedurerequirement"
    ):
        return LegalizationProcedureRequirement.objects.none()
    visible_procedures = legalization_procedures_for_user(
        user=user, include_inactive=True
    ).values_list("pk", flat=True)
    queryset = LegalizationProcedureRequirement.objects.filter(
        procedure_id__in=visible_procedures
    ).select_related("procedure__company", "document_type__company")
    if procedure is not None:
        queryset = queryset.filter(procedure=procedure)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def authorities_for_case_snapshot(*, user, case):
    allowed_uuids = [
        row.get("uuid")
        for row in case.procedure_snapshot.get("authorities", [])
        if isinstance(row, dict) and row.get("uuid")
    ]
    return legalization_authorities_for_user(
        user=user, company=case.company, include_inactive=True
    ).filter(uuid__in=allowed_uuids)


def legalization_cases_for_user(*, user, query="", status="") -> QuerySet[LegalizationCase]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationcase"
    ):
        return LegalizationCase.objects.none()
    queryset = LegalizationCase.objects.select_related(
        "person", "responsible", "company", "procedure_type"
    )
    if not user.is_superuser:
        queryset = queryset.filter(
            person__in=people_for_user(user=user),
            company_id__in=company_ids_for_user(user=user),
        )
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


def user_can_operate_legalization_case(*, user, case, day=None) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or case.responsible_id == user.pk:
        return True
    day = day or timezone.localdate()
    return LegalizationCaseDelegation.objects.filter(
        case=case,
        principal_id=case.responsible_id,
        deputy=user,
        is_active=True,
        valid_from__lte=day,
        valid_until__gte=day,
    ).exists()


def legalization_delegations_for_user(*, user, case=None):
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationcasedelegation"
    ):
        return LegalizationCaseDelegation.objects.none()
    visible_case_ids = legalization_cases_for_user(user=user).values_list("pk", flat=True)
    queryset = LegalizationCaseDelegation.objects.filter(
        case_id__in=visible_case_ids
    ).select_related("case", "principal", "deputy", "created_by", "revoked_by")
    if case is not None:
        queryset = queryset.filter(case=case)
    return queryset


def current_legalization_delegations_for_user(*, user, case=None, day=None):
    day = day or timezone.localdate()
    return legalization_delegations_for_user(user=user, case=case).filter(
        is_active=True,
        valid_from__lte=day,
        valid_until__gte=day,
        principal_id=F("case__responsible_id"),
    )


def legalization_work_events_for_user(*, user, case=None):
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationworkevent"
    ):
        return LegalizationWorkEvent.objects.none()
    visible_case_ids = legalization_cases_for_user(user=user).values_list("pk", flat=True)
    queryset = LegalizationWorkEvent.objects.filter(
        case_id__in=visible_case_ids
    ).select_related(
        "case",
        "delegation",
        "from_user",
        "to_user",
        "actor",
    )
    if case is not None:
        queryset = queryset.filter(case=case)
    return queryset


def legalization_workload_for_user(
    *, user, query="", status="", owner="", attention=""
) -> QuerySet[LegalizationCase]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_legalization.view_legalizationworkload"
    ):
        return LegalizationCase.objects.none()
    queryset = legalization_cases_for_user(user=user, query=query)
    active_statuses = (
        LegalizationCase.Status.DRAFT,
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.ADDITIONAL_INFORMATION,
    )
    valid_statuses = {value for value, _label in LegalizationCase.Status.choices}
    if status in valid_statuses:
        queryset = queryset.filter(status=status)
    else:
        queryset = queryset.filter(status__in=active_statuses)
    try:
        owner_id = int(owner)
    except (TypeError, ValueError):
        owner_id = None
    if owner_id:
        queryset = queryset.filter(responsible_id=owner_id)
    today = timezone.localdate()
    if attention == "overdue":
        queryset = queryset.filter(deadline__lt=today)
    elif attention == "due_14":
        queryset = queryset.filter(
            deadline__gte=today,
            deadline__lte=today + timedelta(days=14),
        )
    elif attention == "no_deadline":
        queryset = queryset.filter(deadline__isnull=True)
    current_delegations = LegalizationCaseDelegation.objects.filter(
        is_active=True,
        valid_from__lte=today,
        valid_until__gte=today,
    ).select_related("principal", "deputy")
    return queryset.prefetch_related(
        Prefetch(
            "delegations",
            queryset=current_delegations,
            to_attr="current_delegations",
        )
    ).order_by(
        F("deadline").asc(nulls_last=True),
        "responsible__username",
        "person__passport_name",
        "pk",
    )


def legalization_workload_owner_choices(*, user):
    if not user.has_perm("hydra_legalization.view_legalizationworkload"):
        return []
    return list(
        legalization_cases_for_user(user=user)
        .values_list(
            "responsible_id",
            "responsible__first_name",
            "responsible__last_name",
            "responsible__username",
        )
        .distinct()
        .order_by("responsible__username")
    )


def visible_private_documents_for_case(*, user, case) -> QuerySet[PrivateDocument]:
    if not user.has_perm("hydra_documents.view_privatedocument"):
        return PrivateDocument.objects.none()
    candidates = linked_candidates_for_user(user=user).filter(
        hydra_person_link__person=case.person
    )
    return PrivateDocument.objects.filter(
        person=case.person,
        candidate__in=candidates,
        deleted_at__isnull=True,
        scanned_at__isnull=False,
    ).exclude(file="").select_related("candidate", "person")


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


def authority_events_for_user(*, user, case):
    if not user.has_perm("hydra_legalization.view_legalizationauthorityevent"):
        return []
    visible_case = legalization_cases_for_user(user=user).filter(pk=case.pk).exists()
    if not visible_case:
        return []
    visible_document_ids = set(
        visible_private_documents_for_case(user=user, case=case).values_list(
            "pk", flat=True
        )
    )
    events = list(
        LegalizationAuthorityEvent.objects.filter(case=case).select_related(
            "actor", "evidence_document"
        )
    )
    for event in events:
        event.evidence_available = event.evidence_document_id in visible_document_ids
    return events


def renewal_links_for_user(*, user) -> QuerySet[LegalizationRenewalLink]:
    if not user.has_perm("hydra_legalization.view_legalizationrenewallink"):
        return LegalizationRenewalLink.objects.none()
    visible_case_ids = legalization_cases_for_user(user=user).values_list("pk", flat=True)
    return LegalizationRenewalLink.objects.filter(
        predecessor_id__in=visible_case_ids,
        successor_id__in=visible_case_ids,
    ).select_related(
        "predecessor__person",
        "successor__person",
        "actor",
    )


def renewal_links_for_case(*, user, case):
    links = renewal_links_for_user(user=user)
    predecessor_link = links.filter(successor=case).first()
    successor_link = links.filter(predecessor=case).first()
    return predecessor_link, successor_link


def eligible_renewal_predecessors(*, user, successor):
    if not user.has_perms(
        (
            "hydra_legalization.view_legalizationcase",
            "hydra_legalization.view_legalizationrenewallink",
            "hydra_legalization.create_legalizationrenewallink",
        )
    ):
        return LegalizationCase.objects.none()
    if not user_can_operate_legalization_case(user=user, case=successor):
        return LegalizationCase.objects.none()
    existing = LegalizationRenewalLink.objects.filter(successor=successor).first()
    if existing:
        return legalization_cases_for_user(user=user).filter(pk=existing.predecessor_id)
    used_predecessors = LegalizationRenewalLink.objects.values_list(
        "predecessor_id", flat=True
    )
    return (
        legalization_cases_for_user(user=user)
        .filter(
            person=successor.person,
            company=successor.company,
            procedure_type=successor.procedure_type,
        )
        .filter(
            Q(status__in=(LegalizationCase.Status.APPROVED, LegalizationCase.Status.EXPIRED))
            | Q(status_history__to_status=LegalizationCase.Status.APPROVED)
        )
        .exclude(pk=successor.pk)
        .exclude(pk__in=used_predecessors)
        .filter(
            Q(created_at__lt=successor.created_at)
            | Q(created_at=successor.created_at, pk__lt=successor.pk)
        )
        .distinct()
        .order_by("-created_at", "-pk")
    )
