from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urljoin, urlsplit
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan, OnboardingHandoff
from hydra_arrivals.selectors import arrival_plans_for_user
from hydra_legalization.models import LegalizationCase
from hydra_legalization.selectors import legalization_cases_for_user
from hydra_notifications.models import (
    HydraNotificationEmailDelivery,
    HydraNotificationEnvelope,
    HydraNotificationPreference,
    HydraNotificationStateEvent,
    NotificationCategory,
    NotificationKind,
    NotificationSeverity,
    NotificationTargetKind,
)
from hydra_notifications.policy import policy_for, severity_meets_threshold
from hydra_notifications.selectors import visible_envelopes_for_user
from hydra_people.models import Person
from hydra_people.selectors import people_for_user
from hydra_tasks.models import HydraTask
from hydra_tasks.selectors import tasks_for_user
from notifications.models import Notification


def _normalized_uuid(value, *, field_name="target_uuid"):
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: "Choose a valid notification target."}) from error


def _safe_local_path(value):
    value = (value or "").strip()
    parsed = urlsplit(value)
    if (
        not value
        or not value.startswith("/")
        or value.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or any(ord(character) < 32 for character in value)
    ):
        raise ValidationError({"redirect_path": "Choose a safe local redirect."})
    return value


def _target_contract(*, target_kind, target_uuid):
    target_uuid = _normalized_uuid(target_uuid)
    if target_kind in (
        NotificationTargetKind.GENERAL,
        NotificationTargetKind.ORGANIZATION,
    ):
        if target_uuid is not None:
            raise ValidationError({"target_uuid": "This notification has no object target."})
        return None, None, None
    if target_uuid is None:
        raise ValidationError({"target_uuid": "A scoped notification target is required."})

    if target_kind == NotificationTargetKind.PERSON:
        target = Person._base_manager.get(uuid=target_uuid)
        return target, None, target
    if target_kind == NotificationTargetKind.LEGALIZATION_CASE:
        target = LegalizationCase._base_manager.select_related("company", "person").get(
            uuid=target_uuid
        )
        return target, target.company, target.person
    if target_kind == NotificationTargetKind.ARRIVAL_PLAN:
        target = ArrivalPlan._base_manager.select_related(
            "destination_location__company", "person"
        ).get(uuid=target_uuid)
        return target, target.destination_location.company, target.person
    if target_kind == NotificationTargetKind.ONBOARDING_HANDOFF:
        target = OnboardingHandoff.objects.select_related(
            "arrival__destination_location__company", "person"
        ).get(uuid=target_uuid)
        return target, target.arrival.destination_location.company, target.person
    if target_kind == NotificationTargetKind.HYDRA_TASK:
        target = HydraTask._base_manager.select_related("company", "person").get(
            uuid=target_uuid
        )
        return target, target.company, target.person
    raise ValidationError({"target_kind": "Choose a reviewed notification target."})


def _target_is_visible(*, recipient, target_kind, target_uuid):
    if target_kind in (
        NotificationTargetKind.GENERAL,
        NotificationTargetKind.ORGANIZATION,
    ):
        return True
    if target_kind == NotificationTargetKind.PERSON:
        return people_for_user(user=recipient).filter(uuid=target_uuid).exists()
    if target_kind == NotificationTargetKind.LEGALIZATION_CASE:
        return legalization_cases_for_user(user=recipient).filter(
            uuid=target_uuid
        ).exists()
    if target_kind == NotificationTargetKind.ARRIVAL_PLAN:
        return arrival_plans_for_user(user=recipient).filter(uuid=target_uuid).exists()
    if target_kind == NotificationTargetKind.ONBOARDING_HANDOFF:
        return OnboardingHandoff.objects.filter(
            uuid=target_uuid,
            arrival__in=arrival_plans_for_user(user=recipient),
        ).exists()
    if target_kind == NotificationTargetKind.HYDRA_TASK:
        return tasks_for_user(user=recipient).filter(uuid=target_uuid).exists()
    return False


def preference_for_user(*, user):
    preference, _created = HydraNotificationPreference.objects.get_or_create(user=user)
    return preference


def _email_policy_reason(*, recipient, severity, preference):
    if not preference.email_enabled:
        return "PreferenceDisabled"
    if not severity_meets_threshold(
        severity=severity,
        threshold=preference.email_min_severity,
    ):
        return "BelowSeverityThreshold"
    email = (recipient.email or "").strip()
    if not recipient.is_active or "@" not in email or len(email) > 254:
        return "RecipientEmailUnavailable"
    return ""


@transaction.atomic
def send_hydra_notification(
    *,
    actor,
    recipient,
    kind,
    target_kind,
    target_uuid=None,
    redirect_path,
    idempotency_key,
    email_hook=True,
):
    if not getattr(recipient, "pk", None):
        raise ValidationError({"recipient": "A saved notification recipient is required."})
    if not getattr(actor, "pk", None):
        raise ValidationError({"actor": "A saved notification actor is required."})
    if kind not in NotificationKind.values or kind == NotificationKind.LEGACY:
        raise ValidationError({"kind": "Choose a reviewed Hydra notification kind."})
    if target_kind not in NotificationTargetKind.values:
        raise ValidationError({"target_kind": "Choose a reviewed target kind."})
    idempotency_key = (idempotency_key or "").strip()
    if not idempotency_key or len(idempotency_key) > 180:
        raise ValidationError({"idempotency_key": "A bounded idempotency key is required."})
    redirect_path = _safe_local_path(redirect_path)
    policy = policy_for(kind)
    expected_target_kind = {
        NotificationCategory.ORGANIZATION: NotificationTargetKind.ORGANIZATION,
        NotificationCategory.ARRIVALS: NotificationTargetKind.ARRIVAL_PLAN,
        NotificationCategory.LEGALIZATION: NotificationTargetKind.LEGALIZATION_CASE,
        NotificationCategory.TASKS: NotificationTargetKind.HYDRA_TASK,
        NotificationCategory.ONBOARDING: NotificationTargetKind.ONBOARDING_HANDOFF,
    }[policy.category]
    if target_kind != expected_target_kind:
        raise ValidationError(
            {"target_kind": "The notification kind and target kind do not match."}
        )
    target, company, person = _target_contract(
        target_kind=target_kind,
        target_uuid=target_uuid,
    )
    normalized_target_uuid = getattr(target, "uuid", None)
    if not _target_is_visible(
        recipient=recipient,
        target_kind=target_kind,
        target_uuid=normalized_target_uuid,
    ):
        raise PermissionDenied

    existing = HydraNotificationEnvelope._base_manager.filter(
        idempotency_key=idempotency_key
    ).select_related("notification").first()
    if existing:
        if (
            existing.recipient_id != recipient.pk
            or existing.kind != kind
            or existing.target_kind != target_kind
            or existing.target_uuid != normalized_target_uuid
        ):
            raise ValidationError(
                {"idempotency_key": "The notification key belongs to another event."}
            )
        return existing.notification

    envelope_uuid = uuid4()
    center_path = reverse("hydra-notification-center")
    notification = Notification(
        recipient=recipient,
        actor_content_type=ContentType.objects.get_for_model(actor),
        actor_object_id=str(actor.pk),
        verb=policy.message,
        verb_en=policy.message,
        verb_ar=policy.message,
        verb_de=policy.message,
        verb_es=policy.message,
        verb_fr=policy.message,
        level=policy.severity,
        public=False,
        description=None,
        timestamp=timezone.now(),
        data={
            "redirect": center_path,
            "verb_en": policy.message,
            "icon": policy.icon,
            "label": "Hydra",
        },
    )
    notification.full_clean()
    notification.save(force_insert=True)
    envelope = HydraNotificationEnvelope(
        uuid=envelope_uuid,
        idempotency_key=idempotency_key,
        notification=notification,
        recipient=recipient,
        kind=kind,
        category=policy.category,
        severity=policy.severity,
        target_kind=target_kind,
        target_uuid=normalized_target_uuid,
        company=company,
        person=person,
        redirect_path=redirect_path,
        occurred_at=notification.timestamp,
    )
    envelope.full_clean()
    envelope.save(force_insert=True)
    HydraNotificationStateEvent.objects.create(
        envelope=envelope,
        sequence=1,
        action=HydraNotificationStateEvent.Action.CREATED,
        actor=None,
    )

    if email_hook:
        preference = preference_for_user(user=recipient)
        reason = _email_policy_reason(
            recipient=recipient,
            severity=policy.severity,
            preference=preference,
        )
        HydraNotificationEmailDelivery.objects.create(
            envelope=envelope,
            recipient=recipient,
            status=(
                HydraNotificationEmailDelivery.Status.NOT_APPLICABLE
                if reason
                else HydraNotificationEmailDelivery.Status.PENDING
            ),
            next_attempt_at=None if reason else timezone.now(),
            error_code=reason,
        )
    return notification


@transaction.atomic
def wrap_legacy_notification(*, notification, imported=False):
    existing = HydraNotificationEnvelope._base_manager.filter(
        notification=notification
    ).first()
    if existing:
        return existing
    envelope = HydraNotificationEnvelope(
        idempotency_key=f"legacy:{notification.pk}",
        notification=notification,
        recipient=notification.recipient,
        kind=NotificationKind.LEGACY,
        category=NotificationCategory.LEGACY,
        severity=(
            notification.level
            if notification.level in NotificationSeverity.values
            else NotificationSeverity.INFO
        ),
        target_kind=NotificationTargetKind.GENERAL,
        occurred_at=notification.timestamp,
        read_at=None if notification.unread else notification.timestamp,
        archived_at=notification.timestamp if notification.deleted else None,
    )
    envelope.full_clean()
    envelope.save(force_insert=True)
    HydraNotificationStateEvent.objects.create(
        envelope=envelope,
        sequence=1,
        action=(
            HydraNotificationStateEvent.Action.IMPORTED
            if imported
            else HydraNotificationStateEvent.Action.CREATED
        ),
        actor=None,
    )
    return envelope


def _validate_expected_version(envelope, expected_version):
    if expected_version is None:
        return
    try:
        expected_version = int(expected_version)
    except (TypeError, ValueError) as error:
        raise ValidationError({"version": "Choose a valid notification version."}) from error
    if expected_version < 1 or envelope.version != expected_version:
        raise ValidationError(
            {"version": "This notification changed in another session. Refresh and retry."}
        )


def _lock_visible_envelope(*, actor, envelope_uuid, include_archived=False):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    visible_pk = visible_envelopes_for_user(
        user=actor,
        include_archived=include_archived,
    ).filter(uuid=envelope_uuid).values_list("pk", flat=True).first()
    if visible_pk is None:
        raise HydraNotificationEnvelope.DoesNotExist
    return HydraNotificationEnvelope._base_manager.select_for_update().get(pk=visible_pk)


def _record_state(*, envelope, action, actor, now):
    envelope.version += 1
    envelope.save(
        service_update=True,
        update_fields=("read_at", "archived_at", "version"),
    )
    HydraNotificationStateEvent.objects.create(
        envelope=envelope,
        sequence=envelope.version,
        action=action,
        actor=actor,
        occurred_at=now,
    )


@transaction.atomic
def mark_envelope_read(
    *, actor, envelope_uuid, expected_version=None, opened=False
):
    envelope = _lock_visible_envelope(actor=actor, envelope_uuid=envelope_uuid)
    _validate_expected_version(envelope, expected_version)
    if envelope.read_at is not None:
        return envelope
    now = timezone.now()
    envelope.read_at = now
    Notification._base_manager.filter(pk=envelope.notification_id).update(unread=False)
    _record_state(
        envelope=envelope,
        action=(
            HydraNotificationStateEvent.Action.OPENED
            if opened
            else HydraNotificationStateEvent.Action.READ
        ),
        actor=actor,
        now=now,
    )
    return envelope


@transaction.atomic
def mark_envelope_unread(*, actor, envelope_uuid, expected_version=None):
    envelope = _lock_visible_envelope(actor=actor, envelope_uuid=envelope_uuid)
    _validate_expected_version(envelope, expected_version)
    if envelope.read_at is None:
        return envelope
    now = timezone.now()
    envelope.read_at = None
    Notification._base_manager.filter(pk=envelope.notification_id).update(unread=True)
    _record_state(
        envelope=envelope,
        action=HydraNotificationStateEvent.Action.UNREAD,
        actor=actor,
        now=now,
    )
    return envelope


@transaction.atomic
def archive_envelope(*, actor, envelope_uuid, expected_version=None):
    envelope = _lock_visible_envelope(actor=actor, envelope_uuid=envelope_uuid)
    _validate_expected_version(envelope, expected_version)
    if envelope.archived_at is not None:
        return envelope
    now = timezone.now()
    envelope.archived_at = now
    if envelope.read_at is None:
        envelope.read_at = now
    Notification._base_manager.filter(pk=envelope.notification_id).update(
        unread=False,
        deleted=True,
    )
    _record_state(
        envelope=envelope,
        action=HydraNotificationStateEvent.Action.ARCHIVED,
        actor=actor,
        now=now,
    )
    return envelope


@transaction.atomic
def restore_envelope(*, actor, envelope_uuid, expected_version=None):
    envelope = _lock_visible_envelope(
        actor=actor,
        envelope_uuid=envelope_uuid,
        include_archived=True,
    )
    _validate_expected_version(envelope, expected_version)
    if envelope.archived_at is None:
        return envelope
    now = timezone.now()
    envelope.archived_at = None
    Notification._base_manager.filter(pk=envelope.notification_id).update(deleted=False)
    _record_state(
        envelope=envelope,
        action=HydraNotificationStateEvent.Action.RESTORED,
        actor=actor,
        now=now,
    )
    return envelope


STATE_CHANGE_BATCH_SIZE = 200


def mark_all_visible_read(*, actor):
    changed = 0
    last_pk = 0
    while True:
        batch = list(
            visible_envelopes_for_user(user=actor)
            .filter(read_at__isnull=True, pk__gt=last_pk)
            .order_by("pk")
            .values_list("pk", "uuid")[:STATE_CHANGE_BATCH_SIZE]
        )
        if not batch:
            return changed
        for _pk, envelope_uuid in batch:
            mark_envelope_read(actor=actor, envelope_uuid=envelope_uuid)
            changed += 1
        last_pk = batch[-1][0]


def archive_all_visible(*, actor, unread_only=False):
    changed = 0
    last_pk = 0
    while True:
        queryset = visible_envelopes_for_user(user=actor).filter(pk__gt=last_pk)
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)
        batch = list(
            queryset.order_by("pk").values_list("pk", "uuid")[
                :STATE_CHANGE_BATCH_SIZE
            ]
        )
        if not batch:
            return changed
        for _pk, envelope_uuid in batch:
            archive_envelope(actor=actor, envelope_uuid=envelope_uuid)
            changed += 1
        last_pk = batch[-1][0]


def safe_redirect_for_envelope(*, envelope):
    candidate = envelope.redirect_path
    if envelope.kind == NotificationKind.LEGACY:
        data = envelope.notification.data or {}
        candidate = data.get("redirect", "") if isinstance(data, dict) else ""
    try:
        return _safe_local_path(candidate)
    except ValidationError:
        return reverse("hydra-notification-center")


@transaction.atomic
def update_preferences(
    *,
    actor,
    email_enabled,
    email_min_severity,
    browser_sound_enabled,
    expected_version,
):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    preference = preference_for_user(user=actor)
    preference = HydraNotificationPreference._base_manager.select_for_update().get(
        pk=preference.pk
    )
    try:
        expected_version = int(expected_version)
    except (TypeError, ValueError) as error:
        raise ValidationError({"version": "Choose a valid preference version."}) from error
    if expected_version != preference.version:
        raise ValidationError(
            {"version": "Notification preferences changed. Refresh and retry."}
        )
    if email_min_severity not in NotificationSeverity.values:
        raise ValidationError({"email_min_severity": "Choose a valid severity."})
    preference.email_enabled = bool(email_enabled)
    preference.email_min_severity = email_min_severity
    preference.browser_sound_enabled = bool(browser_sound_enabled)
    preference.version += 1
    preference.modified_by = actor
    preference.save(
        service_update=True,
        update_fields=(
            "email_enabled",
            "email_min_severity",
            "browser_sound_enabled",
            "version",
            "modified_at",
            "modified_by",
        ),
    )
    return preference


def toggle_browser_sound(*, actor):
    preference = preference_for_user(user=actor)
    return update_preferences(
        actor=actor,
        email_enabled=preference.email_enabled,
        email_min_severity=preference.email_min_severity,
        browser_sound_enabled=not preference.browser_sound_enabled,
        expected_version=preference.version,
    )


def _delivery_policy_reason(delivery):
    envelope = delivery.envelope
    recipient = delivery.recipient
    if envelope.archived_at is not None:
        return "NotificationArchived"
    if not visible_envelopes_for_user(user=recipient).filter(pk=envelope.pk).exists():
        return "ScopeNoLongerVisible"
    preference = preference_for_user(user=recipient)
    return _email_policy_reason(
        recipient=recipient,
        severity=envelope.severity,
        preference=preference,
    )


def recover_expired_email_leases(*, now=None, limit=100):
    now = now or timezone.now()
    if limit < 1 or limit > 1000:
        raise ValidationError("Email lease recovery limit must be 1 to 1000.")
    delivery_ids = list(
        HydraNotificationEmailDelivery._base_manager.filter(
            status=HydraNotificationEmailDelivery.Status.SENDING,
            lease_expires_at__lte=now,
        )
        .order_by("lease_expires_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    recovered = 0
    for delivery_id in delivery_ids:
        with transaction.atomic():
            delivery = HydraNotificationEmailDelivery._base_manager.select_for_update().get(
                pk=delivery_id
            )
            if (
                delivery.status != HydraNotificationEmailDelivery.Status.SENDING
                or delivery.lease_expires_at is None
                or delivery.lease_expires_at > now
            ):
                continue
            delivery.status = (
                HydraNotificationEmailDelivery.Status.DEAD
                if delivery.attempts >= settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS
                else HydraNotificationEmailDelivery.Status.FAILED
            )
            delivery.next_attempt_at = (
                None
                if delivery.status == HydraNotificationEmailDelivery.Status.DEAD
                else now
            )
            delivery.lease_expires_at = None
            delivery.error_code = "LeaseExpired"
            delivery.save(
                update_fields=(
                    "status",
                    "next_attempt_at",
                    "lease_expires_at",
                    "error_code",
                )
            )
            recovered += 1
    return recovered


def dispatch_notification_email(delivery_id, *, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        delivery = HydraNotificationEmailDelivery._base_manager.select_for_update().get(
            pk=delivery_id
        )
        if delivery.status in (
            HydraNotificationEmailDelivery.Status.SENT,
            HydraNotificationEmailDelivery.Status.DEAD,
            HydraNotificationEmailDelivery.Status.NOT_APPLICABLE,
        ):
            return delivery.status == HydraNotificationEmailDelivery.Status.SENT
        if delivery.status == HydraNotificationEmailDelivery.Status.SENDING:
            return False
        if delivery.next_attempt_at and delivery.next_attempt_at > now:
            return False
        reason = _delivery_policy_reason(delivery)
        if reason:
            delivery.status = HydraNotificationEmailDelivery.Status.NOT_APPLICABLE
            delivery.next_attempt_at = None
            delivery.lease_expires_at = None
            delivery.error_code = reason
            delivery.save(
                update_fields=(
                    "status",
                    "next_attempt_at",
                    "lease_expires_at",
                    "error_code",
                )
            )
            return True
        if delivery.attempts >= settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS:
            delivery.status = HydraNotificationEmailDelivery.Status.DEAD
            delivery.next_attempt_at = None
            delivery.error_code = "RetriesExhausted"
            delivery.save(update_fields=("status", "next_attempt_at", "error_code"))
            return False
        delivery.status = HydraNotificationEmailDelivery.Status.SENDING
        delivery.attempts += 1
        delivery.last_attempt_at = now
        delivery.next_attempt_at = None
        delivery.lease_expires_at = now + timedelta(
            seconds=settings.HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS
        )
        delivery.error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "attempts",
                "last_attempt_at",
                "next_attempt_at",
                "lease_expires_at",
                "error_code",
            )
        )
        delivery_uuid = delivery.uuid
        recipient_email = delivery.recipient.email.strip()

    base_url = settings.HYDRA_NOTIFICATION_BASE_URL.rstrip("/") + "/"
    center_url = urljoin(base_url, reverse("hydra-notification-center").lstrip("/"))
    hostname = urlsplit(base_url).hostname or "invalid.local"
    try:
        sent = EmailMessage(
            subject="Hydra notification",
            body=(
                "You have a new notification in Hydra. Sign in to review it.\n\n"
                f"{center_url}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
            headers={"Message-ID": f"<hydra-notification-{delivery_uuid}@{hostname}>"},
        ).send(fail_silently=False)
        if sent != 1:
            raise RuntimeError("email_backend_returned_no_delivery")
    except Exception as error:
        failed_at = timezone.now()
        with transaction.atomic():
            delivery = HydraNotificationEmailDelivery._base_manager.select_for_update().get(
                pk=delivery_id
            )
            delivery.lease_expires_at = None
            delivery.sent_at = None
            delivery.error_code = type(error).__name__[:80]
            if delivery.attempts >= settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS:
                delivery.status = HydraNotificationEmailDelivery.Status.DEAD
                delivery.next_attempt_at = None
            else:
                delivery.status = HydraNotificationEmailDelivery.Status.FAILED
                delay = min(
                    settings.HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS
                    * (2 ** max(delivery.attempts - 1, 0)),
                    settings.HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS,
                )
                delivery.next_attempt_at = failed_at + timedelta(seconds=delay)
            delivery.save(
                update_fields=(
                    "status",
                    "next_attempt_at",
                    "lease_expires_at",
                    "sent_at",
                    "error_code",
                )
            )
        return False

    with transaction.atomic():
        delivery = HydraNotificationEmailDelivery._base_manager.select_for_update().get(
            pk=delivery_id
        )
        delivery.status = HydraNotificationEmailDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.next_attempt_at = None
        delivery.lease_expires_at = None
        delivery.error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "sent_at",
                "next_attempt_at",
                "lease_expires_at",
                "error_code",
            )
        )
    return True


@dataclass(frozen=True)
class NotificationEmailDispatchResult:
    selected: int
    sent: int
    failed: int
    dead: int
    not_applicable: int
    leases_recovered: int


def dispatch_pending_notification_emails(*, limit, now=None):
    now = now or timezone.now()
    if limit < 1 or limit > 1000:
        raise ValidationError("Notification email batch size must be 1 to 1000.")
    recovered = recover_expired_email_leases(now=now, limit=limit)
    delivery_ids = list(
        HydraNotificationEmailDelivery._base_manager.filter(
            status__in=(
                HydraNotificationEmailDelivery.Status.PENDING,
                HydraNotificationEmailDelivery.Status.FAILED,
            ),
            next_attempt_at__lte=now,
        )
        .order_by("next_attempt_at", "created_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    for delivery_id in delivery_ids:
        dispatch_notification_email(delivery_id, now=now)
    final = HydraNotificationEmailDelivery._base_manager.filter(pk__in=delivery_ids)
    return NotificationEmailDispatchResult(
        selected=len(delivery_ids),
        sent=final.filter(status=HydraNotificationEmailDelivery.Status.SENT).count(),
        failed=final.filter(status=HydraNotificationEmailDelivery.Status.FAILED).count(),
        dead=final.filter(status=HydraNotificationEmailDelivery.Status.DEAD).count(),
        not_applicable=final.filter(
            status=HydraNotificationEmailDelivery.Status.NOT_APPLICABLE
        ).count(),
        leases_recovered=recovered,
    )
