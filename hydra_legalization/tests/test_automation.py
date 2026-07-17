from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from hydra_coordination.models import ScopeGrant
from hydra_legalization.automation import (
    dispatch_legalization_automation_event,
    generate_legalization_automation_events,
)
from hydra_legalization.models import (
    LegalizationAutomationEvent,
    LegalizationCase,
    LegalizationStatusHistory,
)
from hydra_legalization.tests.test_legalization import HydraLegalizationTestCase


@override_settings(
    HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS=(30, 7, 1),
    HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS=(90, 30, 7),
    HYDRA_NOTIFICATION_MAX_ATTEMPTS=10,
)
class LegalizationAutomationTests(HydraLegalizationTestCase):
    run_date = date.today()

    def setUp(self):
        super().setUp()
        self.grant_legalization_write()

    def approved_case(self, *, valid_until):
        case = self.create_case(
            valid_from=valid_until - timedelta(days=365),
            valid_until=valid_until,
        )
        LegalizationCase.objects.filter(pk=case.pk).update(
            status=LegalizationCase.Status.APPROVED
        )
        case.refresh_from_db()
        return case

    def make_escalator(self, *, username, team):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            is_new_employee=False,
        )
        permissions = Permission.objects.filter(
            content_type__app_label__in=("hydra_legalization", "hydra_people"),
            codename__in=(
                "view_legalizationcase",
                "view_person",
                "receive_legalization_escalations",
            ),
        )
        user.user_permissions.add(*permissions)
        ScopeGrant.objects.create(user=user, team=team)
        return user

    def test_deadline_thresholds_catch_up_without_duplicate_events(self):
        case = self.create_case(deadline=self.run_date + timedelta(days=7))

        first = generate_legalization_automation_events(
            today=self.run_date, limit=10
        )
        repeated = generate_legalization_automation_events(
            today=self.run_date, limit=10
        )
        final = generate_legalization_automation_events(
            today=self.run_date + timedelta(days=6), limit=10
        )

        self.assertEqual(first, (1, 1, 0))
        self.assertEqual(repeated, (1, 0, 0))
        self.assertEqual(final, (1, 1, 0))
        self.assertQuerySetEqual(
            case.automation_events.order_by("threshold_days").values_list(
                "threshold_days", flat=True
            ),
            [1, 7],
        )

    def test_overdue_escalation_is_permission_and_person_scoped(self):
        case = self.create_case(deadline=self.run_date - timedelta(days=1))
        inside = self.make_escalator(username="inside-escalator", team=self.team_a)
        outside = self.make_escalator(username="outside-escalator", team=self.team_b)

        generate_legalization_automation_events(today=self.run_date, limit=10)

        recipients = set(
            case.automation_events.filter(
                event_type=LegalizationAutomationEvent.EventType.DEADLINE_OVERDUE
            ).values_list("recipient_id", flat=True)
        )
        self.assertIn(self.user.pk, recipients)
        self.assertIn(self.admin.pk, recipients)
        self.assertIn(inside.pk, recipients)
        self.assertNotIn(outside.pk, recipients)

    def test_valid_until_is_inclusive_and_expiry_is_system_audited(self):
        case = self.approved_case(valid_until=self.run_date)

        on_last_day = generate_legalization_automation_events(
            today=self.run_date, limit=10
        )
        after_last_day = generate_legalization_automation_events(
            today=self.run_date + timedelta(days=1), limit=10
        )
        repeated = generate_legalization_automation_events(
            today=self.run_date + timedelta(days=1), limit=10
        )

        case.refresh_from_db()
        self.assertEqual(on_last_day[2], 0)
        self.assertEqual(after_last_day[2], 1)
        self.assertEqual(repeated, (0, 0, 0))
        self.assertEqual(case.status, LegalizationCase.Status.EXPIRED)
        history = case.status_history.filter(
            to_status=LegalizationCase.Status.EXPIRED
        ).get()
        self.assertEqual(history.source, LegalizationStatusHistory.Source.SYSTEM)
        self.assertIsNone(history.actor)
        self.assertEqual(
            case.automation_events.filter(
                event_type=LegalizationAutomationEvent.EventType.AUTO_EXPIRED
            ).count(),
            2,
        )

    def test_delivery_rechecks_scope_and_becomes_not_applicable(self):
        case = self.create_case(deadline=self.run_date + timedelta(days=7))
        generate_legalization_automation_events(today=self.run_date, limit=10)
        event = case.automation_events.get()
        ScopeGrant.objects.filter(user=self.user).update(is_active=False)

        delivered = dispatch_legalization_automation_event(event.pk)

        event.refresh_from_db()
        self.assertTrue(delivered)
        self.assertEqual(
            event.notification_status,
            LegalizationAutomationEvent.NotificationStatus.NOT_APPLICABLE,
        )
        self.assertIsNone(event.notification_id)

    def test_reminder_follows_current_responsibility_before_delivery(self):
        case = self.create_case(deadline=self.run_date + timedelta(days=7))
        generate_legalization_automation_events(today=self.run_date, limit=10)
        old_event = case.automation_events.get()
        replacement = self.make_escalator(
            username="replacement-responsible", team=self.team_a
        )
        LegalizationCase.objects.filter(pk=case.pk).update(responsible=replacement)

        dispatch_legalization_automation_event(old_event.pk)
        generate_legalization_automation_events(today=self.run_date, limit=10)

        old_event.refresh_from_db()
        self.assertEqual(
            old_event.notification_status,
            LegalizationAutomationEvent.NotificationStatus.NOT_APPLICABLE,
        )
        self.assertTrue(
            case.automation_events.filter(recipient=replacement).exists()
        )

    @override_settings(HYDRA_NOTIFICATION_MAX_ATTEMPTS=1)
    def test_failed_delivery_is_durable_and_operator_retry_is_idempotent(self):
        case = self.create_case(deadline=self.run_date + timedelta(days=7))
        generate_legalization_automation_events(today=self.run_date, limit=10)
        event = case.automation_events.get()

        with patch(
            "hydra_legalization.automation.send_hydra_notification",
            side_effect=RuntimeError("sensitive backend details"),
        ):
            self.assertFalse(dispatch_legalization_automation_event(event.pk))

        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            LegalizationAutomationEvent.NotificationStatus.FAILED,
        )
        self.assertEqual(event.notification_attempts, 1)
        self.assertEqual(event.notification_error_code, "RuntimeError")
        self.assertNotIn("sensitive", event.notification_error_code)

        call_command("dispatch_legalization_notifications", stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual(event.notification_attempts, 1)

        call_command(
            "dispatch_legalization_notifications",
            "--event-uuid",
            str(event.uuid),
            stdout=StringIO(),
        )
        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            LegalizationAutomationEvent.NotificationStatus.SENT,
        )
        self.assertEqual(event.notification_attempts, 2)
        self.assertEqual(LegalizationAutomationEvent.objects.count(), 1)

    def test_manual_command_rejects_future_run_date(self):
        with self.assertRaises(CommandError):
            call_command(
                "run_legalization_automation",
                "--date",
                "2999-01-01",
                stdout=StringIO(),
            )

    def test_event_facts_are_append_only(self):
        case = self.create_case(deadline=self.run_date + timedelta(days=7))
        generate_legalization_automation_events(today=self.run_date, limit=10)
        event = case.automation_events.get()
        event.due_date += timedelta(days=1)

        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            LegalizationAutomationEvent.objects.filter(pk=event.pk).update(
                due_date=self.run_date
            )
        with self.assertRaises(TypeError):
            event.delete()
        with self.assertRaises(TypeError):
            LegalizationAutomationEvent.objects.filter(pk=event.pk).delete()
