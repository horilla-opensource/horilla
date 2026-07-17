from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalAutomationEvent, ArrivalPlan
from hydra_arrivals.selectors import arrival_plans_for_user
from hydra_notifications.models import NotificationKind, NotificationTargetKind
from hydra_notifications.services import send_hydra_notification


@dataclass(frozen=True)
class ArrivalAutomationResult:
    plans_selected: int
    events_created: int
    notifications_sent: int
    notifications_failed: int
    notifications_selected: int


def _nearest_crossed_threshold(*, planned_at, now, thresholds):
    seconds_remaining = (planned_at - now).total_seconds()
    if seconds_remaining < 0:
        return None
    crossed = [
        int(minutes)
        for minutes in thresholds
        if seconds_remaining <= int(minutes) * 60
    ]
    return min(crossed) if crossed else None


def _user_can_receive_plan(*, user, plan_id):
    return bool(
        user.is_active
        and arrival_plans_for_user(user=user).filter(pk=plan_id).exists()
    )


def _scoped_escalation_recipients(plan):
    user_model = get_user_model()
    candidates = user_model._default_manager.filter(is_active=True).filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__content_type__app_label="hydra_arrivals",
            user_permissions__codename="receive_arrival_escalations",
        )
        | Q(
            groups__permissions__content_type__app_label="hydra_arrivals",
            groups__permissions__codename="receive_arrival_escalations",
        )
    ).distinct()
    return [
        user
        for user in candidates
        if user.has_perm("hydra_arrivals.transition_arrivalplan")
        and _user_can_receive_plan(user=user, plan_id=plan.pk)
    ]


def _event_recipients(plan, *, include_escalation):
    recipients = [plan.coordinator]
    if include_escalation:
        recipients.extend(_scoped_escalation_recipients(plan))
    unique = {}
    for recipient in recipients:
        unique.setdefault(recipient.pk, recipient)
    return tuple(unique.values())


def _ensure_events(
    *, plan, event_type, threshold_minutes, include_escalation
):
    created_ids = []
    for recipient in _event_recipients(
        plan, include_escalation=include_escalation
    ):
        event, created = ArrivalAutomationEvent.objects.get_or_create(
            plan=plan,
            event_type=event_type,
            planned_at=plan.planned_at,
            threshold_minutes=threshold_minutes,
            recipient=recipient,
        )
        if created:
            created_ids.append(event.pk)
    return created_ids


def generate_arrival_automation_events(*, now=None, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    now = now or timezone.now()
    thresholds = settings.HYDRA_ARRIVAL_REMINDER_MINUTES
    horizon = now + timedelta(minutes=max(thresholds))
    plan_ids = list(
        ArrivalPlan.objects.filter(
            status=ArrivalPlan.Status.PLANNED,
            planned_at__lte=horizon,
        )
        .order_by("planned_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    created_count = 0
    for plan_id in plan_ids:
        with transaction.atomic():
            plan = ArrivalPlan.objects.select_for_update().select_related(
                "coordinator"
            ).get(pk=plan_id)
            if plan.status != ArrivalPlan.Status.PLANNED:
                continue
            if plan.planned_at < now:
                created = _ensure_events(
                    plan=plan,
                    event_type=ArrivalAutomationEvent.EventType.OVERDUE,
                    threshold_minutes=0,
                    include_escalation=True,
                )
            else:
                threshold = _nearest_crossed_threshold(
                    planned_at=plan.planned_at,
                    now=now,
                    thresholds=thresholds,
                )
                created = (
                    _ensure_events(
                        plan=plan,
                        event_type=ArrivalAutomationEvent.EventType.UPCOMING,
                        threshold_minutes=threshold,
                        include_escalation=False,
                    )
                    if threshold is not None
                    else []
                )
            created_count += len(created)
    return len(plan_ids), created_count


def _event_recipient_is_still_eligible(event):
    if (
        event.plan.status != ArrivalPlan.Status.PLANNED
        or event.plan.planned_at != event.planned_at
    ):
        return False
    if not _user_can_receive_plan(
        user=event.recipient, plan_id=event.plan_id
    ):
        return False
    if event.event_type == ArrivalAutomationEvent.EventType.UPCOMING:
        return event.recipient_id == event.plan.coordinator_id
    return bool(
        event.recipient_id == event.plan.coordinator_id
        or (
            event.recipient.has_perm(
                "hydra_arrivals.receive_arrival_escalations"
            )
            and event.recipient.has_perm(
                "hydra_arrivals.transition_arrivalplan"
            )
        )
    )


def dispatch_arrival_automation_event(event_id):
    try:
        with transaction.atomic():
            event = ArrivalAutomationEvent.objects.select_for_update(
                of=("self",)
            ).select_related("plan", "recipient").get(pk=event_id)
            if event.notification_status in (
                ArrivalAutomationEvent.NotificationStatus.SENT,
                ArrivalAutomationEvent.NotificationStatus.NOT_APPLICABLE,
            ):
                return True
            if not _event_recipient_is_still_eligible(event):
                event.notification_status = (
                    ArrivalAutomationEvent.NotificationStatus.NOT_APPLICABLE
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
                actor=event.plan,
                recipient=event.recipient,
                kind=(
                    NotificationKind.ARRIVAL_UPCOMING
                    if event.event_type == ArrivalAutomationEvent.EventType.UPCOMING
                    else NotificationKind.ARRIVAL_OVERDUE
                ),
                target_kind=NotificationTargetKind.ARRIVAL_PLAN,
                target_uuid=event.plan.uuid,
                redirect_path=reverse(
                    "hydra-arrival-detail",
                    kwargs={"plan_uuid": event.plan.uuid},
                ),
                idempotency_key=f"arrival-automation:{event.uuid}",
            )
            event.notification = notification
            event.notification_status = ArrivalAutomationEvent.NotificationStatus.SENT
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
        ArrivalAutomationEvent.objects.filter(pk=event_id).update(
            notification_status=ArrivalAutomationEvent.NotificationStatus.FAILED,
            notification_attempts=F("notification_attempts") + 1,
            notification_last_attempt_at=timezone.now(),
            notification_error_code=type(error).__name__[:80],
        )
        return False


def dispatch_pending_arrival_notifications(*, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    event_ids = list(
        ArrivalAutomationEvent.objects.filter(
            notification_status__in=(
                ArrivalAutomationEvent.NotificationStatus.PENDING,
                ArrivalAutomationEvent.NotificationStatus.FAILED,
            ),
            notification_attempts__lt=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        )
        .order_by("occurred_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = 0
    for event_id in event_ids:
        if dispatch_arrival_automation_event(event_id):
            sent += 1
        else:
            failed += 1
    return sent, failed, len(event_ids)


def run_arrival_automation(*, now=None, plan_limit=100, notification_limit=100):
    selected, created = generate_arrival_automation_events(
        now=now,
        limit=plan_limit,
    )
    sent, failed, notification_selected = dispatch_pending_arrival_notifications(
        limit=notification_limit
    )
    return ArrivalAutomationResult(
        plans_selected=selected,
        events_created=created,
        notifications_sent=sent,
        notifications_failed=failed,
        notifications_selected=notification_selected,
    )
