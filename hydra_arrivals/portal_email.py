import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q, Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from base.backends import ConfiguredEmailBackend
from base.models import DynamicEmailConfiguration
from hydra_arrivals.models import (
    OnboardingPortalDelivery,
    OnboardingPortalDeliveryAttachment,
    OnboardingPortalDeliveryEvent,
)
from hydra_arrivals.storage import portal_email_storage
from hydra_documents.scanning import ScannerError, scan_file
from hydra_people.recruitment_selectors import linked_candidates_for_user
from onboarding.models import OnboardingPortal
from onboarding.services import ensure_candidate_onboarding
from recruitment.models import Candidate


PORTAL_EMAIL_QUEUE_PERMISSIONS = (
    "hydra_people.view_person",
    "recruitment.view_recruitment",
    "recruitment.view_candidate",
    "recruitment.change_candidate",
    "onboarding.view_onboardingportal",
    "onboarding.add_onboardingportal",
    "onboarding.change_onboardingportal",
)
ACTIVE_DELIVERY_STATUSES = (
    OnboardingPortalDelivery.Status.PENDING,
    OnboardingPortalDelivery.Status.RETRY,
    OnboardingPortalDelivery.Status.SENDING,
)
ALLOWED_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


@dataclass(frozen=True)
class PreparedPortalAttachment:
    filename: str
    content_type: str
    content: bytes
    sha256: str

    @property
    def size(self):
        return len(self.content)


@dataclass(frozen=True)
class PortalEmailDispatchResult:
    selected: int
    sent: int
    failed: int
    dead: int
    cancelled: int
    onboarding_started: int
    onboarding_failed: int
    leases_recovered: int = 0


class PortalAttachmentIntegrityError(RuntimeError):
    pass


class PortalDeliveryNotConfirmed(RuntimeError):
    pass


def _safe_filename(filename):
    name = Path(filename or "attachment").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "attachment")[:255]


def _verified_content_type(content):
    return next(
        (content_type for signature, content_type in ALLOWED_SIGNATURES if content.startswith(signature)),
        None,
    )


def _validate_attachment_limits(attachments):
    max_count = settings.HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS
    max_bytes = settings.HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES
    max_total = settings.HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES
    if len(attachments) > max_count:
        raise ValidationError(
            _("At most %(count)s portal-email attachments are allowed."),
            params={"count": max_count},
        )
    total = 0
    for attachment in attachments:
        if attachment.size <= 0 or attachment.size > max_bytes:
            raise ValidationError(
                _("Each attachment must be non-empty and no larger than %(size)s MB."),
                params={"size": max_bytes // (1024 * 1024)},
            )
        if _verified_content_type(attachment.content) != attachment.content_type:
            raise ValidationError(_("Only verified PDF, JPEG and PNG attachments are allowed."))
        total += attachment.size
    if total > max_total:
        raise ValidationError(
            _("Portal-email attachments exceed the %(size)s MB total limit."),
            params={"size": max_total // (1024 * 1024)},
        )


def prepare_uploaded_portal_attachments(uploads):
    uploads = list(uploads)
    if len(uploads) > settings.HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS:
        raise ValidationError(_("Too many portal-email attachments were selected."))
    if sum(upload.size for upload in uploads) > settings.HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES:
        raise ValidationError(_("Portal-email attachments exceed the configured total limit."))
    prepared = []
    for upload in uploads:
        if upload.size <= 0 or upload.size > settings.HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES:
            raise ValidationError(
                _("Each attachment must be non-empty and within the configured size limit.")
            )
        content = b"".join(upload.chunks())
        upload.seek(0)
        content_type = _verified_content_type(content)
        if content_type is None:
            raise ValidationError(_("Only verified PDF, JPEG and PNG attachments are allowed."))
        try:
            scan_result = scan_file(upload)
        except ScannerError as error:
            raise ValidationError(
                _("The attachment could not be security-scanned. Try again later.")
            ) from error
        if not scan_result.clean:
            raise ValidationError(_("An attachment was rejected by the security scanner."))
        prepared.append(
            PreparedPortalAttachment(
                filename=_safe_filename(upload.name),
                content_type=content_type,
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    _validate_attachment_limits(prepared)
    return tuple(prepared)


def prepare_generated_portal_attachment(*, filename, content, content_type="application/pdf"):
    content = bytes(content)
    attachment = PreparedPortalAttachment(
        filename=_safe_filename(filename),
        content_type=content_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )
    _validate_attachment_limits((attachment,))
    return attachment


def _payload_digest(*, recipient, sender, reply_to, subject, body_html, attachments):
    digest = hashlib.sha256()
    for value in (recipient, sender, reply_to, subject, body_html):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    for attachment in attachments:
        for value in (
            attachment.filename,
            attachment.content_type,
            str(attachment.size),
            attachment.sha256,
        ):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _snapshot(delivery):
    attachment_totals = delivery.attachments.aggregate(
        total_bytes=Sum("size"),
    )
    return {
        "delivery_uuid": str(delivery.uuid),
        "candidate_id": delivery.candidate_id,
        "portal_id": delivery.portal_id,
        "status": delivery.status,
        "attempt": delivery.attempts,
        "attachment_count": delivery.attachments.count(),
        "attachment_bytes": attachment_totals["total_bytes"] or 0,
        "payload_sha256": delivery.payload_sha256,
    }


def _record_event(*, delivery, event_type, actor=None, error_code=""):
    OnboardingPortalDeliveryEvent.objects.create(
        delivery=delivery,
        event_type=event_type,
        actor=actor,
        error_code=error_code[:80],
        attempt=delivery.attempts,
        snapshot=_snapshot(delivery),
    )


def _validate_candidate(candidate):
    if candidate.recruitment_id_id is None:
        raise ValidationError(_("The candidate has no recruitment."))
    if not candidate.is_active or candidate.canceled or not candidate.hired:
        raise ValidationError(_("Only an active, hired candidate can receive a portal link."))
    if candidate.stage_id_id is None or candidate.stage_id.stage_type != "hired":
        raise ValidationError(_("The candidate is not in a hired recruitment stage."))
    if candidate.converted_employee_id:
        raise ValidationError(_("The candidate has already been converted to an employee."))
    if not candidate.email:
        raise ValidationError(_("The candidate has no email address."))


def _portal_url(token):
    base_url = settings.HYDRA_ONBOARDING_PORTAL_BASE_URL.strip()
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(_("The onboarding portal URL is not configured correctly."))
    return urljoin(base_url.rstrip("/") + "/", f"onboarding/user-creation/{token}")


def _email_configuration_for_actor(actor):
    employee = getattr(actor, "employee_get", None)
    company = employee.get_company() if employee is not None else None
    configuration = DynamicEmailConfiguration.objects.filter(company_id=company).first()
    if configuration is None:
        configuration = DynamicEmailConfiguration.objects.filter(is_primary=True).first()
    return configuration


def _validate_email_configuration(configuration):
    if getattr(settings, "HYDRA_ENVIRONMENT", "development") not in {
        "staging",
        "production",
    }:
        return
    host = configuration.host if configuration else settings.EMAIL_HOST
    port = configuration.port if configuration else settings.EMAIL_PORT
    username = configuration.username if configuration else settings.EMAIL_HOST_USER
    password = configuration.password if configuration else settings.EMAIL_HOST_PASSWORD
    from_email = configuration.from_email if configuration else settings.DEFAULT_FROM_EMAIL
    use_tls = configuration.use_tls if configuration else settings.EMAIL_USE_TLS
    use_ssl = configuration.use_ssl if configuration else settings.EMAIL_USE_SSL
    fail_silently = (
        configuration.fail_silently
        if configuration
        else settings.EMAIL_FAIL_SILENTLY
    )
    timeout = configuration.timeout if configuration else settings.EMAIL_TIMEOUT
    values = (host, username, password, from_email)
    if (
        not all(values)
        or any("replace" in str(value).lower() for value in values)
        or not 1 <= int(port or 0) <= 65535
        or "@" not in str(from_email)
        or bool(use_tls) == bool(use_ssl)
        or fail_silently
        or not 1 <= int(timeout or 0)
        or settings.HYDRA_PORTAL_EMAIL_LEASE_SECONDS < 2 * int(timeout or 0)
    ):
        raise ValidationError(
            _("The portal email server configuration is not production-safe.")
        )


def _sender_snapshot(*, actor, configuration):
    mailbox = (
        configuration.from_email
        if configuration is not None
        else settings.DEFAULT_FROM_EMAIL
    )
    mailbox = mailbox or "noreply@localhost.invalid"
    display_name = configuration.display_name if configuration is not None else ""
    employee = getattr(actor, "employee_get", None)
    reply_to = mailbox
    if employee is not None:
        employee_email = employee.get_email()
        if employee_email:
            reply_to = employee_email
        if configuration is not None and configuration.use_dynamic_display_name:
            display_name = employee.get_full_name()
    sender = f"{display_name} <{mailbox}>" if display_name else mailbox
    return sender, reply_to


def queue_onboarding_portal_email(*, candidate_id, actor, attachments=()):
    if not actor.is_authenticated or not actor.has_perms(PORTAL_EMAIL_QUEUE_PERMISSIONS):
        raise PermissionDenied
    if not linked_candidates_for_user(user=actor).filter(pk=candidate_id).exists():
        raise PermissionDenied
    attachments = tuple(attachments)
    _validate_attachment_limits(attachments)
    saved_names = []
    try:
        with transaction.atomic():
            candidate = (
                Candidate._base_manager.select_for_update(of=("self",))
                .select_related("stage_id", "recruitment_id")
                .get(pk=candidate_id)
            )
            if not linked_candidates_for_user(user=actor).filter(pk=candidate.pk).exists():
                raise PermissionDenied
            _validate_candidate(candidate)
            portal = (
                OnboardingPortal._base_manager.select_for_update()
                .filter(candidate_id=candidate)
                .first()
            )
            if portal is not None:
                active = (
                    OnboardingPortalDelivery.objects.select_for_update()
                    .filter(
                        candidate=candidate,
                        status__in=ACTIVE_DELIVERY_STATUSES,
                    )
                    .order_by("-requested_at", "-pk")
                    .first()
                )
                if active is not None:
                    if (
                        active.portal_id == portal.pk
                        and active.portal_token == portal.token
                        and active.payload_purged_at is None
                    ):
                        return active, False
                    raise ValidationError(
                        _("The active portal delivery requires an integrity review.")
                    )
                for exhausted in OnboardingPortalDelivery.objects.select_for_update().filter(
                    candidate=candidate,
                    status=OnboardingPortalDelivery.Status.DEAD,
                ):
                    _cancel_locked(
                        exhausted,
                        portal=portal,
                        error_code="SupersededByNewRequest",
                    )

            token = secrets.token_hex(30)
            if portal is None:
                portal = OnboardingPortal.objects.create(
                    candidate_id=candidate,
                    token=token,
                    used=False,
                    count=0,
                    profile=None,
                )
            else:
                portal.token = token
                portal.used = False
                portal.count = 0
                portal.profile = None
                portal.save(update_fields=("token", "used", "count", "profile"))

            portal_link = _portal_url(token)
            body_html = render_to_string(
                "onboarding/mail_templates/default.html",
                {
                    "portal": portal_link,
                    "instance": candidate,
                    "host": urlparse(portal_link).netloc,
                    "protocol": urlparse(portal_link).scheme,
                },
            )
            subject = f"Hello {candidate.name}, Congratulations on your selection!"
            email_configuration = _email_configuration_for_actor(actor)
            _validate_email_configuration(email_configuration)
            sender, reply_to = _sender_snapshot(
                actor=actor,
                configuration=email_configuration,
            )
            payload_sha256 = _payload_digest(
                recipient=candidate.email,
                sender=sender,
                reply_to=reply_to,
                subject=subject,
                body_html=body_html,
                attachments=attachments,
            )
            idempotency_key = hashlib.sha256(
                f"onboarding-portal:{candidate.pk}:{token}".encode("utf-8")
            ).hexdigest()
            delivery = OnboardingPortalDelivery(
                candidate=candidate,
                portal=portal,
                requested_by=actor,
                email_configuration=email_configuration,
                idempotency_key=idempotency_key,
                portal_token=token,
                recipient=candidate.email,
                sender=sender,
                reply_to=reply_to,
                subject=subject,
                body_html=body_html,
                payload_sha256=payload_sha256,
                next_attempt_at=timezone.now(),
            )
            delivery.full_clean()
            delivery.save(force_insert=True)
            for prepared in attachments:
                attachment = OnboardingPortalDeliveryAttachment(
                    delivery=delivery,
                    original_filename=prepared.filename,
                    content_type=prepared.content_type,
                    size=prepared.size,
                    sha256=prepared.sha256,
                )
                attachment.full_clean(exclude=("file",))
                attachment.file.save(
                    prepared.filename,
                    ContentFile(prepared.content),
                    save=False,
                )
                saved_names.append(attachment.file.name)
                attachment.save(force_insert=True)
            _record_event(
                delivery=delivery,
                event_type=OnboardingPortalDeliveryEvent.EventType.QUEUED,
                actor=actor,
            )
            return delivery, True
    except Exception:
        for name in saved_names:
            try:
                portal_email_storage.delete(name)
            except OSError:
                pass
        raise


def _cancel_locked(delivery, *, portal, error_code):
    if not portal.used and portal.token == delivery.portal_token:
        portal.token = secrets.token_hex(30)
        portal.used = True
        portal.count = 0
        portal.profile = None
        portal.save(update_fields=("token", "used", "count", "profile"))
    delivery.status = OnboardingPortalDelivery.Status.CANCELLED
    delivery.lease_token = None
    delivery.lease_expires_at = None
    delivery.last_error_code = error_code[:80]
    delivery.save(
        update_fields=(
            "status",
            "lease_token",
            "lease_expires_at",
            "last_error_code",
        )
    )
    _record_event(
        delivery=delivery,
        event_type=OnboardingPortalDeliveryEvent.EventType.CANCELLED,
        error_code=error_code,
    )


def recover_expired_portal_email_leases(*, now=None, limit=None):
    now = now or timezone.now()
    if limit is None:
        limit = settings.HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE
    if not 1 <= limit <= 1000:
        raise ValidationError(_("Portal-email lease recovery batch size must be 1 to 1000."))
    ids = list(
        OnboardingPortalDelivery.objects.filter(
            status=OnboardingPortalDelivery.Status.SENDING,
            lease_expires_at__lte=now,
        )
        .order_by("lease_expires_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    recovered = 0
    for delivery_id in ids:
        stub = OnboardingPortalDelivery.objects.filter(pk=delivery_id).values(
            "candidate_id", "portal_id"
        ).first()
        if not stub:
            continue
        with transaction.atomic():
            Candidate._base_manager.select_for_update(of=("self",)).get(
                pk=stub["candidate_id"]
            )
            OnboardingPortal._base_manager.select_for_update().get(pk=stub["portal_id"])
            delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=delivery_id)
            if (
                delivery.status != OnboardingPortalDelivery.Status.SENDING
                or delivery.lease_expires_at is None
                or delivery.lease_expires_at > now
            ):
                continue
            delivery.status = OnboardingPortalDelivery.Status.RETRY
            delivery.next_attempt_at = now
            delivery.lease_token = None
            delivery.lease_expires_at = None
            delivery.last_error_code = "LeaseExpired"
            delivery.save(
                update_fields=(
                    "status",
                    "next_attempt_at",
                    "lease_token",
                    "lease_expires_at",
                    "last_error_code",
                )
            )
            _record_event(
                delivery=delivery,
                event_type=OnboardingPortalDeliveryEvent.EventType.RETRY_SCHEDULED,
                error_code="LeaseExpired",
            )
            recovered += 1
    return recovered


def _claim_delivery(*, delivery_id, now):
    stub = OnboardingPortalDelivery.objects.filter(pk=delivery_id).values(
        "candidate_id", "portal_id"
    ).first()
    if not stub:
        return None, False
    with transaction.atomic():
        candidate = (
            Candidate._base_manager.select_for_update(of=("self",))
            .select_related("stage_id")
            .get(pk=stub["candidate_id"])
        )
        portal = OnboardingPortal._base_manager.select_for_update().get(
            pk=stub["portal_id"]
        )
        delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=delivery_id)
        if delivery.status not in (
            OnboardingPortalDelivery.Status.PENDING,
            OnboardingPortalDelivery.Status.RETRY,
        ) or delivery.next_attempt_at > now:
            return None, False
        cancellation_code = ""
        try:
            _validate_candidate(candidate)
        except ValidationError:
            cancellation_code = "CandidateNoLongerEligible"
        if not cancellation_code and candidate.email.casefold() != delivery.recipient.casefold():
            cancellation_code = "RecipientChanged"
        if not cancellation_code and (portal.used or portal.token != delivery.portal_token):
            cancellation_code = "PortalTokenSuperseded"
        if not cancellation_code and delivery.payload_purged_at is not None:
            cancellation_code = "PayloadUnavailable"
        if cancellation_code:
            _cancel_locked(
                delivery,
                portal=portal,
                error_code=cancellation_code,
            )
            return None, True

        lease_token = uuid4()
        delivery.status = OnboardingPortalDelivery.Status.SENDING
        delivery.attempts += 1
        delivery.last_attempt_at = now
        delivery.lease_token = lease_token
        delivery.lease_expires_at = now + timedelta(
            seconds=settings.HYDRA_PORTAL_EMAIL_LEASE_SECONDS
        )
        delivery.last_error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "attempts",
                "last_attempt_at",
                "lease_token",
                "lease_expires_at",
                "last_error_code",
            )
        )
        _record_event(
            delivery=delivery,
            event_type=OnboardingPortalDeliveryEvent.EventType.CLAIMED,
        )
        return lease_token, False


def _load_message(delivery_id):
    delivery = OnboardingPortalDelivery.objects.select_related(
        "email_configuration"
    ).get(pk=delivery_id)
    prepared = []
    for attachment in delivery.attachments.all():
        if not attachment.file or attachment.purged_at is not None:
            raise PortalAttachmentIntegrityError
        with attachment.file.open("rb") as handle:
            content = handle.read()
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != attachment.size or digest != attachment.sha256:
            raise PortalAttachmentIntegrityError
        prepared.append(
            PreparedPortalAttachment(
                filename=attachment.original_filename,
                content_type=attachment.content_type,
                content=content,
                sha256=digest,
            )
        )
    if _payload_digest(
        recipient=delivery.recipient,
        sender=delivery.sender,
        reply_to=delivery.reply_to,
        subject=delivery.subject,
        body_html=delivery.body_html,
        attachments=prepared,
    ) != delivery.payload_sha256:
        raise PortalAttachmentIntegrityError
    backend = ConfiguredEmailBackend(
        configuration_id=delivery.email_configuration_id,
        fail_silently=False,
    )
    message = EmailMessage(
        subject=delivery.subject,
        body=delivery.body_html,
        from_email=delivery.sender,
        to=[delivery.recipient],
        reply_to=[delivery.reply_to],
        connection=backend,
    )
    message.content_subtype = "html"
    for attachment in prepared:
        message.attach(
            attachment.filename,
            attachment.content,
            attachment.content_type,
        )
    message.hydra_sensitive = True
    message.hydra_audit_reference = str(delivery.uuid)
    return message


def _mark_delivery_failed(*, delivery_id, lease_token, error_code, now):
    with transaction.atomic():
        delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=delivery_id)
        if (
            delivery.status != OnboardingPortalDelivery.Status.SENDING
            or delivery.lease_token != lease_token
        ):
            return None
        exhausted = delivery.attempts >= settings.HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS
        delivery.status = (
            OnboardingPortalDelivery.Status.DEAD
            if exhausted
            else OnboardingPortalDelivery.Status.RETRY
        )
        delay = min(
            settings.HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS,
            settings.HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS
            * (2 ** max(delivery.attempts - 1, 0)),
        )
        delivery.next_attempt_at = now + timedelta(seconds=delay)
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.last_error_code = error_code[:80]
        delivery.save(
            update_fields=(
                "status",
                "next_attempt_at",
                "lease_token",
                "lease_expires_at",
                "last_error_code",
            )
        )
        _record_event(
            delivery=delivery,
            event_type=(
                OnboardingPortalDeliveryEvent.EventType.DEAD
                if exhausted
                else OnboardingPortalDeliveryEvent.EventType.RETRY_SCHEDULED
            ),
            error_code=error_code,
        )
        return delivery.status


def _mark_delivery_sent(*, delivery_id, lease_token, now):
    with transaction.atomic():
        delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=delivery_id)
        if (
            delivery.status != OnboardingPortalDelivery.Status.SENDING
            or delivery.lease_token != lease_token
        ):
            return False
        delivery.status = OnboardingPortalDelivery.Status.SENT
        delivery.sent_at = now
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.last_error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "sent_at",
                "lease_token",
                "lease_expires_at",
                "last_error_code",
            )
        )
        _record_event(
            delivery=delivery,
            event_type=OnboardingPortalDeliveryEvent.EventType.SENT,
        )
        return True


def _start_onboarding_for_sent_delivery(delivery_id):
    stub = OnboardingPortalDelivery.objects.filter(pk=delivery_id).values(
        "candidate_id", "portal_id"
    ).first()
    if not stub:
        return False
    with transaction.atomic():
        candidate = (
            Candidate._base_manager.select_for_update(of=("self",))
            .select_related("stage_id")
            .get(pk=stub["candidate_id"])
        )
        OnboardingPortal._base_manager.select_for_update().get(pk=stub["portal_id"])
        delivery = OnboardingPortalDelivery.objects.select_for_update().select_related(
            "requested_by"
        ).get(pk=delivery_id)
        if delivery.status != OnboardingPortalDelivery.Status.SENT:
            return False
        if delivery.onboarding_started_at is not None:
            return True
        previous_error = delivery.onboarding_error_code
        try:
            _validate_candidate(candidate)
            ensure_candidate_onboarding(candidate=candidate, actor=delivery.requested_by)
        except ValidationError as error:
            error_code = type(error).__name__[:80]
            delivery.onboarding_error_code = error_code
            delivery.save(update_fields=("onboarding_error_code",))
            if previous_error != error_code:
                _record_event(
                    delivery=delivery,
                    event_type=OnboardingPortalDeliveryEvent.EventType.ONBOARDING_FAILED,
                    error_code=error_code,
                )
            return False
        delivery.onboarding_started_at = timezone.now()
        delivery.onboarding_error_code = ""
        delivery.save(update_fields=("onboarding_started_at", "onboarding_error_code"))
        _record_event(
            delivery=delivery,
            event_type=OnboardingPortalDeliveryEvent.EventType.ONBOARDING_STARTED,
            actor=delivery.requested_by,
        )
        return True


def reconcile_sent_portal_deliveries(*, limit):
    if not 1 <= limit <= 1000:
        raise ValidationError(_("Portal-email reconciliation batch size must be 1 to 1000."))
    ids = list(
        OnboardingPortalDelivery.objects.filter(
            status=OnboardingPortalDelivery.Status.SENT,
            onboarding_started_at__isnull=True,
        )
        .order_by("sent_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    started = 0
    failed = 0
    for delivery_id in ids:
        if _start_onboarding_for_sent_delivery(delivery_id):
            started += 1
        else:
            failed += 1
    return started, failed


def dispatch_portal_emails(*, limit, now=None):
    if not 1 <= limit <= 1000:
        raise ValidationError(_("Portal-email delivery batch size must be 1 to 1000."))
    now = now or timezone.now()
    leases_recovered = recover_expired_portal_email_leases(now=now, limit=limit)
    onboarding_started, onboarding_failed = reconcile_sent_portal_deliveries(limit=limit)
    ids = list(
        OnboardingPortalDelivery.objects.filter(
            status__in=(
                OnboardingPortalDelivery.Status.PENDING,
                OnboardingPortalDelivery.Status.RETRY,
            ),
            next_attempt_at__lte=now,
        )
        .order_by("next_attempt_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = dead = cancelled = 0
    for delivery_id in ids:
        lease_token, was_cancelled = _claim_delivery(delivery_id=delivery_id, now=now)
        if was_cancelled:
            cancelled += 1
            continue
        if lease_token is None:
            continue
        try:
            message = _load_message(delivery_id)
            if message.send() != 1:
                raise PortalDeliveryNotConfirmed
        except Exception as error:
            status = _mark_delivery_failed(
                delivery_id=delivery_id,
                lease_token=lease_token,
                error_code=type(error).__name__,
                now=now,
            )
            if status is not None:
                failed += 1
                dead += int(status == OnboardingPortalDelivery.Status.DEAD)
            continue
        if _mark_delivery_sent(
            delivery_id=delivery_id,
            lease_token=lease_token,
            now=timezone.now(),
        ):
            sent += 1
            if _start_onboarding_for_sent_delivery(delivery_id):
                onboarding_started += 1
            else:
                onboarding_failed += 1

    purge_portal_email_payloads(now=now, limit=limit)
    return PortalEmailDispatchResult(
        selected=len(ids),
        sent=sent,
        failed=failed,
        dead=dead,
        cancelled=cancelled,
        onboarding_started=onboarding_started,
        onboarding_failed=onboarding_failed,
        leases_recovered=leases_recovered,
    )


def purge_portal_delivery_payload(delivery_id):
    stub = OnboardingPortalDelivery.objects.filter(pk=delivery_id).values(
        "candidate_id", "portal_id"
    ).first()
    if not stub:
        return False
    with transaction.atomic():
        Candidate._base_manager.select_for_update(of=("self",)).get(
            pk=stub["candidate_id"]
        )
        portal = OnboardingPortal._base_manager.select_for_update().get(
            pk=stub["portal_id"]
        )
        delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=delivery_id)
        if delivery.status not in (
            OnboardingPortalDelivery.Status.SENT,
            OnboardingPortalDelivery.Status.DEAD,
            OnboardingPortalDelivery.Status.CANCELLED,
        ):
            return False
        if delivery.payload_purged_at is not None:
            return False
        if delivery.status == OnboardingPortalDelivery.Status.DEAD:
            _cancel_locked(
                delivery,
                portal=portal,
                error_code="DeadPayloadRetentionExpired",
            )
        attachments = list(delivery.attachments.select_for_update())
        for attachment in attachments:
            if attachment.file:
                try:
                    attachment.file.storage.delete(attachment.file.name)
                except OSError:
                    return False
            attachment.file = ""
            attachment.purged_at = timezone.now()
            attachment.save(update_fields=("file", "purged_at"))
        delivery.portal_token = ""
        delivery.recipient = ""
        delivery.sender = ""
        delivery.reply_to = ""
        delivery.subject = ""
        delivery.body_html = ""
        delivery.payload_purged_at = timezone.now()
        delivery.save(
            update_fields=(
                "portal_token",
                "recipient",
                "sender",
                "reply_to",
                "subject",
                "body_html",
                "payload_purged_at",
            )
        )
        _record_event(
            delivery=delivery,
            event_type=OnboardingPortalDeliveryEvent.EventType.PAYLOAD_PURGED,
        )
        return True


def purge_portal_email_payloads(*, now=None, limit):
    if not 1 <= limit <= 1000:
        raise ValidationError(_("Portal-email purge batch size must be 1 to 1000."))
    now = now or timezone.now()
    dead_cutoff = now - timedelta(hours=settings.HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS)
    ids = list(
        OnboardingPortalDelivery.objects.filter(payload_purged_at__isnull=True)
        .filter(
            Q(status__in=(OnboardingPortalDelivery.Status.SENT, OnboardingPortalDelivery.Status.CANCELLED))
            | Q(
                status=OnboardingPortalDelivery.Status.DEAD,
                last_attempt_at__lte=dead_cutoff,
            )
        )
        .order_by("requested_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    purged = 0
    for delivery_id in ids:
        purged += int(purge_portal_delivery_payload(delivery_id))
    return purged


def retry_portal_delivery(*, delivery_uuid, actor):
    retry_permissions = PORTAL_EMAIL_QUEUE_PERMISSIONS + (
        "hydra_arrivals.retry_onboardingportaldelivery",
    )
    if not actor.is_authenticated or not actor.has_perms(retry_permissions):
        raise PermissionDenied
    stub = OnboardingPortalDelivery.objects.filter(uuid=delivery_uuid).values(
        "candidate_id", "portal_id", "pk"
    ).first()
    if not stub or not linked_candidates_for_user(user=actor).filter(
        pk=stub["candidate_id"]
    ).exists():
        raise PermissionDenied
    with transaction.atomic():
        candidate = (
            Candidate._base_manager.select_for_update(of=("self",))
            .select_related("stage_id")
            .get(pk=stub["candidate_id"])
        )
        portal = OnboardingPortal._base_manager.select_for_update().get(pk=stub["portal_id"])
        delivery = OnboardingPortalDelivery.objects.select_for_update().get(pk=stub["pk"])
        if delivery.status not in (
            OnboardingPortalDelivery.Status.RETRY,
            OnboardingPortalDelivery.Status.DEAD,
        ):
            raise ValidationError(_("Only a failed portal email can be retried."))
        if delivery.payload_purged_at is not None:
            raise ValidationError(_("The retained payload has expired; queue a new portal email."))
        _validate_candidate(candidate)
        if candidate.email.casefold() != delivery.recipient.casefold():
            raise ValidationError(_("The candidate email changed; queue a new portal email."))
        if portal.used or portal.token != delivery.portal_token:
            raise ValidationError(_("The portal token was superseded; queue a new portal email."))
        previous_attempts = delivery.attempts
        delivery.status = OnboardingPortalDelivery.Status.PENDING
        delivery.attempts = 0
        delivery.next_attempt_at = timezone.now()
        delivery.last_error_code = ""
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.save(
            update_fields=(
                "status",
                "attempts",
                "next_attempt_at",
                "last_error_code",
                "lease_token",
                "lease_expires_at",
            )
        )
        delivery.attempts = previous_attempts
        _record_event(
            delivery=delivery,
            event_type=OnboardingPortalDeliveryEvent.EventType.MANUAL_RETRY,
            actor=actor,
        )
        delivery.attempts = 0
        return delivery
