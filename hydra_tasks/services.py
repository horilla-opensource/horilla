from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_people.identity import ensure_canonical_person
from hydra_people.models import Person
from hydra_people.selectors import person_for_user
from hydra_notifications.models import NotificationKind, NotificationTargetKind
from hydra_notifications.services import send_hydra_notification
from hydra_tasks.models import (
    HydraTask,
    HydraTaskEvent,
    HydraTaskNotificationDelivery,
)
from hydra_tasks.selectors import (
    companies_for_task_person,
    tasks_for_user,
    user_is_eligible_task_assignee,
)
from hydra_tasks.targets import resolve_target_for_user


ACTIVE_STATUSES = (HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS)
ALLOWED_TRANSITIONS = {
    HydraTask.Status.OPEN: {
        HydraTask.Status.IN_PROGRESS,
        HydraTask.Status.COMPLETED,
        HydraTask.Status.CANCELLED,
    },
    HydraTask.Status.IN_PROGRESS: {
        HydraTask.Status.OPEN,
        HydraTask.Status.COMPLETED,
        HydraTask.Status.CANCELLED,
    },
    HydraTask.Status.COMPLETED: {HydraTask.Status.OPEN},
    HydraTask.Status.CANCELLED: {HydraTask.Status.OPEN},
}


def _normalized_text(value, *, field, maximum, required=False):
    normalized = " ".join(str(value or "").split())
    if required and len(normalized) < 3:
        raise ValidationError({field: _("Enter at least 3 characters.")})
    if len(normalized) > maximum:
        raise ValidationError(
            {field: _("Ensure this value has at most %(limit)s characters.") % {"limit": maximum}}
        )
    return normalized


def _description(value):
    normalized = str(value or "").strip()
    if len(normalized) > 2000:
        raise ValidationError(
            {"description": _("Ensure this value has at most 2000 characters.")}
        )
    return normalized


def _expected_version(value):
    try:
        version = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({"expected_version": _("Invalid task version.")}) from error
    if version < 1:
        raise ValidationError({"expected_version": _("Invalid task version.")})
    return version


def _request_uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as error:
        raise ValidationError({"request_key": _("Invalid request key.")}) from error


def _validate_due_at(*, due_at, current_due_at=None):
    if due_at is not None and due_at != current_due_at and due_at <= timezone.now():
        raise ValidationError({"due_at": _("The due date must be in the future.")})


def _require_task_permission(actor, codename):
    if not actor.is_authenticated or not actor.has_perm(f"hydra_tasks.{codename}"):
        raise PermissionDenied


def _locked_visible_task(*, actor, task_uuid):
    visible_id = tasks_for_user(user=actor).filter(uuid=task_uuid).values_list(
        "pk", flat=True
    ).first()
    if visible_id is None:
        raise PermissionDenied
    # Lock only the owned task row. PostgreSQL rejects FOR UPDATE when a
    # select_related() path introduces a nullable outer join (created_by is
    # nullable in HorillaModel even though Hydra constrains it for tasks).
    task = HydraTask._base_manager.select_for_update().get(pk=visible_id)
    if not tasks_for_user(user=actor).filter(pk=task.pk).exists():
        raise PermissionDenied
    return task


def _create_event(
    *,
    task,
    action,
    actor,
    reason="",
    from_status="",
    to_status="",
    from_assignee=None,
    to_assignee=None,
    from_due_at=None,
    to_due_at=None,
    from_priority="",
    to_priority="",
    changed_fields=(),
):
    return HydraTaskEvent.objects.create(
        task=task,
        sequence=task.version,
        action=action,
        actor=actor,
        reason=reason,
        from_status=from_status,
        to_status=to_status,
        from_assignee=from_assignee,
        to_assignee=to_assignee,
        from_due_at=from_due_at,
        to_due_at=to_due_at,
        from_priority=from_priority,
        to_priority=to_priority,
        changed_fields=list(changed_fields),
    )


def _queue_notifications(*, event, recipients):
    delivery_ids = []
    for recipient in {recipient for recipient in recipients if recipient is not None}:
        if event.actor_id == recipient.pk:
            continue
        delivery, _created = HydraTaskNotificationDelivery.objects.get_or_create(
            event=event,
            recipient=recipient,
            defaults={"task": event.task},
        )
        delivery_ids.append(delivery.pk)
    if delivery_ids:
        transaction.on_commit(
            lambda identifiers=tuple(delivery_ids): [
                dispatch_task_notification(delivery_id)
                for delivery_id in identifiers
            ]
        )


@transaction.atomic
def create_task(
    *,
    actor,
    person_uuid,
    company,
    assignee,
    title,
    description="",
    priority=HydraTask.Priority.NORMAL,
    due_at=None,
    target_reference,
    request_key,
):
    _require_task_permission(actor, "add_hydratask")
    person = person_for_user(user=actor, person_uuid=person_uuid)
    ensure_canonical_person(person)
    person = Person._base_manager.select_for_update().get(pk=person.pk)
    if not companies_for_task_person(user=actor, person=person).filter(
        pk=company.pk
    ).exists():
        raise ValidationError({"company": _("This Company is outside your scope.")})
    if not user_is_eligible_task_assignee(
        user=assignee,
        person=person,
        company=company,
    ):
        raise ValidationError(
            {"assignee": _("The assignee lacks current task permissions or Person scope.")}
        )
    if priority not in HydraTask.Priority.values:
        raise ValidationError({"priority": _("Select a valid priority.")})
    _validate_due_at(due_at=due_at)
    title = _normalized_text(title, field="title", maximum=180, required=True)
    description = _description(description)
    target = resolve_target_for_user(
        user=actor,
        person=person,
        company=company,
        target_reference=target_reference,
    )
    request_key = _request_uuid(request_key)
    existing = HydraTask._base_manager.filter(request_key=request_key).first()
    if existing is not None:
        expected = (
            existing.created_by_id == actor.pk
            and existing.person_id == person.pk
            and existing.company_id == company.pk
            and existing.assignee_id == assignee.pk
            and existing.title == title
            and existing.description == description
            and existing.priority == priority
            and existing.due_at == due_at
            and existing.target_kind == target.kind
            and existing.target_uuid == target.uuid
        )
        if not expected:
            raise ValidationError(
                {"request_key": _("This request key was already used for different data.")}
            )
        return existing

    task = HydraTask(
        request_key=request_key,
        company=company,
        person=person,
        assignee=assignee,
        title=title,
        description=description,
        priority=priority,
        due_at=due_at,
        target_kind=target.kind,
        target_uuid=target.uuid,
        target_label=target.label,
        created_by=actor,
        modified_by=actor,
    )
    task.full_clean()
    task.save(force_insert=True)
    event = _create_event(
        task=task,
        action=HydraTaskEvent.Action.CREATED,
        actor=actor,
        to_status=task.status,
        to_assignee=assignee,
        to_due_at=task.due_at,
        to_priority=task.priority,
        changed_fields=(
            "company",
            "person",
            "target",
            "assignee",
            "title",
            "description",
            "priority",
            "due_at",
            "status",
        ),
    )
    _queue_notifications(event=event, recipients=(assignee,))
    return task


@transaction.atomic
def update_task(
    *,
    actor,
    task_uuid,
    expected_version,
    title,
    description,
    priority,
    due_at,
):
    _require_task_permission(actor, "change_hydratask")
    task = _locked_visible_task(actor=actor, task_uuid=task_uuid)
    expected_version = _expected_version(expected_version)
    if task.version != expected_version:
        raise ValidationError(
            {"expected_version": _("The task changed. Reload it before saving.")}
        )
    if task.status not in ACTIVE_STATUSES:
        raise ValidationError(_("Completed or cancelled tasks must be reopened first."))
    if priority not in HydraTask.Priority.values:
        raise ValidationError({"priority": _("Select a valid priority.")})
    _validate_due_at(due_at=due_at, current_due_at=task.due_at)
    title = _normalized_text(title, field="title", maximum=180, required=True)
    description = _description(description)

    previous_due_at = task.due_at
    previous_priority = task.priority
    changed_fields = []
    for field, value in (
        ("title", title),
        ("description", description),
        ("priority", priority),
        ("due_at", due_at),
    ):
        if getattr(task, field) != value:
            setattr(task, field, value)
            changed_fields.append(field)
    if not changed_fields:
        return task
    task.version += 1
    task.modified_by = actor
    task.full_clean()
    task.save(
        service_update=True,
        update_fields=tuple(changed_fields) + ("version", "modified_by"),
    )
    event = _create_event(
        task=task,
        action=HydraTaskEvent.Action.UPDATED,
        actor=actor,
        from_status=task.status,
        to_status=task.status,
        from_assignee=task.assignee,
        to_assignee=task.assignee,
        from_due_at=previous_due_at,
        to_due_at=task.due_at,
        from_priority=previous_priority,
        to_priority=task.priority,
        changed_fields=changed_fields,
    )
    _queue_notifications(event=event, recipients=(task.assignee,))
    return task


@transaction.atomic
def reassign_task(
    *,
    actor,
    task_uuid,
    expected_version,
    assignee,
    reason,
):
    _require_task_permission(actor, "assign_hydratask")
    task = _locked_visible_task(actor=actor, task_uuid=task_uuid)
    expected_version = _expected_version(expected_version)
    if task.version != expected_version:
        raise ValidationError(
            {"expected_version": _("The task changed. Reload it before assigning.")}
        )
    if task.status not in ACTIVE_STATUSES:
        raise ValidationError(_("Completed or cancelled tasks cannot be reassigned."))
    if task.assignee_id == assignee.pk:
        raise ValidationError({"assignee": _("Select a different assignee.")})
    if not user_is_eligible_task_assignee(
        user=assignee,
        person=task.person,
        company=task.company,
    ):
        raise ValidationError(
            {"assignee": _("The assignee lacks current task permissions or Person scope.")}
        )
    reason = _normalized_text(reason, field="reason", maximum=500, required=True)
    previous_assignee = task.assignee
    task.assignee = assignee
    task.version += 1
    task.modified_by = actor
    task.full_clean()
    task.save(
        service_update=True,
        update_fields=("assignee", "version", "modified_by"),
    )
    event = _create_event(
        task=task,
        action=HydraTaskEvent.Action.REASSIGNED,
        actor=actor,
        reason=reason,
        from_status=task.status,
        to_status=task.status,
        from_assignee=previous_assignee,
        to_assignee=assignee,
        from_due_at=task.due_at,
        to_due_at=task.due_at,
        from_priority=task.priority,
        to_priority=task.priority,
        changed_fields=("assignee",),
    )
    _queue_notifications(event=event, recipients=(assignee,))
    return task


@transaction.atomic
def transition_task(
    *,
    actor,
    task_uuid,
    expected_version,
    to_status,
    reason="",
):
    _require_task_permission(actor, "transition_hydratask")
    task = _locked_visible_task(actor=actor, task_uuid=task_uuid)
    if task.assignee_id != actor.pk and not (
        actor.is_superuser or actor.has_perm("hydra_tasks.view_all_hydratask")
    ):
        raise PermissionDenied
    expected_version = _expected_version(expected_version)
    if task.version != expected_version:
        raise ValidationError(
            {"expected_version": _("The task changed. Reload it before changing status.")}
        )
    if to_status not in HydraTask.Status.values:
        raise ValidationError({"to_status": _("Select a valid status.")})
    if to_status not in ALLOWED_TRANSITIONS.get(task.status, set()):
        raise ValidationError({"to_status": _("This task transition is not allowed.")})

    terminal_or_reopen = to_status in (
        HydraTask.Status.COMPLETED,
        HydraTask.Status.CANCELLED,
    ) or task.status in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED)
    reason = _normalized_text(
        reason,
        field="reason",
        maximum=500,
        required=terminal_or_reopen,
    )
    if task.status in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED):
        _require_task_permission(actor, "reopen_hydratask")

    previous_status = task.status
    task.status = to_status
    task.version += 1
    task.modified_by = actor
    if to_status == HydraTask.Status.COMPLETED:
        task.completed_at = timezone.now()
        task.cancelled_at = None
        task.resolution_reason = reason
        action = HydraTaskEvent.Action.COMPLETED
    elif to_status == HydraTask.Status.CANCELLED:
        task.completed_at = None
        task.cancelled_at = timezone.now()
        task.resolution_reason = reason
        action = HydraTaskEvent.Action.CANCELLED
    else:
        task.completed_at = None
        task.cancelled_at = None
        task.resolution_reason = ""
        action = (
            HydraTaskEvent.Action.REOPENED
            if previous_status
            in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED)
            else HydraTaskEvent.Action.STATUS_CHANGED
        )
    task.full_clean()
    task.save(
        service_update=True,
        update_fields=(
            "status",
            "completed_at",
            "cancelled_at",
            "resolution_reason",
            "version",
            "modified_by",
        ),
    )
    event = _create_event(
        task=task,
        action=action,
        actor=actor,
        reason=reason,
        from_status=previous_status,
        to_status=to_status,
        from_assignee=task.assignee,
        to_assignee=task.assignee,
        from_due_at=task.due_at,
        to_due_at=task.due_at,
        from_priority=task.priority,
        to_priority=task.priority,
        changed_fields=("status",),
    )
    recipients = [task.assignee]
    if to_status in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED):
        recipients.append(task.created_by)
    _queue_notifications(event=event, recipients=recipients)
    return task


def _notification_kind(event):
    return {
        HydraTaskEvent.Action.CREATED: NotificationKind.TASK_ASSIGNED,
        HydraTaskEvent.Action.UPDATED: NotificationKind.TASK_UPDATED,
        HydraTaskEvent.Action.REASSIGNED: NotificationKind.TASK_REASSIGNED,
        HydraTaskEvent.Action.STATUS_CHANGED: NotificationKind.TASK_STATUS_CHANGED,
        HydraTaskEvent.Action.COMPLETED: NotificationKind.TASK_COMPLETED,
        HydraTaskEvent.Action.CANCELLED: NotificationKind.TASK_CANCELLED,
        HydraTaskEvent.Action.REOPENED: NotificationKind.TASK_REOPENED,
    }[event.action]


def dispatch_task_notification(delivery_id):
    try:
        with transaction.atomic():
            # Keep nullable event.actor out of the locking query. Related rows
            # are loaded lazily inside this transaction and do not need locks.
            delivery = HydraTaskNotificationDelivery.objects.select_for_update().get(
                pk=delivery_id
            )
            if delivery.status in (
                HydraTaskNotificationDelivery.Status.SENT,
                HydraTaskNotificationDelivery.Status.NOT_APPLICABLE,
            ):
                return True
            if not delivery.recipient.is_active or not tasks_for_user(
                user=delivery.recipient
            ).filter(pk=delivery.task_id).exists():
                delivery.status = HydraTaskNotificationDelivery.Status.NOT_APPLICABLE
                delivery.last_attempt_at = timezone.now()
                delivery.error_code = ""
                delivery.save(
                    update_fields=("status", "last_attempt_at", "error_code")
                )
                return True

            notification = send_hydra_notification(
                actor=delivery.event.actor or delivery.task,
                recipient=delivery.recipient,
                kind=_notification_kind(delivery.event),
                target_kind=NotificationTargetKind.HYDRA_TASK,
                target_uuid=delivery.task.uuid,
                redirect_path=delivery.task.get_absolute_url(),
                idempotency_key=f"task-delivery:{delivery.uuid}",
            )
            delivery.notification = notification
            delivery.status = HydraTaskNotificationDelivery.Status.SENT
            delivery.attempts += 1
            delivery.last_attempt_at = timezone.now()
            delivery.error_code = ""
            delivery.save(
                update_fields=(
                    "notification",
                    "status",
                    "attempts",
                    "last_attempt_at",
                    "error_code",
                )
            )
            return True
    except Exception as error:
        HydraTaskNotificationDelivery.objects.filter(pk=delivery_id).update(
            status=HydraTaskNotificationDelivery.Status.FAILED,
            attempts=F("attempts") + 1,
            last_attempt_at=timezone.now(),
            error_code=type(error).__name__[:80],
        )
        return False


def dispatch_pending_task_notifications(*, limit=100):
    if limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    max_attempts = settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS
    delivery_ids = list(
        HydraTaskNotificationDelivery.objects.filter(
            status__in=(
                HydraTaskNotificationDelivery.Status.PENDING,
                HydraTaskNotificationDelivery.Status.FAILED,
            ),
            attempts__lt=max_attempts,
        )
        .order_by("created_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    sent = failed = 0
    for delivery_id in delivery_ids:
        if dispatch_task_notification(delivery_id):
            sent += 1
        else:
            failed += 1
    return sent, failed, len(delivery_ids)
