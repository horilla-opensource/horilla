from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from hydra_legalization.models import (
    LegalizationCase,
    LegalizationCaseDocument,
    LegalizationStatusHistory,
)
from hydra_legalization.selectors import (
    available_private_documents_for_case,
    legalization_case_for_user,
)
from hydra_people.models import Person
from hydra_people.selectors import people_for_user, person_for_user


ALLOWED_TRANSITIONS = {
    LegalizationCase.Status.DRAFT: {
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.COLLECTING_DOCUMENTS: {
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.SUBMITTED: {
        LegalizationCase.Status.ADDITIONAL_INFORMATION,
        LegalizationCase.Status.APPROVED,
        LegalizationCase.Status.REJECTED,
    },
    LegalizationCase.Status.ADDITIONAL_INFORMATION: {
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.REJECTED,
    },
    LegalizationCase.Status.APPROVED: {
        LegalizationCase.Status.EXPIRED,
        LegalizationCase.Status.CLOSED,
    },
    LegalizationCase.Status.REJECTED: {LegalizationCase.Status.CLOSED},
    LegalizationCase.Status.EXPIRED: {LegalizationCase.Status.CLOSED},
    LegalizationCase.Status.CLOSED: set(),
}


def available_transitions(case):
    allowed = ALLOWED_TRANSITIONS[case.status]
    return [choice for choice in LegalizationCase.Status.choices if choice[0] in allowed]


def _require(actor, *permissions):
    if not actor.has_perms(permissions):
        raise PermissionDenied


def _validate_responsible(*, responsible, person):
    required = (
        "hydra_legalization.view_legalizationcase",
        "hydra_people.view_person",
    )
    if not responsible.is_active or not responsible.has_perms(required):
        raise ValidationError(
            {"responsible": _("The responsible user lacks required permissions.")}
        )
    if not people_for_user(user=responsible).filter(pk=person.pk).exists():
        raise ValidationError(
            {"responsible": _("The responsible user cannot access this person.")}
        )


@transaction.atomic
def create_legalization_case(*, case, actor):
    _require(
        actor,
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationcase",
        "hydra_people.view_person",
    )
    person = person_for_user(
        user=actor, person_uuid=case.person.uuid, permission="view_person"
    )
    case.person = Person.objects.select_for_update().get(pk=person.pk)
    case.status = LegalizationCase.Status.DRAFT
    if case.responsible_id != actor.pk:
        _require(actor, "hydra_legalization.assign_legalizationcase")
    _validate_responsible(responsible=case.responsible, person=case.person)
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
    return case


@transaction.atomic
def update_legalization_case(*, case, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case.uuid)
    current = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if current.responsible_id != case.responsible_id:
        _require(actor, "hydra_legalization.assign_legalizationcase")
    _validate_responsible(responsible=case.responsible, person=current.person)
    for field in (
        "case_type",
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


@transaction.atomic
def transition_legalization_case(*, case_uuid, target_status, reason, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.transition_legalizationcase",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    case = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    if target_status not in ALLOWED_TRANSITIONS[case.status]:
        raise ValidationError(_("This status transition is not allowed."))
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
