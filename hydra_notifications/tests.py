from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from notifications.signals import notify

from hydra_coordination.models import ScopeGrant
from hydra_legalization.models import LegalizationCase
from hydra_notifications.models import (
    HydraNotificationEmailDelivery,
    HydraNotificationEnvelope,
    HydraNotificationStateEvent,
    NotificationKind,
    NotificationSeverity,
    NotificationTargetKind,
)
from hydra_notifications.selectors import visible_envelopes_for_user
from hydra_notifications.services import (
    archive_all_visible,
    archive_envelope,
    dispatch_notification_email,
    dispatch_pending_notification_emails,
    mark_envelope_read,
    mark_envelope_unread,
    mark_all_visible_read,
    preference_for_user,
    restore_envelope,
    send_hydra_notification,
    update_preferences,
)
from hydra_ops.readiness import domain_integrity_results
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


class HydraNotificationTests(HydraRecruitmentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from hydra_legalization.models import (
            LegalizationProcedureStatus,
            LegalizationProcedureType,
        )

        for case_type in (
            LegalizationCase.CaseType.WORK_PERMIT,
            LegalizationCase.CaseType.VISA,
        ):
            if LegalizationProcedureType.objects.filter(
                company__isnull=True,
                case_type=case_type,
            ).exists():
                continue
            procedure = LegalizationProcedureType.objects.create(
                code=f"notification-test-{case_type.replace('_', '-')}",
                name=f"Notification test {case_type}",
                case_type=case_type,
                requires_authority=False,
                created_by=cls.admin,
                modified_by=cls.admin,
            )
            LegalizationProcedureStatus.objects.create(
                procedure=procedure,
                status=LegalizationCase.Status.DRAFT,
                label="Draft",
                sort_order=10,
                created_by=cls.admin,
                modified_by=cls.admin,
            )

    def setUp(self):
        super().setUp()
        self.grant(
            ("hydra_people", "view_person"),
            ("hydra_legalization", "view_legalizationcase"),
        )
        self.visible_case = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            responsible=self.admin,
            reference_number="NOTIFY-A",
        )
        self.hidden_case = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            **self.legalization_case_configuration(
                company=self.company_b,
                case_type=LegalizationCase.CaseType.VISA,
            ),
            responsible=self.admin,
            reference_number="NOTIFY-B",
        )

    def enable_email(self, *, minimum=NotificationSeverity.WARNING):
        preference = preference_for_user(user=self.user)
        return update_preferences(
            actor=self.user,
            email_enabled=True,
            email_min_severity=minimum,
            browser_sound_enabled=False,
            expected_version=preference.version,
        )

    def send(self, **overrides):
        data = {
            "actor": self.admin,
            "recipient": self.user,
            "kind": NotificationKind.LEGALIZATION_DEADLINE,
            "target_kind": NotificationTargetKind.LEGALIZATION_CASE,
            "target_uuid": self.visible_case.uuid,
            "redirect_path": self.visible_case.get_absolute_url(),
            "idempotency_key": "notification-test:visible",
        }
        data.update(overrides)
        notification = send_hydra_notification(**data)
        return notification.hydra_envelope

    def test_managed_notification_is_scoped_idempotent_and_pii_free(self):
        envelope = self.send()
        same = self.send()

        self.assertEqual(envelope.pk, same.pk)
        self.assertEqual(envelope.company, self.company_a)
        self.assertEqual(envelope.person, self.person_a)
        self.assertEqual(envelope.version, 1)
        self.assertEqual(envelope.state_events.get().action, "created")
        self.assertIn(envelope, visible_envelopes_for_user(user=self.user))
        rendered = f"{envelope.notification.verb} {envelope.notification.data}"
        self.assertNotIn(self.person_a.hydra_id, rendered)
        self.assertNotIn(self.person_a.passport_name, rendered)
        self.assertNotIn(self.visible_case.reference_number, rendered)
        self.assertEqual(
            envelope.notification.data["redirect"],
            reverse("hydra-notification-center"),
        )

    def test_invalid_kind_target_redirect_and_idempotency_collision_write_nothing_extra(self):
        with self.assertRaises(ValidationError):
            self.send(
                target_kind=NotificationTargetKind.ARRIVAL_PLAN,
                target_uuid=self.visible_case.uuid,
            )
        with self.assertRaises(ValidationError):
            self.send(redirect_path="https://evil.example.test/steal")
        with self.assertRaises(PermissionDenied):
            self.send(
                target_uuid=self.hidden_case.uuid,
                redirect_path=self.hidden_case.get_absolute_url(),
            )
        self.assertFalse(HydraNotificationEnvelope._base_manager.exists())

        self.send()
        with self.assertRaises(ValidationError):
            self.send(
                kind=NotificationKind.LEGALIZATION_OVERDUE,
            )
        self.assertEqual(HydraNotificationEnvelope._base_manager.count(), 1)

    def test_read_unread_archive_restore_are_locked_mirrored_and_append_only(self):
        envelope = self.send()
        mark_envelope_read(
            actor=self.user,
            envelope_uuid=envelope.uuid,
            expected_version=1,
        )
        envelope.refresh_from_db()
        envelope.notification.refresh_from_db()
        self.assertIsNotNone(envelope.read_at)
        self.assertFalse(envelope.notification.unread)

        with self.assertRaises(ValidationError):
            mark_envelope_unread(
                actor=self.user,
                envelope_uuid=envelope.uuid,
                expected_version=1,
            )
        mark_envelope_unread(
            actor=self.user,
            envelope_uuid=envelope.uuid,
            expected_version=2,
        )
        archive_envelope(
            actor=self.user,
            envelope_uuid=envelope.uuid,
            expected_version=3,
        )
        restore_envelope(
            actor=self.user,
            envelope_uuid=envelope.uuid,
            expected_version=4,
        )
        envelope.refresh_from_db()
        envelope.notification.refresh_from_db()
        self.assertEqual(envelope.version, 5)
        self.assertIsNone(envelope.archived_at)
        self.assertFalse(envelope.notification.deleted)
        self.assertEqual(
            list(envelope.state_events.values_list("sequence", "action")),
            [
                (1, "created"),
                (2, "read"),
                (3, "unread"),
                (4, "archived"),
                (5, "restored"),
            ],
        )
        event = envelope.state_events.first()
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            HydraNotificationStateEvent.objects.filter(pk=event.pk).delete()
        envelope.read_at = timezone.now()
        with self.assertRaises(TypeError):
            envelope.save()
        with self.assertRaises(TypeError):
            envelope.delete()
        with self.assertRaises(ProtectedError):
            envelope.notification.delete()

    def test_bulk_state_actions_page_through_bounded_batches(self):
        envelopes = [
            self.send(idempotency_key=f"notification-test:batch:{index}")
            for index in range(3)
        ]
        with patch("hydra_notifications.services.STATE_CHANGE_BATCH_SIZE", 2):
            self.assertEqual(mark_all_visible_read(actor=self.user), 3)
            self.assertEqual(archive_all_visible(actor=self.user), 3)
        self.assertEqual(
            HydraNotificationEnvelope._base_manager.filter(
                pk__in=[envelope.pk for envelope in envelopes],
                read_at__isnull=False,
                archived_at__isnull=False,
            ).count(),
            3,
        )

    def test_center_and_legacy_mutations_enforce_recipient_post_and_current_scope(self):
        own = self.send()
        other_notification = send_hydra_notification(
            actor=self.admin,
            recipient=self.admin,
            kind=NotificationKind.ORGANIZATION_SCOPE_REVOKED,
            target_kind=NotificationTargetKind.ORGANIZATION,
            redirect_path=reverse("hydra-organization"),
            idempotency_key="notification-test:other",
        )
        self.login()
        own_mark_url = reverse("mark-as-read-notification", args=(own.notification_id,))
        self.assertEqual(self.client.get(own_mark_url).status_code, 405)
        own.refresh_from_db()
        self.assertIsNone(own.read_at)
        denied = self.client.post(
            reverse("mark-as-read-notification", args=(other_notification.pk,))
        )
        self.assertEqual(denied.status_code, 404)

        center = self.client.get(reverse("hydra-notification-center"))
        self.assertEqual(center.status_code, 200)
        self.assertContains(center, own.notification.verb)
        self.assertNotContains(center, other_notification.verb)

        ScopeGrant.objects.filter(user=self.user).update(is_active=False)
        denied_scope = self.client.post(
            reverse("hydra-notification-read", args=(own.uuid,)),
            {"version": own.version},
        )
        self.assertEqual(denied_scope.status_code, 404)
        own.refresh_from_db()
        self.assertIsNone(own.read_at)

    def test_preference_view_maps_version_and_rejects_stale_submission(self):
        self.login()
        url = reverse("hydra-notification-preferences")
        response = self.client.post(
            url,
            {
                "email_enabled": "on",
                "email_min_severity": NotificationSeverity.INFO,
                "browser_sound_enabled": "on",
                "version": 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        preference = preference_for_user(user=self.user)
        self.assertTrue(preference.email_enabled)
        self.assertTrue(preference.browser_sound_enabled)
        self.assertEqual(preference.email_min_severity, NotificationSeverity.INFO)
        self.assertEqual(preference.version, 2)

        stale = self.client.post(
            url,
            {
                "email_min_severity": NotificationSeverity.ERROR,
                "version": 1,
            },
        )
        self.assertEqual(stale.status_code, 302)
        preference.refresh_from_db()
        self.assertTrue(preference.email_enabled)
        self.assertTrue(preference.browser_sound_enabled)
        self.assertEqual(preference.email_min_severity, NotificationSeverity.INFO)
        self.assertEqual(preference.version, 2)

    def test_legacy_notify_signal_is_wrapped_without_email_delivery(self):
        responses = notify.send(
            self.admin,
            recipient=self.user,
            verb="A legacy Hydra notification.",
            redirect="#",
        )
        notifications = [
            notification
            for _receiver, response in responses
            if isinstance(response, list)
            for notification in response
        ]
        self.assertEqual(len(notifications), 1)
        envelope = notifications[0].hydra_envelope
        self.assertEqual(envelope.kind, NotificationKind.LEGACY)
        self.assertFalse(
            HydraNotificationEmailDelivery._base_manager.filter(
                envelope=envelope
            ).exists()
        )

    @override_settings(
        HYDRA_NOTIFICATION_BASE_URL="https://hydra.example.test/",
        DEFAULT_FROM_EMAIL="hydra@example.test",
    )
    def test_email_hook_sends_only_generic_content_and_rechecks_scope(self):
        self.enable_email(minimum=NotificationSeverity.INFO)
        envelope = self.send()
        delivery = envelope.email_delivery
        self.assertEqual(delivery.status, delivery.Status.PENDING)

        with patch("hydra_notifications.services.EmailMessage") as email_message:
            email_message.return_value.send.return_value = 1
            self.assertTrue(dispatch_notification_email(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, delivery.Status.SENT)
        kwargs = email_message.call_args.kwargs
        body = kwargs["body"]
        self.assertNotIn(self.person_a.hydra_id, body)
        self.assertNotIn(self.person_a.passport_name, body)
        self.assertNotIn(self.visible_case.reference_number, body)
        self.assertIn(reverse("hydra-notification-center"), body)

        second = self.send(idempotency_key="notification-test:scope-loss")
        third = self.send(idempotency_key="notification-test:scope-loss-batch")
        ScopeGrant.objects.filter(user=self.user).update(is_active=False)
        with patch("hydra_notifications.services.EmailMessage") as not_called:
            self.assertTrue(dispatch_notification_email(second.email_delivery.pk))
            not_called.assert_not_called()
        second.email_delivery.refresh_from_db()
        self.assertEqual(
            second.email_delivery.status,
            HydraNotificationEmailDelivery.Status.NOT_APPLICABLE,
        )
        self.assertEqual(
            second.email_delivery.error_code,
            "ScopeNoLongerVisible",
        )
        result = dispatch_pending_notification_emails(limit=10)
        third.email_delivery.refresh_from_db()
        self.assertEqual(result.selected, 1)
        self.assertEqual(result.sent, 0)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.not_applicable, 1)
        self.assertEqual(
            third.email_delivery.status,
            HydraNotificationEmailDelivery.Status.NOT_APPLICABLE,
        )

    @override_settings(
        HYDRA_NOTIFICATION_BASE_URL="https://hydra.example.test/",
        DEFAULT_FROM_EMAIL="hydra@example.test",
        HYDRA_NOTIFICATION_MAX_ATTEMPTS=2,
        HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS=5,
        HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS=30,
    )
    def test_email_failure_is_minimal_bounded_and_retryable(self):
        self.enable_email(minimum=NotificationSeverity.INFO)
        delivery = self.send().email_delivery
        now = timezone.now()
        with patch(
            "hydra_notifications.services.EmailMessage.send",
            side_effect=RuntimeError("smtp credentials and private details"),
        ):
            self.assertFalse(dispatch_notification_email(delivery.pk, now=now))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, delivery.Status.FAILED)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.error_code, "RuntimeError")
        self.assertNotIn("private", delivery.error_code)
        with patch(
            "hydra_notifications.services.EmailMessage.send",
            return_value=1,
        ):
            self.assertTrue(
                dispatch_notification_email(
                    delivery.pk,
                    now=delivery.next_attempt_at + timedelta(seconds=1),
                )
            )
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, delivery.Status.SENT)
        self.assertEqual(delivery.attempts, 2)

    def test_readiness_covers_notification_state_target_payload_and_delivery(self):
        self.send()
        results = {result.name: result for result in domain_integrity_results()}
        for name in (
            "notification_read_state",
            "notification_targets",
            "notification_payloads",
            "notification_email_deliveries",
        ):
            self.assertTrue(results[name].ok, results[name].detail)
