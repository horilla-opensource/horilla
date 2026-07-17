from copy import deepcopy
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_coordination.selectors import company_ids_for_user
from hydra_documents.selectors import document_types_for_user
from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationAuthorityEvent,
    LegalizationCase,
    LegalizationCaseDocument,
    LegalizationConfigurationEvent,
    LegalizationProcedureRequirement,
    LegalizationProcedureStatus,
    LegalizationProcedureType,
    LegalizationRenewalLink,
    LegalizationStatusHistory,
)
from hydra_legalization.selectors import (
    authorities_for_case_snapshot,
    available_private_documents_for_case,
    legalization_authorities_for_user,
    legalization_case_for_user,
    legalization_companies_for_person,
    legalization_procedures_for_user,
    legalization_requirements_for_user,
    user_can_operate_legalization_case,
    visible_private_documents_for_case,
)
from hydra_legalization.workload import (
    record_initial_responsibility,
    validate_legalization_responsible,
)
from hydra_people.models import Person
from hydra_people.selectors import person_for_user


ALLOWED_TRANSITIONS = {
    LegalizationCase.Status.DRAFT: {
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.COLLECTING_DOCUMENTS: {
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.SUBMITTED: {
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.ADDITIONAL_INFORMATION: {
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.APPROVED: {
        LegalizationCase.Status.EXPIRED,
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.REJECTED: {LegalizationCase.Status.CLOSED},
    LegalizationCase.Status.EXPIRED: {LegalizationCase.Status.CLOSED},
    LegalizationCase.Status.CLOSED: set(),
}

AUTHORITY_EVENTS_BY_STATUS = {
    LegalizationCase.Status.COLLECTING_DOCUMENTS: {
        LegalizationAuthorityEvent.EventType.SUBMITTED,
    },
    LegalizationCase.Status.SUBMITTED: {
        LegalizationAuthorityEvent.EventType.REFERENCE_ASSIGNED,
        LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED,
        LegalizationAuthorityEvent.EventType.APPROVED,
        LegalizationAuthorityEvent.EventType.REJECTED,
    },
    LegalizationCase.Status.ADDITIONAL_INFORMATION: {
        LegalizationAuthorityEvent.EventType.REFERENCE_ASSIGNED,
        LegalizationAuthorityEvent.EventType.INFORMATION_RESPONDED,
        LegalizationAuthorityEvent.EventType.REJECTED,
    },
}

EXTERNAL_FACT_LOCKED_STATUSES = {
    LegalizationCase.Status.SUBMITTED,
    LegalizationCase.Status.ADDITIONAL_INFORMATION,
    LegalizationCase.Status.APPROVED,
    LegalizationCase.Status.REJECTED,
    LegalizationCase.Status.EXPIRED,
    LegalizationCase.Status.CLOSED,
}

ACTIVE_CASE_STATUSES = {
    LegalizationCase.Status.DRAFT,
    LegalizationCase.Status.COLLECTING_DOCUMENTS,
    LegalizationCase.Status.SUBMITTED,
    LegalizationCase.Status.ADDITIONAL_INFORMATION,
}


AUTHORITY_EVENT_TARGET_STATUS = {
    LegalizationAuthorityEvent.EventType.SUBMITTED: LegalizationCase.Status.SUBMITTED,
    LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED: LegalizationCase.Status.ADDITIONAL_INFORMATION,
    LegalizationAuthorityEvent.EventType.INFORMATION_RESPONDED: LegalizationCase.Status.SUBMITTED,
    LegalizationAuthorityEvent.EventType.APPROVED: LegalizationCase.Status.APPROVED,
    LegalizationAuthorityEvent.EventType.REJECTED: LegalizationCase.Status.REJECTED,
}


def _enabled_statuses(case):
    return {
        row.get("status")
        for row in case.procedure_snapshot.get("statuses", [])
        if isinstance(row, dict) and row.get("status")
    }


def available_transitions(case):
    allowed = ALLOWED_TRANSITIONS[case.status].intersection(_enabled_statuses(case))
    labels = {
        row.get("status"): row.get("label")
        for row in case.procedure_snapshot.get("statuses", [])
        if isinstance(row, dict)
    }
    return [
        (value, labels.get(value) or label)
        for value, label in LegalizationCase.Status.choices
        if value in allowed
    ]


def available_authority_events(case):
    allowed = AUTHORITY_EVENTS_BY_STATUS.get(case.status, set())
    enabled = _enabled_statuses(case)
    return [
        choice
        for choice in LegalizationAuthorityEvent.EventType.choices
        if choice[0] in allowed
        and AUTHORITY_EVENT_TARGET_STATUS.get(choice[0], case.status) in enabled
    ]


def _require(actor, *permissions):
    if not actor.has_perms(permissions):
        raise PermissionDenied


def _validate_responsible(*, responsible, person, company):
    validate_legalization_responsible(
        responsible=responsible,
        person=person,
    )
    if not legalization_companies_for_person(
        user=responsible, person=person
    ).filter(pk=company.pk).exists():
        raise ValidationError(
            {"responsible": _("The responsible user cannot access the case company.")}
        )


def _ensure_no_active_case_duplicate(
    *, person, company, procedure_type, exclude_pk=None
):
    duplicate = LegalizationCase.objects.filter(
        person=person,
        company=company,
        procedure_type=procedure_type,
        status__in=ACTIVE_CASE_STATUSES,
    )
    if exclude_pk:
        duplicate = duplicate.exclude(pk=exclude_pk)
    if duplicate.exists():
        raise ValidationError(
            {
                "procedure_type": _(
                    "An active case of this procedure already exists for this person and company."
                )
            }
        )


def _validate_snapshot_for_new_case(*, procedure, company):
    snapshot = procedure.rules_snapshot(company_id=company.pk)
    enabled = {
        row.get("status")
        for row in snapshot["statuses"]
        if isinstance(row, dict)
    }
    mandatory = {
        LegalizationCase.Status.DRAFT,
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.APPROVED,
        LegalizationCase.Status.REJECTED,
        LegalizationCase.Status.EXPIRED,
        LegalizationCase.Status.CLOSED,
    }
    if not mandatory.issubset(enabled):
        raise ValidationError(
            {"procedure_type": _("The procedure does not enable every mandatory core status.")}
        )
    if procedure.requires_authority and not snapshot["authorities"]:
        raise ValidationError(
            {"procedure_type": _("Configure at least one approved authority first.")}
        )
    return snapshot


def _locked_procedure_snapshot(*, actor, company, procedure):
    visible = legalization_procedures_for_user(
        user=actor, company=company
    ).filter(pk=procedure.pk).first()
    if visible is None:
        raise ValidationError({"procedure_type": _("The procedure is unavailable.")})
    locked = LegalizationProcedureType.objects.select_for_update().get(pk=visible.pk)
    list(
        LegalizationProcedureStatus.objects.select_for_update()
        .filter(procedure=locked)
        .order_by("pk")
    )
    list(
        LegalizationProcedureRequirement.objects.select_for_update()
        .filter(procedure=locked)
        .order_by("pk")
    )
    list(locked.authorities.select_for_update().order_by("pk"))
    return locked, _validate_snapshot_for_new_case(
        procedure=locked, company=company
    )


@transaction.atomic
def create_legalization_case(*, case, actor):
    _require(
        actor,
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_people.view_person",
    )
    person = person_for_user(
        user=actor, person_uuid=case.person.uuid, permission="view_person"
    )
    case.person = Person.objects.select_for_update().get(pk=person.pk)
    company = legalization_companies_for_person(
        user=actor, person=case.person
    ).filter(pk=case.company_id).first()
    if company is None:
        raise ValidationError({"company": _("The company is outside this Person scope.")})
    case.company = company
    procedure, snapshot = _locked_procedure_snapshot(
        actor=actor,
        company=company,
        procedure=case.procedure_type,
    )
    case.procedure_type = procedure
    case.case_type = procedure.case_type
    case.procedure_snapshot = snapshot
    case.status = LegalizationCase.Status.DRAFT
    if not case.deadline and procedure.default_deadline_days:
        case.deadline = timezone.localdate() + timedelta(
            days=procedure.default_deadline_days
        )
    _ensure_no_active_case_duplicate(
        person=case.person,
        company=company,
        procedure_type=procedure,
    )
    if case.responsible_id != actor.pk:
        _require(actor, "hydra_legalization.assign_legalizationcase")
    _validate_responsible(
        responsible=case.responsible,
        person=case.person,
        company=company,
    )
    case.created_by = actor
    case.modified_by = actor
    case.full_clean()
    case.save()
    LegalizationStatusHistory.objects.create(
        case=case,
        from_status="",
        to_status=case.status,
        actor=actor,
        reason="created",
    )
    record_initial_responsibility(case=case, actor=actor)
    return case


def _case_was_approved(case):
    return case.status in {
        LegalizationCase.Status.APPROVED,
        LegalizationCase.Status.EXPIRED,
    } or case.status_history.filter(to_status=LegalizationCase.Status.APPROVED).exists()


def _validate_renewal_pair(*, predecessor, successor):
    if predecessor.pk == successor.pk:
        raise ValidationError(_("A case cannot renew itself."))
    if predecessor.person_id != successor.person_id:
        raise ValidationError(_("Renewal cases must belong to the same person."))
    if (
        predecessor.company_id != successor.company_id
        or predecessor.procedure_type_id != successor.procedure_type_id
    ):
        raise ValidationError(_("Renewal cases must use the same company and procedure."))
    if not _case_was_approved(predecessor):
        raise ValidationError(_("Only an approved or previously approved case can be renewed."))
    if predecessor.created_at and successor.created_at:
        predecessor_order = (predecessor.created_at, predecessor.pk)
        successor_order = (successor.created_at, successor.pk)
        if predecessor_order >= successor_order:
            raise ValidationError(_("The predecessor must be older than the successor."))


def case_can_start_renewal(*, case, actor):
    if not actor.has_perms(
        (
            "hydra_legalization.view_legalizationcase",
            "hydra_legalization.add_legalizationcase",
            "hydra_legalization.view_legalizationrenewallink",
            "hydra_legalization.create_legalizationrenewallink",
        )
    ):
        return False
    if not user_can_operate_legalization_case(user=actor, case=case):
        return False
    if not _case_was_approved(case):
        return False
    if LegalizationRenewalLink.objects.filter(predecessor=case).exists():
        return False
    return not LegalizationCase.objects.filter(
        person_id=case.person_id,
        company_id=case.company_id,
        procedure_type_id=case.procedure_type_id,
        status__in=ACTIVE_CASE_STATUSES,
    ).exists()


@transaction.atomic
def create_legalization_renewal(*, predecessor_uuid, deadline, notes, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_legalization.view_legalizationrenewallink",
        "hydra_legalization.create_legalizationrenewallink",
        "hydra_people.view_person",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=predecessor_uuid)
    person = Person.objects.select_for_update().get(pk=visible.person_id)
    predecessor = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if not user_can_operate_legalization_case(user=actor, case=predecessor):
        raise PermissionDenied
    if not _case_was_approved(predecessor):
        raise ValidationError(_("Only an approved or previously approved case can be renewed."))
    existing = (
        LegalizationRenewalLink.objects.select_related("successor")
        .filter(predecessor=predecessor)
        .first()
    )
    if existing:
        return existing.successor, False
    procedure, snapshot = _locked_procedure_snapshot(
        actor=actor,
        company=predecessor.company,
        procedure=predecessor.procedure_type,
    )
    _ensure_no_active_case_duplicate(
        person=person,
        company=predecessor.company,
        procedure_type=procedure,
    )
    _validate_responsible(
        responsible=actor,
        person=person,
        company=predecessor.company,
    )
    successor = LegalizationCase(
        person=person,
        company=predecessor.company,
        procedure_type=procedure,
        case_type=procedure.case_type,
        procedure_snapshot=snapshot,
        status=LegalizationCase.Status.DRAFT,
        responsible=actor,
        deadline=deadline,
        notes=notes,
        created_by=actor,
        modified_by=actor,
    )
    successor.full_clean()
    successor.save()
    LegalizationStatusHistory.objects.create(
        case=successor,
        from_status="",
        to_status=LegalizationCase.Status.DRAFT,
        actor=actor,
        reason="renewal_created",
    )
    record_initial_responsibility(case=successor, actor=actor)
    link = LegalizationRenewalLink(
        predecessor=predecessor,
        successor=successor,
        source=LegalizationRenewalLink.Source.CREATED,
        reason="",
        actor=actor,
    )
    link.full_clean()
    link.save()
    return successor, True


@transaction.atomic
def link_existing_legalization_renewal(
    *, predecessor_uuid, successor_uuid, reason, actor
):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationrenewallink",
        "hydra_legalization.create_legalizationrenewallink",
    )
    visible_predecessor = legalization_case_for_user(
        user=actor, case_uuid=predecessor_uuid
    )
    visible_successor = legalization_case_for_user(user=actor, case_uuid=successor_uuid)
    if visible_predecessor.person_id != visible_successor.person_id:
        raise ValidationError(_("Renewal cases must belong to the same person."))
    Person.objects.select_for_update().get(pk=visible_predecessor.person_id)
    locked = {
        case.pk: case
        for case in LegalizationCase.objects.select_for_update()
        .filter(pk__in=(visible_predecessor.pk, visible_successor.pk))
        .order_by("pk")
    }
    predecessor = locked[visible_predecessor.pk]
    successor = locked[visible_successor.pk]
    if not user_can_operate_legalization_case(user=actor, case=successor):
        raise PermissionDenied
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError({"reason": _("A manual historical link requires a reason.")})
    _validate_renewal_pair(predecessor=predecessor, successor=successor)
    existing_successor = (
        LegalizationRenewalLink.objects.select_related("predecessor")
        .filter(successor=successor)
        .first()
    )
    if existing_successor:
        if (
            existing_successor.predecessor_id == predecessor.pk
            and existing_successor.source == LegalizationRenewalLink.Source.MANUAL
            and existing_successor.reason == reason
            and existing_successor.actor_id == actor.pk
        ):
            return existing_successor, False
        raise ValidationError(_("The successor already has a different predecessor."))
    if LegalizationRenewalLink.objects.filter(predecessor=predecessor).exists():
        raise ValidationError(_("The predecessor already has a successor."))
    link = LegalizationRenewalLink(
        predecessor=predecessor,
        successor=successor,
        source=LegalizationRenewalLink.Source.MANUAL,
        reason=reason,
        actor=actor,
    )
    link.full_clean()
    link.save()
    return link, True


@transaction.atomic
def update_legalization_case(*, case, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case.uuid)
    current = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if not user_can_operate_legalization_case(user=actor, case=current):
        raise PermissionDenied
    if current.status in EXTERNAL_FACT_LOCKED_STATUSES:
        for field in (
            "reference_number",
            "deadline",
            "valid_from",
            "valid_until",
        ):
            if getattr(current, field) != getattr(case, field):
                raise ValidationError(
                    {field: _("This external fact can only be changed by an authority event.")}
                )
    if current.responsible_id != case.responsible_id:
        _require(actor, "hydra_legalization.assign_legalizationcase")
        raise ValidationError(
            {
                "responsible": _(
                    "Use the audited responsibility transfer action to change the owner."
                )
            }
        )
    _validate_responsible(
        responsible=case.responsible,
        person=current.person,
        company=current.company,
    )
    for field in (
        "responsible",
        "reference_number",
        "deadline",
        "valid_from",
        "valid_until",
        "notes",
    ):
        setattr(current, field, getattr(case, field))
    current.modified_by = actor
    current.full_clean()
    current.save()
    return current


def _validate_case_requirements(*, case, target_status, proposed_document=None):
    requirements = [
        row
        for row in case.procedure_snapshot.get("requirements", [])
        if isinstance(row, dict)
        and row.get("required_before_status") == target_status
    ]
    if not requirements:
        return
    satisfied = {
        str(value)
        for value in case.document_links.filter(
            document__deleted_at__isnull=True,
            document__scanned_at__isnull=False,
        )
        .exclude(document__file="")
        .values_list("document__document_type__uuid", flat=True)
    }
    if proposed_document is not None and proposed_document.is_downloadable:
        satisfied.add(str(proposed_document.document_type.uuid))
    missing = [
        row.get("name") or row.get("code")
        for row in requirements
        if row.get("document_type_uuid") not in satisfied
    ]
    if missing:
        raise ValidationError(
            {
                "target_status": _("Missing required document(s): %(documents)s")
                % {"documents": ", ".join(missing)}
            }
        )


@transaction.atomic
def transition_legalization_case(*, case_uuid, target_status, reason, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.transition_legalizationcase",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    case = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if not user_can_operate_legalization_case(user=actor, case=case):
        raise PermissionDenied
    if (
        target_status not in ALLOWED_TRANSITIONS[case.status]
        or target_status not in _enabled_statuses(case)
    ):
        raise ValidationError(_("This status transition is not allowed."))
    _validate_case_requirements(case=case, target_status=target_status)
    reason = " ".join(reason.split())
    if target_status in {
        LegalizationCase.Status.REJECTED,
        LegalizationCase.Status.CLOSED,
    } and not reason:
        raise ValidationError(_("A reason is required for this transition."))
    previous = case.status
    case.status = target_status
    case.modified_by = actor
    case.full_clean()
    case.save(update_fields=("status", "modified_by"))
    LegalizationStatusHistory.objects.create(
        case=case,
        from_status=previous,
        to_status=target_status,
        actor=actor,
        reason=reason,
    )
    return case


def _normalized_authority_payload(
    *,
    event_type,
    occurred_on,
    authority_config,
    authority_snapshot,
    channel,
    reference_number,
    response_deadline,
    valid_from,
    valid_until,
    evidence_document,
    details,
):
    return {
        "event_type": event_type,
        "occurred_on": occurred_on,
        "authority_config_id": authority_config.pk,
        "authority": authority_snapshot["name"],
        "authority_snapshot": authority_snapshot,
        "channel": channel,
        "reference_number": " ".join(reference_number.split()),
        "response_deadline": response_deadline,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "evidence_document_id": evidence_document.pk,
        "details": details.strip(),
    }


def _authority_event_matches(*, event, payload, actor):
    return event.actor_id == actor.pk and all(
        getattr(event, field) == value for field, value in payload.items()
    )


def _apply_authority_event_to_case(*, case, event_type, payload, actor):
    previous = case.status
    target_status = previous
    if event_type == LegalizationAuthorityEvent.EventType.SUBMITTED:
        target_status = LegalizationCase.Status.SUBMITTED
    elif event_type == LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED:
        target_status = LegalizationCase.Status.ADDITIONAL_INFORMATION
        case.deadline = payload["response_deadline"]
    elif event_type == LegalizationAuthorityEvent.EventType.INFORMATION_RESPONDED:
        target_status = LegalizationCase.Status.SUBMITTED
        case.deadline = None
    elif event_type == LegalizationAuthorityEvent.EventType.APPROVED:
        target_status = LegalizationCase.Status.APPROVED
        case.deadline = None
        case.valid_from = payload["valid_from"]
        case.valid_until = payload["valid_until"]
    elif event_type == LegalizationAuthorityEvent.EventType.REJECTED:
        target_status = LegalizationCase.Status.REJECTED
        case.deadline = None

    if payload["reference_number"]:
        case.reference_number = payload["reference_number"]
    case.status = target_status
    case.modified_by = actor
    case.full_clean()
    case.save(
        update_fields=(
            "status",
            "reference_number",
            "deadline",
            "valid_from",
            "valid_until",
            "modified_by",
        )
    )
    if target_status != previous:
        LegalizationStatusHistory.objects.create(
            case=case,
            from_status=previous,
            to_status=target_status,
            actor=actor,
            reason=f"authority:{event_type}",
        )


@transaction.atomic
def record_legalization_authority_event(
    *,
    case_uuid,
    event_type,
    occurred_on,
    authority_uuid,
    channel,
    reference_number,
    response_deadline,
    valid_from,
    valid_until,
    evidence_document_uuid,
    details,
    idempotency_key,
    actor,
):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationauthorityevent",
        "hydra_legalization.record_legalizationauthorityevent",
        "hydra_legalization.view_legalizationauthority",
        "hydra_documents.view_privatedocument",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    case = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if not user_can_operate_legalization_case(user=actor, case=case):
        raise PermissionDenied
    authority_snapshot = next(
        (
            row
            for row in case.procedure_snapshot.get("authorities", [])
            if isinstance(row, dict) and row.get("uuid") == str(authority_uuid)
        ),
        None,
    )
    if authority_snapshot is None:
        raise ValidationError(
            {"authority_config": _("The authority is unavailable for this case policy.")}
        )
    authority_pk = (
        authorities_for_case_snapshot(user=actor, case=case)
        .filter(uuid=authority_uuid)
        .values_list("pk", flat=True)
        .first()
    )
    if authority_pk is None:
        raise ValidationError(
            {"authority_config": _("The authority is unavailable for this case policy.")}
        )
    authority_config = LegalizationAuthority.objects.select_for_update().get(
        pk=authority_pk
    )
    evidence = (
        visible_private_documents_for_case(user=actor, case=case)
        .select_for_update()
        .filter(uuid=evidence_document_uuid)
        .first()
    )
    if evidence is None or not evidence.is_downloadable:
        raise ValidationError(
            {"evidence_document": _("The evidence document is unavailable for this case.")}
        )
    payload = _normalized_authority_payload(
        event_type=event_type,
        occurred_on=occurred_on,
        authority_config=authority_config,
        authority_snapshot=authority_snapshot,
        channel=channel,
        reference_number=reference_number,
        response_deadline=response_deadline,
        valid_from=valid_from,
        valid_until=valid_until,
        evidence_document=evidence,
        details=details,
    )
    existing = (
        LegalizationAuthorityEvent.objects.select_related("evidence_document")
        .filter(case=case, idempotency_key=idempotency_key)
        .first()
    )
    if existing:
        if not _authority_event_matches(event=existing, payload=payload, actor=actor):
            raise ValidationError(_("This request identifier was already used with different data."))
        return existing, False

    allowed = AUTHORITY_EVENTS_BY_STATUS.get(case.status, set())
    target_status = AUTHORITY_EVENT_TARGET_STATUS.get(event_type, case.status)
    if event_type not in allowed or target_status not in _enabled_statuses(case):
        raise ValidationError({"event_type": _("This authority event is not allowed for the current status.")})
    _validate_case_requirements(
        case=case,
        target_status=target_status,
        proposed_document=evidence,
    )
    latest = case.authority_events.order_by("-occurred_on", "-recorded_at", "-pk").first()
    if latest and occurred_on < latest.occurred_on:
        raise ValidationError(
            {"occurred_on": _("The event date cannot precede the latest recorded authority event.")}
        )

    event = LegalizationAuthorityEvent(
        case=case,
        idempotency_key=idempotency_key,
        evidence_document=evidence,
        evidence_sha256=evidence.sha256,
        actor=actor,
        **payload,
    )
    event.full_clean()
    _apply_authority_event_to_case(
        case=case,
        event_type=event_type,
        payload=payload,
        actor=actor,
    )
    event.save()
    document_role = {
        LegalizationAuthorityEvent.EventType.SUBMITTED: LegalizationCaseDocument.Role.APPLICATION,
        LegalizationAuthorityEvent.EventType.INFORMATION_RESPONDED: LegalizationCaseDocument.Role.APPLICATION,
        LegalizationAuthorityEvent.EventType.APPROVED: LegalizationCaseDocument.Role.DECISION,
        LegalizationAuthorityEvent.EventType.REJECTED: LegalizationCaseDocument.Role.DECISION,
    }.get(event_type, LegalizationCaseDocument.Role.OTHER)
    LegalizationCaseDocument.objects.get_or_create(
        case=case,
        document=evidence,
        defaults={
            "role": document_role,
            "created_by": actor,
            "modified_by": actor,
        },
    )
    return event, True


@transaction.atomic
def attach_private_document(*, case_uuid, document_uuid, role, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.link_privatedocument",
        "hydra_documents.view_privatedocument",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    case = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if not user_can_operate_legalization_case(user=actor, case=case):
        raise PermissionDenied
    document = available_private_documents_for_case(user=actor, case=case).filter(
        uuid=document_uuid
    ).first()
    existing = LegalizationCaseDocument.objects.filter(
        case=case, document__uuid=document_uuid
    ).first()
    if existing:
        return existing
    if document is None:
        raise ValidationError(_("The document is unavailable for this case."))
    link = LegalizationCaseDocument(
        case=case,
        document=document,
        role=role,
        created_by=actor,
        modified_by=actor,
    )
    link.full_clean()
    link.save()
    return link


def _configuration_company_allowed(*, actor, company):
    if company is None:
        return actor.is_superuser
    return actor.is_superuser or company.pk in company_ids_for_user(user=actor)


def _authority_configuration_snapshot(authority):
    return {**authority.snapshot(), "is_active": authority.is_active}


def _procedure_configuration_snapshot(procedure):
    return {
        **procedure.rules_snapshot(company_id=procedure.company_id),
        "is_active": procedure.is_active,
        "description": procedure.description,
        "authority_uuids": sorted(
            str(value)
            for value in procedure.authorities.values_list("uuid", flat=True)
        ),
    }


def _requirement_configuration_snapshot(requirement):
    return {
        "uuid": str(requirement.uuid),
        "procedure_uuid": str(requirement.procedure.uuid),
        "code": requirement.code,
        "name": requirement.name,
        "document_type_uuid": str(requirement.document_type.uuid),
        "required_before_status": requirement.required_before_status,
        "sort_order": requirement.sort_order,
        "is_active": requirement.is_active,
    }


def _record_configuration_event(
    *, entity_type, entity_uuid, before, after, actor
):
    LegalizationConfigurationEvent.objects.create(
        entity_type=entity_type,
        entity_uuid=entity_uuid,
        action=(
            LegalizationConfigurationEvent.Action.UPDATED
            if before
            else LegalizationConfigurationEvent.Action.CREATED
        ),
        before_snapshot=before,
        after_snapshot=after,
        actor=actor,
    )


@transaction.atomic
def adopt_legacy_legalization_case_policy(
    *, case_uuid, authority_uuids, reason, actor
):
    """Resolve the one-time authority gap produced by unknowable legacy data."""

    if not actor.is_superuser:
        raise PermissionDenied
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError({"reason": _("A legacy policy adoption reason is required.")})
    requested = {str(value) for value in authority_uuids}
    if not requested:
        raise ValidationError(
            {"authority": _("Choose at least one approved authority.")}
        )
    case = LegalizationCase.objects.select_for_update().filter(uuid=case_uuid).first()
    if case is None:
        raise ValidationError({"case": _("The legalization case was not found.")})
    before = deepcopy(case.procedure_snapshot)
    if (
        not isinstance(before, dict)
        or not before.get("legacy_authority_policy_pending")
        or before.get("authorities")
    ):
        raise ValidationError(
            {"case": _("This case does not require legacy authority policy adoption.")}
        )
    authorities = list(
        LegalizationAuthority.objects.select_for_update()
        .filter(uuid__in=requested, is_active=True)
        .filter(Q(company__isnull=True) | Q(company_id=case.company_id))
        .order_by("pk")
    )
    if {str(authority.uuid) for authority in authorities} != requested:
        raise ValidationError(
            {"authority": _("An authority is inactive or outside the case company.")}
        )
    after = deepcopy(before)
    after["authorities"] = [authority.snapshot() for authority in authorities]
    after["requires_authority"] = True
    after["legacy_authority_policy_pending"] = False
    LegalizationCase._base_manager.filter(pk=case.pk).update(
        procedure_snapshot=after
    )
    event = LegalizationConfigurationEvent.objects.create(
        entity_type=LegalizationConfigurationEvent.EntityType.CASE_POLICY,
        entity_uuid=case.uuid,
        action=LegalizationConfigurationEvent.Action.ADOPTED,
        before_snapshot=before,
        after_snapshot=after,
        reason=reason,
        actor=actor,
    )
    case.procedure_snapshot = after
    return case, event


@transaction.atomic
def save_legalization_authority(*, actor, authority, cleaned_data):
    creating = not authority.pk
    _require(
        actor,
        "hydra_legalization.view_legalizationauthority",
        (
            "hydra_legalization.add_legalizationauthority"
            if creating
            else "hydra_legalization.change_legalizationauthority"
        ),
    )
    current = None
    before = {}
    if not creating:
        current = LegalizationAuthority.objects.select_for_update().get(pk=authority.pk)
        before = _authority_configuration_snapshot(current)
    company = cleaned_data["company"]
    if not _configuration_company_allowed(actor=actor, company=company):
        raise PermissionDenied
    if current and current.company_id != getattr(company, "pk", None):
        raise ValidationError({"company": _("An authority scope cannot be changed.")})
    target = current or authority
    for field in (
        "company",
        "code",
        "name",
        "jurisdiction",
        "allowed_channels",
        "is_active",
    ):
        setattr(target, field, cleaned_data[field])
    if creating:
        target.created_by = actor
    target.modified_by = actor
    target.full_clean()
    target.save()
    _record_configuration_event(
        entity_type=LegalizationConfigurationEvent.EntityType.AUTHORITY,
        entity_uuid=target.uuid,
        before=before,
        after=_authority_configuration_snapshot(target),
        actor=actor,
    )
    return target


@transaction.atomic
def save_legalization_procedure(*, actor, procedure, cleaned_data):
    creating = not procedure.pk
    _require(
        actor,
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_legalization.view_legalizationauthority",
        (
            "hydra_legalization.add_legalizationproceduretype"
            if creating
            else "hydra_legalization.change_legalizationproceduretype"
        ),
    )
    current = None
    before = {}
    if not creating:
        current = LegalizationProcedureType.objects.select_for_update().get(
            pk=procedure.pk
        )
        before = _procedure_configuration_snapshot(current)
    company = cleaned_data["company"]
    if not _configuration_company_allowed(actor=actor, company=company):
        raise PermissionDenied
    if current and current.company_id != getattr(company, "pk", None):
        raise ValidationError({"company": _("A procedure scope cannot be changed.")})
    authorities = list(cleaned_data["authorities"])
    visible_authorities = set(
        legalization_authorities_for_user(
            user=actor, company=company
        ).filter(pk__in=[row.pk for row in authorities]).values_list("pk", flat=True)
    )
    if visible_authorities != {row.pk for row in authorities}:
        raise ValidationError({"authorities": _("An authority is outside this scope.")})
    if company is None and any(row.company_id is not None for row in authorities):
        raise ValidationError(
            {"authorities": _("A global procedure can use only global authorities.")}
        )
    if cleaned_data["requires_authority"] and not authorities:
        raise ValidationError(
            {"authorities": _("Choose at least one approved authority.")}
        )
    enabled_statuses = set(cleaned_data["enabled_statuses"])
    mandatory = {
        LegalizationCase.Status.DRAFT,
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.APPROVED,
        LegalizationCase.Status.REJECTED,
        LegalizationCase.Status.EXPIRED,
        LegalizationCase.Status.CLOSED,
    }
    if not mandatory.issubset(enabled_statuses):
        raise ValidationError(
            {"enabled_statuses": _("Every mandatory core status must remain enabled.")}
        )
    target = current or procedure
    for field in (
        "company",
        "code",
        "name",
        "case_type",
        "description",
        "default_deadline_days",
        "renewal_lead_days",
        "requires_authority",
        "is_active",
    ):
        setattr(target, field, cleaned_data[field])
    if creating:
        target.created_by = actor
    target.modified_by = actor
    target.full_clean()
    target.save()
    target.authorities.set(authorities)
    status_labels = dict(LegalizationCase.Status.choices)
    status_order = {value: index for index, (value, _label) in enumerate(
        LegalizationCase.Status.choices
    )}
    for status, label in LegalizationCase.Status.choices:
        row, _created = LegalizationProcedureStatus.objects.get_or_create(
            procedure=target,
            status=status,
            defaults={
                "label": str(label),
                "sort_order": status_order[status],
                "created_by": actor,
                "modified_by": actor,
            },
        )
        row.label = str(status_labels[status])
        row.sort_order = status_order[status]
        row.is_active = status in enabled_statuses
        row.modified_by = actor
        row.full_clean()
        row.save()
    _record_configuration_event(
        entity_type=LegalizationConfigurationEvent.EntityType.PROCEDURE,
        entity_uuid=target.uuid,
        before=before,
        after=_procedure_configuration_snapshot(target),
        actor=actor,
    )
    return target


@transaction.atomic
def save_legalization_requirement(*, actor, requirement, cleaned_data):
    creating = not requirement.pk
    _require(
        actor,
        "hydra_legalization.view_legalizationprocedurerequirement",
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_documents.view_privatedocumenttype",
        (
            "hydra_legalization.add_legalizationprocedurerequirement"
            if creating
            else "hydra_legalization.change_legalizationprocedurerequirement"
        ),
    )
    current = None
    before = {}
    if not creating:
        current = LegalizationProcedureRequirement.objects.select_for_update().get(
            pk=requirement.pk
        )
        before = _requirement_configuration_snapshot(current)
    procedure = legalization_procedures_for_user(
        user=actor, include_inactive=True
    ).filter(pk=cleaned_data["procedure"].pk).first()
    if procedure is None:
        raise PermissionDenied
    if current and current.procedure_id != procedure.pk:
        raise ValidationError({"procedure": _("A requirement procedure cannot be changed.")})
    document_type = document_types_for_user(
        user=actor, include_inactive=True
    ).filter(pk=cleaned_data["document_type"].pk).first()
    if document_type is None or document_type.company_id not in (
        None,
        procedure.company_id,
    ):
        raise ValidationError(
            {"document_type": _("The document type is outside this procedure scope.")}
        )
    enabled_statuses = set(
        procedure.status_rules.filter(is_active=True).values_list("status", flat=True)
    )
    if cleaned_data["required_before_status"] not in enabled_statuses:
        raise ValidationError(
            {"required_before_status": _("The selected status is disabled for this procedure.")}
        )
    target = current or requirement
    for field in (
        "procedure",
        "code",
        "name",
        "required_before_status",
        "sort_order",
        "is_active",
    ):
        setattr(target, field, cleaned_data[field])
    target.document_type = document_type
    if creating:
        target.created_by = actor
    target.modified_by = actor
    target.full_clean()
    target.save()
    _record_configuration_event(
        entity_type=LegalizationConfigurationEvent.EntityType.REQUIREMENT,
        entity_uuid=target.uuid,
        before=before,
        after=_requirement_configuration_snapshot(target),
        actor=actor,
    )
    return target
