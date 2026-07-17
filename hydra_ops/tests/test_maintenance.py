from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from hydra_arrivals.automation import ArrivalAutomationResult
from hydra_arrivals.onboarding import HandoffReconciliationResult
from hydra_arrivals.portal_email import PortalEmailDispatchResult
from hydra_legalization.automation import LegalizationAutomationResult
from hydra_housing.services import HousingReservationExpiryResult
from hydra_ops.maintenance import (
    MaintenanceCycleResult,
    acquire_maintenance_lock,
    maintenance_health,
    release_maintenance_lock,
    run_maintenance_cycle,
    start_maintenance_state,
)
from hydra_ops.models import MaintenanceState


@override_settings(
    HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE=25,
    HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE=100,
    HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE=80,
    HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE=40,
    HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE=35,
    HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE=45,
    HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE=30,
    HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=20,
    HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS=3600,
    HYDRA_MAINTENANCE_STALE_SECONDS=120,
    HYDRA_MAINTENANCE_MAX_FAILURES=3,
    HYDRA_NOTIFICATION_MAX_ATTEMPTS=10,
)
class MaintenanceCycleTests(TestCase):
    def test_cycle_dispatches_notifications_purges_storage_and_heartbeats(self):
        owner = uuid4()
        now = timezone.now()
        start_maintenance_state(owner_uuid=owner, now=now)

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(2, 0, 2),
        ) as dispatch, patch(
            "hydra_ops.maintenance.dispatch_pending_legalization_work_notifications",
            return_value=(3, 0, 3),
        ) as work_dispatch, patch(
            "hydra_ops.maintenance.dispatch_pending_task_notifications",
            return_value=(4, 0, 4),
        ) as task_dispatch, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=3
        ) as purge_quarantine, patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=1
        ) as purge_deleted, patch(
            "hydra_ops.maintenance.purge_expired_candidate_import_data",
            return_value=2,
        ) as purge_imports:
            result = run_maintenance_cycle(
                owner_uuid=owner, now=now, force_document_purge=True
            )

        dispatch.assert_called_once_with(limit=25)
        work_dispatch.assert_called_once_with(limit=25)
        task_dispatch.assert_called_once_with(limit=25)
        purge_quarantine.assert_called_once_with(now=now, limit=100)
        purge_deleted.assert_called_once_with(now=now, limit=100)
        purge_imports.assert_called_once_with(now=now, limit=80)
        self.assertEqual(result.notifications_sent, 2)
        self.assertEqual(result.legalization_work_notifications_sent, 3)
        self.assertEqual(result.legalization_work_notifications_selected, 3)
        self.assertEqual(result.task_notifications_sent, 4)
        self.assertEqual(result.task_notifications_selected, 4)
        self.assertEqual(result.quarantine_purged, 3)
        self.assertEqual(result.deleted_documents_purged, 1)
        self.assertEqual(result.candidate_imports_purged, 2)
        self.assertFalse(result.errors)
        state = MaintenanceState.objects.get(pk="primary")
        self.assertEqual(state.consecutive_failures, 0)
        self.assertIsNotNone(state.last_success_at)
        self.assertIsNotNone(state.last_legalization_run_at)
        self.assertIsNotNone(state.last_arrival_run_at)
        self.assertIsNotNone(state.last_onboarding_reconcile_at)
        self.assertIsNotNone(state.last_portal_email_dispatch_at)
        self.assertIsNotNone(state.last_document_purge_at)
        self.assertTrue(maintenance_health()[0])

    def test_cycle_runs_bounded_legalization_automation(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)
        automation_result = LegalizationAutomationResult(
            cases_selected=3,
            events_created=2,
            cases_expired=1,
            notifications_sent=2,
            notifications_failed=0,
            notifications_selected=2,
        )

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.run_legalization_automation",
            return_value=automation_result,
        ) as automation, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner, force_document_purge=True
            )

        automation.assert_called_once_with(
            case_limit=40,
            notification_limit=25,
        )
        self.assertEqual(result.legalization_cases_selected, 3)
        self.assertEqual(result.legalization_events_created, 2)
        self.assertEqual(result.legalization_cases_expired, 1)
        self.assertEqual(result.legalization_notifications_sent, 2)

    def test_cycle_runs_bounded_arrival_automation(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)
        automation_result = ArrivalAutomationResult(
            plans_selected=4,
            events_created=3,
            notifications_sent=2,
            notifications_failed=0,
            notifications_selected=2,
        )

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.run_arrival_automation",
            return_value=automation_result,
        ) as automation, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner, force_document_purge=True
            )

        automation.assert_called_once_with(
            plan_limit=35,
            notification_limit=25,
        )
        self.assertEqual(result.arrival_plans_selected, 4)
        self.assertEqual(result.arrival_events_created, 3)
        self.assertEqual(result.arrival_notifications_sent, 2)

    def test_cycle_runs_bounded_housing_reservation_expiry(self):
        owner = uuid4()
        now = timezone.now()
        start_maintenance_state(owner_uuid=owner, now=now)
        expiry_result = HousingReservationExpiryResult(selected=5, expired=4)

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.expire_due_housing_reservations",
            return_value=expiry_result,
        ) as expiry, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner,
                now=now,
                force_document_purge=True,
            )

        expiry.assert_called_once_with(now=now, limit=45)
        self.assertEqual(result.housing_reservations_selected, 5)
        self.assertEqual(result.housing_reservations_expired, 4)
        self.assertIsNotNone(
            MaintenanceState.objects.get(pk="primary").last_housing_run_at
        )

    def test_cycle_runs_bounded_onboarding_reconciliation(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)
        reconciliation_result = HandoffReconciliationResult(
            handoffs_selected=5,
            handoffs_updated=3,
            handoffs_completed=2,
        )

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.reconcile_open_onboarding_handoffs",
            return_value=reconciliation_result,
        ) as reconciliation, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner, force_document_purge=True
            )

        reconciliation.assert_called_once_with(batch_size=30)
        self.assertEqual(result.onboarding_handoffs_selected, 5)
        self.assertEqual(result.onboarding_handoffs_updated, 3)
        self.assertEqual(result.onboarding_handoffs_completed, 2)

    def test_cycle_dispatches_bounded_portal_email_outbox(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)
        dispatch_result = PortalEmailDispatchResult(
            selected=4,
            sent=2,
            failed=1,
            dead=0,
            cancelled=1,
            onboarding_started=2,
            onboarding_failed=0,
            leases_recovered=1,
        )

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.dispatch_portal_emails",
            return_value=dispatch_result,
        ) as dispatch, patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner,
                force_document_purge=True,
            )

        dispatch.assert_called_once()
        self.assertEqual(dispatch.call_args.kwargs["limit"], 20)
        self.assertEqual(result.portal_emails_selected, 4)
        self.assertEqual(result.portal_emails_sent, 2)
        self.assertEqual(result.portal_emails_failed, 1)
        self.assertIn("PortalEmailDeliveryFailed", result.errors)

    def test_failure_records_only_error_type_and_trips_health_threshold(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            side_effect=ValueError("secret backend detail"),
        ), patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            for _ in range(3):
                result = run_maintenance_cycle(
                    owner_uuid=owner, force_document_purge=True
                )

        self.assertEqual(result.errors, ("ValueError",))
        state = MaintenanceState.objects.get(pk="primary")
        self.assertEqual(state.consecutive_failures, 3)
        self.assertEqual(state.last_error_code, "ValueError")
        self.assertNotIn("secret", state.last_error_code)
        ok, detail = maintenance_health()
        self.assertFalse(ok)
        self.assertIn("threshold", detail)

    def test_full_document_batch_keeps_purge_due_to_drain_backlog(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=100
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ):
            run_maintenance_cycle(owner_uuid=owner, force_document_purge=True)

        state = MaintenanceState.objects.get(pk="primary")
        self.assertIsNone(state.last_document_purge_at)

    def test_full_import_batch_keeps_purge_due_to_drain_backlog(self):
        owner = uuid4()
        start_maintenance_state(owner_uuid=owner)

        with patch(
            "hydra_ops.maintenance.dispatch_pending_organization_notifications",
            return_value=(0, 0, 0),
        ), patch(
            "hydra_ops.maintenance.purge_expired_quarantine", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_deleted_document_files", return_value=0
        ), patch(
            "hydra_ops.maintenance.purge_expired_candidate_import_data",
            return_value=80,
        ):
            result = run_maintenance_cycle(
                owner_uuid=owner,
                force_document_purge=True,
            )

        state = MaintenanceState.objects.get(pk="primary")
        self.assertEqual(result.candidate_imports_purged, 80)
        self.assertIsNone(state.last_document_purge_at)

    def test_stale_heartbeat_is_unhealthy(self):
        start_maintenance_state(
            owner_uuid=uuid4(), now=timezone.now() - timedelta(minutes=5)
        )

        ok, detail = maintenance_health()

        self.assertFalse(ok)
        self.assertIn("stale", detail)

    def test_worker_restart_preserves_failure_alarm_state(self):
        original_owner = uuid4()
        start_maintenance_state(owner_uuid=original_owner)
        state = MaintenanceState.objects.get(pk="primary")
        state.consecutive_failures = 3
        state.last_error_code = "OrganizationNotificationRetriesExhausted"
        state.save(update_fields=("consecutive_failures", "last_error_code"))

        replacement_owner = uuid4()
        start_maintenance_state(owner_uuid=replacement_owner)

        state.refresh_from_db()
        self.assertEqual(state.owner_uuid, replacement_owner)
        self.assertEqual(state.consecutive_failures, 3)
        self.assertEqual(
            state.last_error_code, "OrganizationNotificationRetriesExhausted"
        )

    def test_worker_once_uses_lock_and_releases_it(self):
        result = MaintenanceCycleResult(0, 0, 0, 0, 0, ())
        output = StringIO()

        with patch(
            "hydra_ops.management.commands.run_hydra_maintenance.acquire_maintenance_lock",
            return_value=True,
        ) as acquire, patch(
            "hydra_ops.management.commands.run_hydra_maintenance.release_maintenance_lock"
        ) as release, patch(
            "hydra_ops.management.commands.run_hydra_maintenance.run_maintenance_cycle",
            return_value=result,
        ):
            call_command("run_hydra_maintenance", "--once", stdout=output)

        acquire.assert_called_once_with()
        release.assert_called_once_with()
        self.assertIn("maintenance cycle", output.getvalue())

    def test_worker_refuses_to_run_without_single_owner_lock(self):
        with patch(
            "hydra_ops.management.commands.run_hydra_maintenance.acquire_maintenance_lock",
            return_value=False,
        ):
            with self.assertRaises(CommandError):
                call_command("run_hydra_maintenance", "--once", stdout=StringIO())

    def test_postgresql_advisory_lock_round_trip(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL-only advisory lock")
        try:
            self.assertTrue(acquire_maintenance_lock())
        finally:
            release_maintenance_lock()

    def test_health_command_fails_without_worker_state(self):
        with self.assertRaises(CommandError):
            call_command("hydra_maintenance_health", stdout=StringIO())
