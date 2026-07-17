from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import connection, transaction
from django.db.utils import OperationalError
from django.utils import timezone

from hydra_arrivals.automation import run_arrival_automation
from hydra_arrivals.models import ArrivalAutomationEvent, OnboardingPortalDelivery
from hydra_arrivals.onboarding import reconcile_open_onboarding_handoffs
from hydra_arrivals.portal_email import dispatch_portal_emails
from hydra_coordination.services import dispatch_pending_organization_notifications
from hydra_coordination.models import OrganizationAccessEvent
from hydra_documents.services import (
    purge_deleted_document_files,
    purge_expired_quarantine,
)
from hydra_imports.services import purge_expired_candidate_import_data
from hydra_legalization.automation import run_legalization_automation
from hydra_legalization.models import LegalizationAutomationEvent, LegalizationWorkEvent
from hydra_legalization.workload import (
    dispatch_pending_legalization_work_notifications,
)
from hydra_housing.services import expire_due_housing_reservations
from hydra_notifications.models import HydraNotificationEmailDelivery
from hydra_notifications.services import dispatch_pending_notification_emails
from hydra_ops.models import MaintenanceState
from hydra_tasks.models import HydraTaskNotificationDelivery
from hydra_tasks.services import dispatch_pending_task_notifications


MAINTENANCE_STATE_KEY = "primary"
MAINTENANCE_ADVISORY_LOCK_ID = 0x48594452414D4149


@dataclass(frozen=True)
class MaintenanceCycleResult:
    notifications_sent: int
    notifications_failed: int
    notifications_selected: int
    quarantine_purged: int
    deleted_documents_purged: int
    errors: tuple[str, ...]
    legalization_cases_selected: int = 0
    legalization_events_created: int = 0
    legalization_cases_expired: int = 0
    legalization_notifications_sent: int = 0
    legalization_notifications_failed: int = 0
    legalization_notifications_selected: int = 0
    arrival_plans_selected: int = 0
    arrival_events_created: int = 0
    arrival_notifications_sent: int = 0
    arrival_notifications_failed: int = 0
    arrival_notifications_selected: int = 0
    housing_reservations_selected: int = 0
    housing_reservations_expired: int = 0
    onboarding_handoffs_selected: int = 0
    onboarding_handoffs_updated: int = 0
    onboarding_handoffs_completed: int = 0
    portal_emails_selected: int = 0
    portal_emails_sent: int = 0
    portal_emails_failed: int = 0
    portal_emails_dead: int = 0
    portal_emails_cancelled: int = 0
    portal_email_onboarding_started: int = 0
    portal_email_onboarding_failed: int = 0
    portal_email_leases_recovered: int = 0
    candidate_imports_purged: int = 0
    legalization_work_notifications_sent: int = 0
    legalization_work_notifications_failed: int = 0
    legalization_work_notifications_selected: int = 0
    task_notifications_sent: int = 0
    task_notifications_failed: int = 0
    task_notifications_selected: int = 0
    notification_emails_selected: int = 0
    notification_emails_sent: int = 0
    notification_emails_failed: int = 0
    notification_emails_dead: int = 0
    notification_emails_not_applicable: int = 0
    notification_email_leases_recovered: int = 0


def acquire_maintenance_lock():
    if connection.vendor != "postgresql":
        raise RuntimeError("Hydra maintenance requires PostgreSQL advisory locks")
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [MAINTENANCE_ADVISORY_LOCK_ID])
        return bool(cursor.fetchone()[0])


def release_maintenance_lock():
    if connection.vendor != "postgresql" or connection.connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [MAINTENANCE_ADVISORY_LOCK_ID])
    except OperationalError:
        pass


def start_maintenance_state(*, owner_uuid=None, now=None):
    owner_uuid = owner_uuid or uuid4()
    now = now or timezone.now()
    state, created = MaintenanceState.objects.get_or_create(
        key=MAINTENANCE_STATE_KEY,
        defaults={
            "owner_uuid": owner_uuid,
            "started_at": now,
            "heartbeat_at": now,
            "last_cycle_started_at": None,
            "last_cycle_completed_at": None,
            "consecutive_failures": 0,
            "last_error_code": "",
        },
    )
    if not created:
        state.owner_uuid = owner_uuid
        state.started_at = now
        state.heartbeat_at = now
        state.last_cycle_started_at = None
        state.last_cycle_completed_at = None
        state.save(
            update_fields=(
                "owner_uuid",
                "started_at",
                "heartbeat_at",
                "last_cycle_started_at",
                "last_cycle_completed_at",
            )
        )
    return state


def run_maintenance_cycle(*, owner_uuid, now=None, force_document_purge=False):
    now = now or timezone.now()
    with transaction.atomic():
        state = MaintenanceState.objects.select_for_update().get(
            key=MAINTENANCE_STATE_KEY,
            owner_uuid=owner_uuid,
        )
        state.heartbeat_at = now
        state.last_cycle_started_at = now
        state.save(update_fields=("heartbeat_at", "last_cycle_started_at"))

    sent = failed = selected = 0
    work_sent = work_failed = work_selected = 0
    task_sent = task_failed = task_selected = 0
    legalization_result = None
    legalization_succeeded = False
    arrival_result = None
    arrival_succeeded = False
    housing_result = None
    housing_succeeded = False
    onboarding_result = None
    onboarding_succeeded = False
    notification_email_result = None
    quarantine_purged = deleted_purged = candidate_imports_purged = 0
    errors = []
    try:
        sent, failed, selected = dispatch_pending_organization_notifications(
            limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE
        )
        if failed:
            errors.append("OrganizationNotificationDeliveryFailed")
        if OrganizationAccessEvent.objects.filter(
            notification_status=OrganizationAccessEvent.NotificationStatus.FAILED,
            notification_attempts__gte=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        ).exists():
            errors.append("OrganizationNotificationRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        task_sent, task_failed, task_selected = dispatch_pending_task_notifications(
            limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE
        )
        if task_failed:
            errors.append("TaskNotificationDeliveryFailed")
        if HydraTaskNotificationDelivery.objects.filter(
            status=HydraTaskNotificationDelivery.Status.FAILED,
            attempts__gte=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        ).exists():
            errors.append("TaskNotificationRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        work_sent, work_failed, work_selected = (
            dispatch_pending_legalization_work_notifications(
                limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE
            )
        )
        if work_failed:
            errors.append("LegalizationWorkNotificationDeliveryFailed")
        if LegalizationWorkEvent.objects.filter(
            notification_status=LegalizationWorkEvent.NotificationStatus.FAILED,
            notification_attempts__gte=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        ).exists():
            errors.append("LegalizationWorkNotificationRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    portal_email_result = None
    portal_email_succeeded = False
    try:
        portal_email_result = dispatch_portal_emails(
            limit=settings.HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE,
            now=now,
        )
        portal_email_succeeded = True
        if portal_email_result.failed:
            errors.append("PortalEmailDeliveryFailed")
        if portal_email_result.dead or OnboardingPortalDelivery.objects.filter(
            status=OnboardingPortalDelivery.Status.DEAD,
        ).exists():
            errors.append("PortalEmailRetriesExhausted")
        if portal_email_result.onboarding_failed:
            errors.append("PortalEmailOnboardingFailed")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        legalization_result = run_legalization_automation(
            case_limit=settings.HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE,
            notification_limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE,
        )
        legalization_succeeded = True
        if legalization_result.notifications_failed:
            errors.append("LegalizationNotificationDeliveryFailed")
        if LegalizationAutomationEvent.objects.filter(
            notification_status=LegalizationAutomationEvent.NotificationStatus.FAILED,
            notification_attempts__gte=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        ).exists():
            errors.append("LegalizationNotificationRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        arrival_result = run_arrival_automation(
            plan_limit=settings.HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE,
            notification_limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE,
        )
        arrival_succeeded = True
        if arrival_result.notifications_failed:
            errors.append("ArrivalNotificationDeliveryFailed")
        if ArrivalAutomationEvent.objects.filter(
            notification_status=ArrivalAutomationEvent.NotificationStatus.FAILED,
            notification_attempts__gte=settings.HYDRA_NOTIFICATION_MAX_ATTEMPTS,
        ).exists():
            errors.append("ArrivalNotificationRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        housing_result = expire_due_housing_reservations(
            now=now,
            limit=settings.HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE,
        )
        housing_succeeded = True
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        onboarding_result = reconcile_open_onboarding_handoffs(
            batch_size=settings.HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE,
        )
        onboarding_succeeded = True
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    try:
        notification_email_result = dispatch_pending_notification_emails(
            limit=settings.HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE,
            now=now,
        )
        if notification_email_result.failed:
            errors.append("NotificationEmailDeliveryFailed")
        if notification_email_result.dead or HydraNotificationEmailDelivery.objects.filter(
            status=HydraNotificationEmailDelivery.Status.DEAD
        ).exists():
            errors.append("NotificationEmailRetriesExhausted")
    except OperationalError:
        raise
    except Exception as error:
        errors.append(type(error).__name__[:120])

    state = MaintenanceState.objects.get(
        key=MAINTENANCE_STATE_KEY, owner_uuid=owner_uuid
    )
    purge_due = force_document_purge or state.last_document_purge_at is None or (
        state.last_document_purge_at
        <= now - timedelta(seconds=settings.HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS)
    )
    purge_succeeded = False
    purge_complete = False
    if purge_due:
        try:
            batch_size = settings.HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE
            quarantine_purged = purge_expired_quarantine(
                now=now, limit=batch_size
            )
            deleted_purged = purge_deleted_document_files(
                now=now, limit=batch_size
            )
            import_batch_size = settings.HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE
            candidate_imports_purged = purge_expired_candidate_import_data(
                now=now,
                limit=import_batch_size,
            )
            purge_succeeded = True
            purge_complete = (
                quarantine_purged < batch_size and deleted_purged < batch_size
                and candidate_imports_purged < import_batch_size
            )
        except OperationalError:
            raise
        except Exception as error:
            errors.append(type(error).__name__[:120])

    completed_at = timezone.now()
    with transaction.atomic():
        state = MaintenanceState.objects.select_for_update().get(
            key=MAINTENANCE_STATE_KEY,
            owner_uuid=owner_uuid,
        )
        state.heartbeat_at = completed_at
        state.last_cycle_completed_at = completed_at
        state.last_notification_dispatch_at = completed_at
        if legalization_succeeded:
            state.last_legalization_run_at = completed_at
        if arrival_succeeded:
            state.last_arrival_run_at = completed_at
        if housing_succeeded:
            state.last_housing_run_at = completed_at
        if onboarding_succeeded:
            state.last_onboarding_reconcile_at = completed_at
        if portal_email_succeeded:
            state.last_portal_email_dispatch_at = completed_at
        if purge_due and purge_succeeded and purge_complete:
            state.last_document_purge_at = completed_at
        if errors:
            state.consecutive_failures += 1
            state.last_error_code = ",".join(errors)[:120]
        else:
            state.consecutive_failures = 0
            state.last_error_code = ""
            state.last_success_at = completed_at
        state.save(
            update_fields=(
                "heartbeat_at",
                "last_cycle_completed_at",
                "last_notification_dispatch_at",
                "last_legalization_run_at",
                "last_arrival_run_at",
                "last_housing_run_at",
                "last_onboarding_reconcile_at",
                "last_portal_email_dispatch_at",
                "last_document_purge_at",
                "consecutive_failures",
                "last_error_code",
                "last_success_at",
            )
        )
    return MaintenanceCycleResult(
        notifications_sent=sent,
        notifications_failed=failed,
        notifications_selected=selected,
        quarantine_purged=quarantine_purged,
        deleted_documents_purged=deleted_purged,
        errors=tuple(errors),
        legalization_cases_selected=(
            legalization_result.cases_selected if legalization_result else 0
        ),
        legalization_events_created=(
            legalization_result.events_created if legalization_result else 0
        ),
        legalization_cases_expired=(
            legalization_result.cases_expired if legalization_result else 0
        ),
        legalization_notifications_sent=(
            legalization_result.notifications_sent if legalization_result else 0
        ),
        legalization_notifications_failed=(
            legalization_result.notifications_failed if legalization_result else 0
        ),
        legalization_notifications_selected=(
            legalization_result.notifications_selected if legalization_result else 0
        ),
        arrival_plans_selected=(
            arrival_result.plans_selected if arrival_result else 0
        ),
        arrival_events_created=(
            arrival_result.events_created if arrival_result else 0
        ),
        arrival_notifications_sent=(
            arrival_result.notifications_sent if arrival_result else 0
        ),
        arrival_notifications_failed=(
            arrival_result.notifications_failed if arrival_result else 0
        ),
        arrival_notifications_selected=(
            arrival_result.notifications_selected if arrival_result else 0
        ),
        housing_reservations_selected=(
            housing_result.selected if housing_result else 0
        ),
        housing_reservations_expired=(
            housing_result.expired if housing_result else 0
        ),
        onboarding_handoffs_selected=(
            onboarding_result.handoffs_selected if onboarding_result else 0
        ),
        onboarding_handoffs_updated=(
            onboarding_result.handoffs_updated if onboarding_result else 0
        ),
        onboarding_handoffs_completed=(
            onboarding_result.handoffs_completed if onboarding_result else 0
        ),
        portal_emails_selected=(portal_email_result.selected if portal_email_result else 0),
        portal_emails_sent=(portal_email_result.sent if portal_email_result else 0),
        portal_emails_failed=(portal_email_result.failed if portal_email_result else 0),
        portal_emails_dead=(portal_email_result.dead if portal_email_result else 0),
        portal_emails_cancelled=(
            portal_email_result.cancelled if portal_email_result else 0
        ),
        portal_email_onboarding_started=(
            portal_email_result.onboarding_started if portal_email_result else 0
        ),
        portal_email_onboarding_failed=(
            portal_email_result.onboarding_failed if portal_email_result else 0
        ),
        portal_email_leases_recovered=(
            portal_email_result.leases_recovered if portal_email_result else 0
        ),
        candidate_imports_purged=candidate_imports_purged,
        legalization_work_notifications_sent=work_sent,
        legalization_work_notifications_failed=work_failed,
        legalization_work_notifications_selected=work_selected,
        task_notifications_sent=task_sent,
        task_notifications_failed=task_failed,
        task_notifications_selected=task_selected,
        notification_emails_selected=(
            notification_email_result.selected if notification_email_result else 0
        ),
        notification_emails_sent=(
            notification_email_result.sent if notification_email_result else 0
        ),
        notification_emails_failed=(
            notification_email_result.failed if notification_email_result else 0
        ),
        notification_emails_dead=(
            notification_email_result.dead if notification_email_result else 0
        ),
        notification_emails_not_applicable=(
            notification_email_result.not_applicable
            if notification_email_result
            else 0
        ),
        notification_email_leases_recovered=(
            notification_email_result.leases_recovered
            if notification_email_result
            else 0
        ),
    )


def maintenance_health(*, now=None):
    now = now or timezone.now()
    try:
        state = MaintenanceState.objects.get(key=MAINTENANCE_STATE_KEY)
    except MaintenanceState.DoesNotExist:
        return False, "maintenance worker has not registered"
    stale_before = now - timedelta(seconds=settings.HYDRA_MAINTENANCE_STALE_SECONDS)
    if state.heartbeat_at < stale_before:
        return False, "maintenance heartbeat is stale"
    if state.consecutive_failures >= settings.HYDRA_MAINTENANCE_MAX_FAILURES:
        return False, "maintenance failure threshold was reached"
    return True, "maintenance worker is healthy"
