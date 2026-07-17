from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from hydra_arrivals.automation import (
    dispatch_arrival_automation_event,
    generate_arrival_automation_events,
)
from hydra_arrivals.models import ArrivalAutomationEvent, ArrivalPlan
from hydra_arrivals.tests.test_arrivals import HydraArrivalTestCase
from hydra_coordination.models import ScopeGrant


@override_settings(
    HYDRA_ARRIVAL_REMINDER_MINUTES=(1440, 120),
    HYDRA_NOTIFICATION_MAX_ATTEMPTS=10,
)
class ArrivalAutomationTests(HydraArrivalTestCase):
    def setUp(self):
        super().setUp()
        self.grant_arrival_write()
        self.run_at = timezone.now()

    def make_escalator(self, *, username, location):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            is_new_employee=False,
        )
        wanted = (
            ("hydra_arrivals", "view_arrivalplan"),
            ("hydra_arrivals", "transition_arrivalplan"),
            ("hydra_arrivals", "receive_arrival_escalations"),
            ("hydra_coordination", "view_location"),
            ("hydra_people", "view_person"),
            ("recruitment", "view_candidate"),
        )
        user.user_permissions.add(
            *[
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
                for app_label, codename in wanted
            ]
        )
        ScopeGrant.objects.create(user=user, location=location)
        return user

    def test_reminder_thresholds_catch_up_without_duplicates(self):
        plan = self.make_plan(
            planned_at=self.run_at + timedelta(minutes=1440)
        )

        first = generate_arrival_automation_events(now=self.run_at, limit=10)
        repeated = generate_arrival_automation_events(now=self.run_at, limit=10)
        near = generate_arrival_automation_events(
            now=plan.planned_at - timedelta(minutes=120), limit=10
        )

        self.assertEqual(first, (1, 1))
        self.assertEqual(repeated, (1, 0))
        self.assertEqual(near, (1, 1))
        self.assertQuerySetEqual(
            plan.automation_events.order_by("threshold_minutes").values_list(
                "threshold_minutes", flat=True
            ),
            [120, 1440],
        )

    def test_overdue_escalation_is_location_scoped_and_does_not_mark_no_show(self):
        plan = self.make_plan(
            planned_at=self.run_at + timedelta(minutes=30)
        )
        inside = self.make_escalator(
            username="inside-arrival-escalator", location=self.location_a
        )
        outside = self.make_escalator(
            username="outside-arrival-escalator", location=self.location_b
        )

        generate_arrival_automation_events(
            now=self.run_at + timedelta(hours=1), limit=10
        )

        plan.refresh_from_db()
        recipients = set(
            plan.automation_events.filter(
                event_type=ArrivalAutomationEvent.EventType.OVERDUE
            ).values_list("recipient_id", flat=True)
        )
        self.assertEqual(plan.status, ArrivalPlan.Status.PLANNED)
        self.assertEqual(plan.status_history.count(), 1)
        self.assertIn(self.user.pk, recipients)
        self.assertIn(self.admin.pk, recipients)
        self.assertIn(inside.pk, recipients)
        self.assertNotIn(outside.pk, recipients)

    def test_terminal_or_rescheduled_plan_invalidates_stale_delivery(self):
        plan = self.make_plan(
            planned_at=self.run_at + timedelta(minutes=120)
        )
        generate_arrival_automation_events(now=self.run_at, limit=10)
        event = plan.automation_events.get()
        ArrivalPlan.objects.filter(pk=plan.pk).update(
            status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=self.run_at,
        )

        delivered = dispatch_arrival_automation_event(event.pk)

        event.refresh_from_db()
        self.assertTrue(delivered)
        self.assertEqual(
            event.notification_status,
            ArrivalAutomationEvent.NotificationStatus.NOT_APPLICABLE,
        )
        self.assertIsNone(event.notification_id)

    @override_settings(HYDRA_NOTIFICATION_MAX_ATTEMPTS=1)
    def test_failed_delivery_is_durable_and_operator_can_recover_one_event(self):
        plan = self.make_plan(
            planned_at=self.run_at + timedelta(minutes=120)
        )
        generate_arrival_automation_events(now=self.run_at, limit=10)
        event = plan.automation_events.get()

        with patch(
            "hydra_arrivals.automation.send_hydra_notification",
            side_effect=RuntimeError("sensitive backend details"),
        ):
            self.assertFalse(dispatch_arrival_automation_event(event.pk))

        call_command("dispatch_arrival_notifications", stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual(event.notification_attempts, 1)
        self.assertEqual(event.notification_error_code, "RuntimeError")
        self.assertNotIn("sensitive", event.notification_error_code)

        call_command(
            "dispatch_arrival_notifications",
            "--event-uuid",
            str(event.uuid),
            stdout=StringIO(),
        )
        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            ArrivalAutomationEvent.NotificationStatus.SENT,
        )
        self.assertEqual(event.notification_attempts, 2)
        self.assertEqual(ArrivalAutomationEvent.objects.count(), 1)

    def test_event_facts_are_append_only(self):
        plan = self.make_plan(
            planned_at=self.run_at + timedelta(minutes=120)
        )
        generate_arrival_automation_events(now=self.run_at, limit=10)
        event = plan.automation_events.get()
        event.threshold_minutes = 30

        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            ArrivalAutomationEvent.objects.filter(pk=event.pk).update(
                threshold_minutes=30
            )
        with self.assertRaises(TypeError):
            event.delete()

    def test_manual_command_rejects_future_run_time(self):
        with self.assertRaises(CommandError):
            call_command(
                "run_arrival_automation",
                "--at",
                "2999-01-01T00:00:00+00:00",
                stdout=StringIO(),
            )
