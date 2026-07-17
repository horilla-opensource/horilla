from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_legalization.models import (
    LegalizationCase,
    LegalizationCaseDelegation,
    LegalizationWorkEvent,
)
from hydra_legalization.selectors import (
    legalization_case_for_user,
    user_can_operate_legalization_case,
)
from hydra_people.models import Person
from hydra_people.selectors import people_for_user
from hydra_notifications.models import NotificationKind, NotificationTargetKind
from hydra_notifications.services import send_hydra_notification


def _require(actor, *permissions):
    if not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def validate_legalization_responsible(*, responsible, person, field="responsible"):
    required = (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_legalization.view_legalizationauthority",
        "hydra_people.view_person",
    )
    if not responsible.is_active or not responsible.has_perms(required):
        raise ValidationError(
            {field: _("The selected user lacks required legalization permissions.")}
        )
    if not people_for_user(user=responsible).filter(pk=person.pk).exists():
        raise ValidationError(
            {field: _("The selected user cannot access this person.")}
        )


def validate_legalization_deputy(*, deputy, person):
    required = (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
        "hydra_legalization.transition_legalizationcase",
        "hydra_legalization.link_privatedocument",
        "hydra_legalization.view_legalizationauthorityevent",
        "hydra_legalization.record_legalizationauthorityevent",
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_legalization.view_legalizationauthority",
        "hydra_legalization.view_legalizationrenewallink",
        "hydra_legalization.create_legalizationrenewallink",
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationcasedelegation",
        "hydra_legalization.view_legalizationworkevent",
        "hydra_people.view_person",
        "hydra_documents.view_privatedocument",
        "recruitment.view_candidate",
    )
    if not deputy.is_active or not deputy.has_perms(required):
        raise ValidationError(
            {"deputy": _("The deputy lacks required operational permissions.")}
        )
    if not people_for_user(user=deputy).filter(pk=person.pk).exists():
        raise ValidationError({"deputy": _("The deputy cannot access this person.")})


def _notification_recipient(*, actor, target):
    if target is None or actor is None or target.pk == actor.pk:
        return None
    return target


def _create_work_event(
    *,
    case,
    action,
    actor,
    from_user,
    to_user,
    reason,
    delegation=None,
    effective_from=None,
    effective_until=None,
):
    recipient = _notification_recipient(actor=actor, target=to_user)
    event = LegalizationWorkEvent(
        case=case,
        delegation=delegation,
        action=action,
        from_user=from_user,
        to_user=to_user,
        actor=actor,
        source=LegalizationWorkEvent.Source.USER,
        recipient=recipient,
        reason=reason,
        effective_from=effective_from,
        effective_until=effective_until,
        notification_status=(
            LegalizationWorkEvent.NotificationStatus.PENDING
            if recipient is not None
            else LegalizationWorkEvent.NotificationStatus.NOT_APPLICABLE
        ),
    )
    event.full_clean()
    event.save()
    if recipient is not None:
        transaction.on_commit(lambda: dispatch_legalization_work_event(event.pk))
    return event


def record_initial_responsibility(*, case, actor):
    return _create_work_event(
        case=case,
        action=LegalizationWorkEvent.Action.RESPONSIBILITY_ASSIGNED,
        actor=actor,
        from_user=None,
        to_user=case.responsible,
        reason="Case created",
    )


def _normalize_reason(reason, *, field="reason"):
    normalized = " ".join(reason.split())
    if not normalized:
        raise ValidationError({field: _("A reason is required.")})
    return normalized[:255]


def _event_recipient_is_still_eligible(event):
    recipient = event.recipient
    if recipient is None or not recipient.is_active:
        return False
    if not recipient.has_perms(
        (
            "hydra_legalization.view_legalizationcase",
            "hydra_people.view_person",
        )
    ):
        return False
    if not people_for_user(user=recipient).filter(pk=event.case.person_id).exists():
        return False
    if event.action in (
        LegalizationWorkEvent.Action.RESPONSIBILITY_ASSIGNED,
        LegalizationWorkEvent.Action.RESPONSIBILITY_TRANSFERRED,
    ):
        return event.case.responsible_id == recipient.pk
    if event.action == LegalizationWorkEvent.Action.DELEGATION_CREATED:
        delegation = event.delegation
        return (
            delegation is not None
            and delegation.is_active
            and delegation.deputy_id == recipient.pk
            and delegation.principal_id == event.case.responsible_id
        )
    return event.action == LegalizationWorkEvent.Action.DELEGATION_REVOKED


def _notification_kind(event):
    return {
        LegalizationWorkEvent.Action.RESPONSIBILITY_ASSIGNED: NotificationKind.LEGALIZATION_ASSIGNED,
        LegalizationWorkEvent.Action.RESPONSIBILITY_TRANSFERRED: NotificationKind.LEGALIZATION_TRANSFERRED,
        LegalizationWorkEvent.Action.DELEGATION_CREATED: NotificationKind.LEGALIZATION_DEPUTY,
        LegalizationWorkEvent.Action.DELEGATION_REVOKED: NotificationKind.LEGALIZATION_DEPUTY_REVOKED,
    }[event.action]


def dispatch_legalization_work_event(event_id):
    try:
        with transaction.atomic():
            event = (
                LegalizationWorkEvent.objects.select_for_update(of=("self",))
                .select_related(
                    "actor",
                    "recipient",
                    "case__person",
                    "case__responsible",
                    "delegation",
                )
                .get(pk=event_id)
            )
            if event.notification_status in (
                LegalizationWorkEvent.NotificationStatus.SENT,
                LegalizationWorkEvent.NotificationStatus.NOT_APPLICABLE,
            ):
                return True
            if event.actor_id is None or not _event_recipient_is_still_eligible(event):
                event.notification_status = (
                    LegalizationWorkEvent.NotificationStatus.NOT_APPLICABLE
                )
                event.notification_last_attempt_at = timezone.now()
                event.notification_error_code = ""
                event.save(
                    update_fields=(
                        "notification_status",
                        "notification_last_attempt_at",
                        "notification_error_code",
                    )
                )
                return True

            redirect = (
                reverse("hydra-legalization-list")
                if event.action == LegalizationWorkEvent.Action.DELEGATION_REVOKED
                else event.case.get_absolute_url()
            )
            notification = send_hydra_notification(
                actor=event.actor,
                recipient=event.recipient,
                kind=_notification_kind(event),
                target_kind=NotificationTargetKind.LEGALIZATION_CASE,
                target_uuid=event.case.uuid,
                redirect_path=redirect,
                idempotency_key=f"legalization-work:{event.uuid}",
            )
            event.notification = notification
            event.notification_status = LegalizationWorkEvent.NotificationStatus.SENT
            event.notification_attempts += 1
            event.notification_last_attempt_at = timezone.now()
            event.notification_error_code = ""
            event.save(
                update_fields=(
                    "notification",
                    "notification_status",
                    "notification_attempts",
                    "notification_last_attempt_at",
                    "notification_error_code",
                )
            )
            return True
    except Exception as error:
        LegalizationWorkEvent.objects.filter(pk=event_id).update(
            notification_status=LegalizationWorkEvent.NotificationStatus.FAILED,
            notification_attempts=F("notification_attempts") + 1,
            notification_last_attempt_at=timezone.now(),
            notification_error_code=type(error).__name__[:80],
        )
        return False


def dispatch_pending_legalization_work_notifications(*, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    event_ids = list(
        LegalizationWorkEvent.objects.filter(
            notification_status__in=(
                LegalizationWorkEvent.NotificationStatus.PENDING,
                LegalizationWorkEvent.NotificationStatus.FAILED,
            ),
            notification_attempts__lt=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        )
        .order_by("occurred_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = 0
    for event_id in event_ids:
        if dispatch_legalization_work_event(event_id):
            sent += 1
        else:
            failed += 1
    return sent, failed, len(event_ids)


@transaction.atomic
def create_legalization_delegation(
    *, case_uuid, deputy, valid_from, valid_until, reason, actor
):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationcasedelegation",
        "hydra_legalization.manage_legalizationdelegation",
        "hydra_people.view_person",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    Person.objects.select_for_update().get(pk=visible.person_id)
    case = LegalizationCase.objects.select_for_update().select_related(
        "person", "responsible"
    ).get(pk=visible.pk)
    if not actor.is_superuser and case.responsible_id != actor.pk:
        raise PermissionDenied
    reason = _normalize_reason(reason)
    today = timezone.localdate()
    if valid_from is None or valid_until is None:
        raise ValidationError({"valid_until": _("Choose both delegation dates.")})
    if valid_from < today:
        raise ValidationError({"valid_from": _("A delegation cannot start in the past.")})
    if valid_until < valid_from:
        raise ValidationError({"valid_until": _("The end date cannot precede the start date.")})
    if (valid_until - valid_from).days >= LegalizationCaseDelegation.MAX_DURATION_DAYS:
        raise ValidationError(
            {"valid_until": _("A delegation cannot exceed 90 calendar days.")}
        )
    validate_legalization_deputy(deputy=deputy, person=case.person)
    if deputy.pk == case.responsible_id:
        raise ValidationError(
            {"deputy": _("The responsible user cannot be their own deputy.")}
        )

    overlapping = list(
        LegalizationCaseDelegation.objects.select_for_update()
        .filter(
            case=case,
            is_active=True,
            valid_from__lte=valid_until,
            valid_until__gte=valid_from,
        )
        .order_by("pk")
    )
    if overlapping:
        existing = overlapping[0]
        if (
            len(overlapping) == 1
            and existing.principal_id == case.responsible_id
            and existing.deputy_id == deputy.pk
            and existing.valid_from == valid_from
            and existing.valid_until == valid_until
            and existing.reason == reason
        ):
            return existing, False
        raise ValidationError(
            _("This case already has a delegation covering part of that period.")
        )

    delegation = LegalizationCaseDelegation(
        case=case,
        principal=case.responsible,
        deputy=deputy,
        valid_from=valid_from,
        valid_until=valid_until,
        reason=reason,
        created_by=actor,
        modified_by=actor,
    )
    delegation.full_clean()
    delegation.save()
    _create_work_event(
        case=case,
        delegation=delegation,
        action=LegalizationWorkEvent.Action.DELEGATION_CREATED,
        actor=actor,
        from_user=case.responsible,
        to_user=deputy,
        reason=reason,
        effective_from=valid_from,
        effective_until=valid_until,
    )
    return delegation, True


def _revoke_locked_delegation(*, delegation, reason, actor):
    if not delegation.is_active:
        return False
    delegation.is_active = False
    delegation.revoked_at = timezone.now()
    delegation.revoked_by = actor
    delegation.revocation_reason = reason
    delegation.modified_by = actor
    delegation.full_clean()
    delegation.save(
        update_fields=(
            "is_active",
            "revoked_at",
            "revoked_by",
            "revocation_reason",
            "modified_by",
        )
    )
    _create_work_event(
        case=delegation.case,
        delegation=delegation,
        action=LegalizationWorkEvent.Action.DELEGATION_REVOKED,
        actor=actor,
        from_user=delegation.principal,
        to_user=delegation.deputy,
        reason=reason,
        effective_from=delegation.valid_from,
        effective_until=delegation.valid_until,
    )
    return True


@transaction.atomic
def revoke_legalization_delegation(*, delegation_uuid, reason, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationcasedelegation",
        "hydra_legalization.manage_legalizationdelegation",
    )
    delegation_view = (
        LegalizationCaseDelegation.objects.select_related("case__person")
        .filter(uuid=delegation_uuid)
        .first()
    )
    if delegation_view is None:
        raise LegalizationCaseDelegation.DoesNotExist
    visible = legalization_case_for_user(
        user=actor,
        case_uuid=delegation_view.case.uuid,
    )
    Person.objects.select_for_update().get(pk=visible.person_id)
    case = LegalizationCase.objects.select_for_update().get(pk=visible.pk)
    delegation = (
        LegalizationCaseDelegation.objects.select_for_update()
        .select_related("case", "principal", "deputy")
        .get(pk=delegation_view.pk, case=case)
    )
    if not actor.is_superuser and case.responsible_id != actor.pk:
        raise PermissionDenied
    reason = _normalize_reason(reason)
    return delegation, _revoke_locked_delegation(
        delegation=delegation,
        reason=reason,
        actor=actor,
    )


@transaction.atomic
def reassign_legalization_case(*, case_uuid, new_responsible, reason, actor):
    _require(
        actor,
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
        "hydra_legalization.assign_legalizationcase",
        "hydra_people.view_person",
    )
    visible = legalization_case_for_user(user=actor, case_uuid=case_uuid)
    person = Person.objects.select_for_update().get(pk=visible.person_id)
    case = LegalizationCase.objects.select_for_update().select_related(
        "person", "responsible"
    ).get(pk=visible.pk)
    reason = _normalize_reason(reason)
    validate_legalization_responsible(
        responsible=new_responsible,
        person=person,
        field="new_responsible",
    )
    if case.responsible_id == new_responsible.pk:
        return case, False

    previous = case.responsible
    today = timezone.localdate()
    delegations = list(
        LegalizationCaseDelegation.objects.select_for_update()
        .select_related("case", "principal", "deputy")
        .filter(case=case, is_active=True, valid_until__gte=today)
        .order_by("pk")
    )
    revocation_reason = f"Responsibility transferred: {reason}"[:255]
    for delegation in delegations:
        _revoke_locked_delegation(
            delegation=delegation,
            reason=revocation_reason,
            actor=actor,
        )

    case.responsible = new_responsible
    case.modified_by = actor
    case.full_clean()
    case.save(update_fields=("responsible", "modified_by"))
    _create_work_event(
        case=case,
        action=LegalizationWorkEvent.Action.RESPONSIBILITY_TRANSFERRED,
        actor=actor,
        from_user=previous,
        to_user=new_responsible,
        reason=reason,
    )
    return case, True


def actor_can_manage_case_work(*, actor, case):
    return user_can_operate_legalization_case(user=actor, case=case)
