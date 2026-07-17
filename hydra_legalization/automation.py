from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from hydra_legalization.models import (
    LegalizationAutomationEvent,
    LegalizationCase,
    LegalizationStatusHistory,
)
from hydra_legalization.selectors import legalization_cases_for_user
from hydra_notifications.models import NotificationKind, NotificationTargetKind
from hydra_notifications.services import send_hydra_notification


ACTIVE_WORKFLOW_STATUSES = (
    LegalizationCase.Status.DRAFT,
    LegalizationCase.Status.COLLECTING_DOCUMENTS,
    LegalizationCase.Status.SUBMITTED,
    LegalizationCase.Status.ADDITIONAL_INFORMATION,
)


@dataclass(frozen=True)
class LegalizationAutomationResult:
    cases_selected: int
    events_created: int
    cases_expired: int
    notifications_sent: int
    notifications_failed: int
    notifications_selected: int


def _nearest_crossed_threshold(*, due_date, today, thresholds):
    days_remaining = (due_date - today).days
    if days_remaining < 0:
        return None
    crossed = [int(days) for days in thresholds if days_remaining <= int(days)]
    return min(crossed) if crossed else None


def _user_can_receive_case(*, user, case_id):
    return bool(
        user.is_active
        and user.has_perms(
            (
                "hydra_legalization.view_legalizationcase",
                "hydra_people.view_person",
            )
        )
        and legalization_cases_for_user(user=user).filter(pk=case_id).exists()
    )


def _event_recipient_is_still_eligible(event):
    if not _user_can_receive_case(
        user=event.recipient, case_id=event.case_id
    ):
        return False
    if event.event_type in (
        LegalizationAutomationEvent.EventType.DEADLINE_REMINDER,
        LegalizationAutomationEvent.EventType.VALIDITY_REMINDER,
    ):
        return event.recipient_id == event.case.responsible_id
    return bool(
        event.recipient_id == event.case.responsible_id
        or event.recipient.has_perm(
            "hydra_legalization.receive_legalization_escalations"
        )
    )


def _scoped_escalation_recipients(case):
    user_model = get_user_model()
    explicit_permission = (
        Q(
            user_permissions__content_type__app_label="hydra_legalization",
            user_permissions__codename="receive_legalization_escalations",
        )
        | Q(
            groups__permissions__content_type__app_label="hydra_legalization",
            groups__permissions__codename="receive_legalization_escalations",
        )
        | Q(is_superuser=True)
    )
    candidates = user_model._default_manager.filter(
        is_active=True
    ).filter(explicit_permission).distinct()
    return [
        user
        for user in candidates
        if _user_can_receive_case(user=user, case_id=case.pk)
    ]


def _event_recipients(case, *, include_escalation):
    recipients = [case.responsible]
    if include_escalation:
        recipients.extend(_scoped_escalation_recipients(case))
    unique = {}
    for recipient in recipients:
        unique.setdefault(recipient.pk, recipient)
    return tuple(unique.values())


def _ensure_events(
    *, case, event_type, due_date, threshold_days, include_escalation
):
    created_ids = []
    for recipient in _event_recipients(
        case, include_escalation=include_escalation
    ):
        event, created = LegalizationAutomationEvent.objects.get_or_create(
            case=case,
            event_type=event_type,
            due_date=due_date,
            threshold_days=threshold_days,
            recipient=recipient,
        )
        if created:
            created_ids.append(event.pk)
    return created_ids


def generate_legalization_automation_events(*, today=None, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    today = today or timezone.localdate()
    deadline_thresholds = settings.HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS
    validity_thresholds = settings.HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS
    deadline_horizon = today + timedelta(days=max(deadline_thresholds))
    validity_horizon = today + timedelta(days=max(validity_thresholds))
    case_ids = list(
        LegalizationCase.objects.filter(
            Q(
                status__in=ACTIVE_WORKFLOW_STATUSES,
                deadline__isnull=False,
                deadline__lte=deadline_horizon,
            )
            | Q(
                status=LegalizationCase.Status.APPROVED,
                valid_until__isnull=False,
                valid_until__lte=validity_horizon,
            )
        )
        .order_by("deadline", "valid_until", "pk")
        .values_list("pk", flat=True)[:limit]
    )

    created_count = 0
    expired_count = 0
    for case_id in case_ids:
        with transaction.atomic():
            case = LegalizationCase.objects.select_for_update().select_related(
                "responsible"
            ).get(pk=case_id)
            created_ids = []
            if case.status in ACTIVE_WORKFLOW_STATUSES and case.deadline:
                if case.deadline < today:
                    created_ids.extend(
                        _ensure_events(
                            case=case,
                            event_type=(
                                LegalizationAutomationEvent.EventType.DEADLINE_OVERDUE
                            ),
                            due_date=case.deadline,
                            threshold_days=0,
                            include_escalation=True,
                        )
                    )
                else:
                    threshold = _nearest_crossed_threshold(
                        due_date=case.deadline,
                        today=today,
                        thresholds=deadline_thresholds,
                    )
                    if threshold is not None:
                        created_ids.extend(
                            _ensure_events(
                                case=case,
                                event_type=(
                                    LegalizationAutomationEvent.EventType.DEADLINE_REMINDER
                                ),
                                due_date=case.deadline,
                                threshold_days=threshold,
                                include_escalation=False,
                            )
                        )
            elif (
                case.status == LegalizationCase.Status.APPROVED
                and case.valid_until
            ):
                if case.valid_until < today:
                    previous = case.status
                    case.status = LegalizationCase.Status.EXPIRED
                    case.full_clean()
                    case.save(update_fields=("status",))
                    LegalizationStatusHistory.objects.create(
                        case=case,
                        from_status=previous,
                        to_status=LegalizationCase.Status.EXPIRED,
                        source=LegalizationStatusHistory.Source.SYSTEM,
                        actor=None,
                        reason="automatic validity expiry",
                    )
                    expired_count += 1
                    created_ids.extend(
                        _ensure_events(
                            case=case,
                            event_type=LegalizationAutomationEvent.EventType.AUTO_EXPIRED,
                            due_date=case.valid_until,
                            threshold_days=0,
                            include_escalation=True,
                        )
                    )
                else:
                    threshold = _nearest_crossed_threshold(
                        due_date=case.valid_until,
                        today=today,
                        thresholds=validity_thresholds,
                    )
                    if threshold is not None:
                        created_ids.extend(
                            _ensure_events(
                                case=case,
                                event_type=(
                                    LegalizationAutomationEvent.EventType.VALIDITY_REMINDER
                                ),
                                due_date=case.valid_until,
                                threshold_days=threshold,
                                include_escalation=False,
                            )
                        )
            created_count += len(created_ids)
    return len(case_ids), created_count, expired_count


def _notification_kind(event):
    return {
        LegalizationAutomationEvent.EventType.DEADLINE_REMINDER: NotificationKind.LEGALIZATION_DEADLINE,
        LegalizationAutomationEvent.EventType.DEADLINE_OVERDUE: NotificationKind.LEGALIZATION_OVERDUE,
        LegalizationAutomationEvent.EventType.VALIDITY_REMINDER: NotificationKind.LEGALIZATION_VALIDITY,
        LegalizationAutomationEvent.EventType.AUTO_EXPIRED: NotificationKind.LEGALIZATION_EXPIRED,
    }[event.event_type]


def dispatch_legalization_automation_event(event_id):
    try:
        with transaction.atomic():
            event = LegalizationAutomationEvent.objects.select_for_update(
                of=("self",)
            ).select_related("case", "recipient").get(pk=event_id)
            if event.notification_status in (
                LegalizationAutomationEvent.NotificationStatus.SENT,
                LegalizationAutomationEvent.NotificationStatus.NOT_APPLICABLE,
            ):
                return True
            if not _event_recipient_is_still_eligible(event):
                event.notification_status = (
                    LegalizationAutomationEvent.NotificationStatus.NOT_APPLICABLE
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

            notification = send_hydra_notification(
                actor=event.case,
                recipient=event.recipient,
                kind=_notification_kind(event),
                target_kind=NotificationTargetKind.LEGALIZATION_CASE,
                target_uuid=event.case.uuid,
                redirect_path=reverse(
                    "hydra-legalization-detail",
                    kwargs={"case_uuid": event.case.uuid},
                ),
                idempotency_key=f"legalization-automation:{event.uuid}",
            )
            event.notification = notification
            event.notification_status = (
                LegalizationAutomationEvent.NotificationStatus.SENT
            )
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
        LegalizationAutomationEvent.objects.filter(pk=event_id).update(
            notification_status=LegalizationAutomationEvent.NotificationStatus.FAILED,
            notification_attempts=F("notification_attempts") + 1,
            notification_last_attempt_at=timezone.now(),
            notification_error_code=type(error).__name__[:80],
        )
        return False


def dispatch_pending_legalization_notifications(*, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    event_ids = list(
        LegalizationAutomationEvent.objects.filter(
            notification_status__in=(
                LegalizationAutomationEvent.NotificationStatus.PENDING,
                LegalizationAutomationEvent.NotificationStatus.FAILED,
            ),
            notification_attempts__lt=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        )
        .order_by("occurred_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = 0
    for event_id in event_ids:
        if dispatch_legalization_automation_event(event_id):
            sent += 1
        else:
            failed += 1
    return sent, failed, len(event_ids)


def run_legalization_automation(*, today=None, case_limit=100, notification_limit=100):
    selected, created, expired = generate_legalization_automation_events(
        today=today,
        limit=case_limit,
    )
    sent, failed, notification_selected = (
        dispatch_pending_legalization_notifications(limit=notification_limit)
    )
    return LegalizationAutomationResult(
        cases_selected=selected,
        events_created=created,
        cases_expired=expired,
        notifications_sent=sent,
        notifications_failed=failed,
        notifications_selected=notification_selected,
    )
