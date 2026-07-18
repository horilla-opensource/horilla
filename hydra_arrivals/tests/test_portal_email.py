import json
import tempfile
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import (
    OnboardingPortalDelivery,
    OnboardingPortalDeliveryEvent,
)
from base.backends import ConfiguredEmailBackend
from base.models import DynamicEmailConfiguration, EmailLog, HydraMailTemplate
from hydra_arrivals.portal_email import (
    PORTAL_EMAIL_QUEUE_PERMISSIONS,
    dispatch_portal_emails,
    prepare_generated_portal_attachment,
    prepare_uploaded_portal_attachments,
    purge_portal_email_payloads,
    queue_onboarding_portal_email,
    recover_expired_portal_email_leases,
    retry_portal_delivery,
)
from hydra_arrivals.tests.test_arrivals import HydraArrivalTestCase
from hydra_documents.scanning import ScanResult, ScannerUnavailable
from hydra_people.recruitment_workflow import transition_candidate
from onboarding.models import CandidateStage, CandidateTask, OnboardingStage, OnboardingTask
from recruitment.models import Candidate, Stage


@override_settings(
    HYDRA_ONBOARDING_PORTAL_BASE_URL="https://onboarding.example.test/",
    HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=3,
    HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS=60,
    HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS=3600,
    HYDRA_PORTAL_EMAIL_LEASE_SECONDS=120,
    HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS=72,
    HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS=8,
    HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES=10 * 1024 * 1024,
    HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES=25 * 1024 * 1024,
    EMAIL_HOST_USER="noreply@example.test",
    EMAIL_HOST="smtp.example.test",
    EMAIL_HOST_PASSWORD="test-smtp-password",
    EMAIL_PORT=587,
    DEFAULT_FROM_EMAIL="noreply@example.test",
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
    EMAIL_FAIL_SILENTLY=False,
    EMAIL_TIMEOUT=30,
)
class PortalEmailOutboxTests(HydraArrivalTestCase):
    def setUp(self):
        super().setUp()
        self.storage_dir = tempfile.TemporaryDirectory()
        self.storage_override = override_settings(
            HYDRA_PORTAL_EMAIL_MEDIA_ROOT=self.storage_dir.name
        )
        self.storage_override.enable()
        self.addCleanup(self.storage_override.disable)
        self.addCleanup(self.storage_dir.cleanup)
        self.candidate = Candidate._base_manager.get(pk=type(self).candidate_a.pk)
        self.hired_stage = Stage._base_manager.create(
            recruitment_id=self.recruitment_a,
            stage="Portal hired",
            stage_type="hired",
            sequence=100,
        )
        self.candidate, _transition = transition_candidate(
            candidate=self.candidate,
            target_stage=self.hired_stage,
            actor=self.admin,
            reason="Portal email test setup.",
            joining_date=date(2026, 8, 3),
        )
        self.onboarding_stage = OnboardingStage._base_manager.get(
            recruitment_id=self.recruitment_a
        )
        self.onboarding_task = OnboardingTask.objects.create(
            task_title="Portal task",
            stage_id=self.onboarding_stage,
        )

    def queue(self, *, actor=None, attachments=()):
        return queue_onboarding_portal_email(
            candidate_id=self.candidate.pk,
            actor=actor or self.admin,
            attachments=attachments,
        )

    def grant_queue_permissions(self):
        self.grant(
            *(tuple(permission.split(".", 1)) for permission in PORTAL_EMAIL_QUEUE_PERMISSIONS)
        )

    def test_lease_recovery_rejects_unbounded_batch_size(self):
        for limit in (0, 1001):
            with self.subTest(limit=limit):
                with self.assertRaises(ValidationError):
                    recover_expired_portal_email_leases(limit=limit)

    def test_queue_is_transactional_idempotent_and_does_not_start_onboarding(self):
        first, first_created = self.queue()
        second, second_created = self.queue()

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OnboardingPortalDelivery.objects.count(), 1)
        self.candidate.refresh_from_db()
        self.assertFalse(self.candidate.start_onboard)
        self.assertFalse(CandidateStage.objects.filter(candidate_id=self.candidate).exists())
        self.assertEqual(first.sender, "noreply@example.test")
        self.assertEqual(first.reply_to, self.admin_employee.email)
        self.assertIn(
            "https://onboarding.example.test/onboarding/user-creation/",
            first.body_html,
        )
        self.assertEqual(
            list(first.events.values_list("event_type", flat=True)),
            [OnboardingPortalDeliveryEvent.EventType.QUEUED],
        )

    def test_delivery_events_are_append_only(self):
        delivery, _created = self.queue()
        event = delivery.events.get()

        event.error_code = "changed"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            delivery.events.update(error_code="changed")
        with self.assertRaises(TypeError):
            delivery.events.all().delete()

    def test_database_constraint_allows_only_one_active_delivery_per_candidate(self):
        delivery, _created = self.queue()

        with self.assertRaises(IntegrityError), transaction.atomic():
            OnboardingPortalDelivery.objects.create(
                candidate=delivery.candidate,
                portal=delivery.portal,
                requested_by=self.admin,
                idempotency_key="f" * 64,
                portal_token="another-token",
                recipient=delivery.recipient,
                sender=delivery.sender,
                reply_to=delivery.reply_to,
                subject="Duplicate",
                body_html="duplicate",
                payload_sha256="e" * 64,
            )

    def test_mismatched_active_delivery_is_reported_without_rotating_again(self):
        delivery, _created = self.queue()
        delivery.portal.token = "unexpected-current-token"
        delivery.portal.save(update_fields=("token",))

        with self.assertRaisesMessage(ValidationError, "integrity review"):
            self.queue()

        self.assertEqual(OnboardingPortalDelivery.objects.count(), 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.PENDING)

    @override_settings(HYDRA_ENVIRONMENT="staging")
    def test_unsafe_company_email_configuration_fails_before_queue_commit(self):
        DynamicEmailConfiguration.objects.create(
            host="smtp.example.test",
            port=587,
            from_email="noreply@example.test",
            username="hydra",
            password="test-password",
            use_tls=True,
            use_ssl=False,
            fail_silently=True,
            timeout=30,
            company_id=self.company_a,
        )

        with self.assertRaises(ValidationError):
            self.queue()

        self.assertFalse(OnboardingPortalDelivery.objects.exists())

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_successful_delivery_starts_onboarding_and_purges_payload(self, send):
        attachment = prepare_generated_portal_attachment(
            filename="terms.pdf",
            content=b"%PDF-1.4\nportal terms\n%%EOF",
        )
        delivery, _created = self.queue(attachments=(attachment,))
        portal_token = delivery.portal_token
        storage_name = delivery.attachments.get().file.name

        result = dispatch_portal_emails(limit=10)

        self.assertEqual((result.selected, result.sent, result.failed), (1, 1, 0))
        send.assert_called_once_with()
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.SENT)
        self.assertIsNotNone(delivery.sent_at)
        self.assertIsNotNone(delivery.onboarding_started_at)
        self.assertIsNotNone(delivery.payload_purged_at)
        self.assertEqual(
            (
                delivery.recipient,
                delivery.sender,
                delivery.reply_to,
                delivery.subject,
                delivery.body_html,
            ),
            ("", "", "", "", ""),
        )
        self.assertFalse(delivery.attachments.get().file)
        self.assertFalse(delivery.attachments.get().file.storage.exists(storage_name))
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.start_onboard)
        self.assertTrue(CandidateStage.objects.filter(candidate_id=self.candidate).exists())
        self.assertTrue(CandidateTask.objects.filter(candidate_id=self.candidate).exists())
        delivery.portal.refresh_from_db()
        self.assertEqual(delivery.portal.token, portal_token)
        self.assertFalse(delivery.portal.used)
        self.assertEqual(
            list(delivery.events.values_list("event_type", flat=True)),
            ["queued", "claimed", "sent", "onboarding", "purged"],
        )

    @patch(
        "hydra_arrivals.portal_email.EmailMessage.send",
        side_effect=RuntimeError("secret SMTP detail"),
    )
    def test_smtp_failure_schedules_backoff_without_persisting_secret(self, send):
        delivery, _created = self.queue()
        now = timezone.now()

        result = dispatch_portal_emails(limit=1, now=now)

        self.assertEqual((result.failed, result.dead), (1, 0))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.RETRY)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.last_error_code, "RuntimeError")
        self.assertGreaterEqual(delivery.next_attempt_at, now + timedelta(seconds=60))
        self.assertNotIn("secret", delivery.last_error_code)
        retry_event = delivery.events.get(event_type="retry")
        self.assertEqual(retry_event.error_code, "RuntimeError")
        self.assertNotIn(self.candidate.email, json.dumps(retry_event.snapshot))
        self.candidate.refresh_from_db()
        self.assertFalse(self.candidate.start_onboard)

    @override_settings(HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=2)
    @patch(
        "hydra_arrivals.portal_email.EmailMessage.send",
        side_effect=RuntimeError("mail unavailable"),
    )
    def test_retry_exhaustion_moves_delivery_to_dead(self, send):
        delivery, _created = self.queue()
        first_at = timezone.now()

        dispatch_portal_emails(limit=1, now=first_at)
        result = dispatch_portal_emails(
            limit=1,
            now=first_at + timedelta(seconds=61),
        )

        self.assertEqual((result.failed, result.dead), (1, 1))
        self.assertEqual(send.call_count, 2)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.DEAD)
        self.assertEqual(delivery.attempts, 2)
        self.assertTrue(delivery.events.filter(event_type="dead").exists())

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_onboarding_failure_is_reconciled_without_resending_email(self, send):
        stage = CandidateStage.objects.create(
            candidate_id=self.candidate,
            onboarding_stage_id=self.onboarding_stage,
            sequence=0,
        )
        first = CandidateTask.objects.create(
            candidate_id=self.candidate,
            stage_id=self.onboarding_stage,
            onboarding_task_id=self.onboarding_task,
        )
        CandidateTask.objects.create(
            candidate_id=self.candidate,
            stage_id=self.onboarding_stage,
            onboarding_task_id=self.onboarding_task,
        )
        delivery, _created = self.queue()

        first_cycle = dispatch_portal_emails(limit=10)

        self.assertEqual(first_cycle.sent, 1)
        self.assertEqual(first_cycle.onboarding_failed, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.SENT)
        self.assertEqual(delivery.onboarding_error_code, "ValidationError")
        self.assertIsNone(delivery.onboarding_started_at)
        CandidateTask.objects.exclude(pk=first.pk).filter(
            candidate_id=self.candidate,
            onboarding_task_id=self.onboarding_task,
        ).delete()

        second_cycle = dispatch_portal_emails(limit=10)

        self.assertEqual(second_cycle.selected, 0)
        self.assertEqual(second_cycle.onboarding_started, 1)
        self.assertEqual(send.call_count, 1)
        delivery.refresh_from_db()
        self.assertIsNotNone(delivery.onboarding_started_at)
        self.assertEqual(delivery.onboarding_error_code, "")

    @override_settings(HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=1)
    @patch(
        "hydra_arrivals.portal_email.EmailMessage.send",
        side_effect=RuntimeError("mail unavailable"),
    )
    def test_authorized_manual_retry_reuses_same_token_and_preserves_audit(self, send):
        delivery, _created = self.queue()
        token = delivery.portal_token
        dispatch_portal_emails(limit=1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.DEAD)

        retried = retry_portal_delivery(delivery_uuid=delivery.uuid, actor=self.admin)

        self.assertEqual(retried.status, OnboardingPortalDelivery.Status.PENDING)
        self.assertEqual(retried.attempts, 0)
        self.assertEqual(retried.portal_token, token)
        self.assertTrue(retried.events.filter(event_type="manual_retry").exists())

    @override_settings(HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=1)
    @patch(
        "hydra_arrivals.portal_email.EmailMessage.send",
        side_effect=RuntimeError("mail unavailable"),
    )
    def test_expired_dead_payload_is_purged_and_token_is_revoked(self, send):
        delivery, _created = self.queue()
        original_token = delivery.portal_token
        failed_at = timezone.now()
        dispatch_portal_emails(limit=1, now=failed_at)

        purged = purge_portal_email_payloads(
            now=failed_at + timedelta(hours=73),
            limit=1,
        )

        self.assertEqual(purged, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.CANCELLED)
        self.assertIsNotNone(delivery.payload_purged_at)
        delivery.portal.refresh_from_db()
        self.assertTrue(delivery.portal.used)
        self.assertNotEqual(delivery.portal.token, original_token)

    def test_scope_is_enforced_before_queueing_or_retrying(self):
        self.grant_queue_permissions()
        candidate_b = Candidate._base_manager.get(pk=type(self).candidate_b.pk)
        hired_stage_b = Stage._base_manager.create(
            recruitment_id=self.recruitment_b,
            stage="Portal hired B",
            stage_type="hired",
            sequence=100,
        )
        candidate_b, _transition = transition_candidate(
            candidate=candidate_b,
            target_stage=hired_stage_b,
            actor=self.admin,
            reason="Out-of-scope portal-email test setup.",
            joining_date=date(2026, 8, 3),
        )

        with self.assertRaises(PermissionDenied):
            queue_onboarding_portal_email(
                candidate_id=candidate_b.pk,
                actor=self.user,
            )

        delivery, _created = queue_onboarding_portal_email(
            candidate_id=candidate_b.pk,
            actor=self.admin,
        )
        self.grant(("hydra_arrivals", "retry_onboardingportaldelivery"))
        with self.assertRaises(PermissionDenied):
            retry_portal_delivery(delivery_uuid=delivery.uuid, actor=self.user)

    def test_onboarding_candidate_list_is_scoped_and_shows_delivery_status(self):
        delivery, _created = self.queue()
        candidate_b = Candidate._base_manager.get(pk=type(self).candidate_b.pk)
        candidate_b.hired = True
        candidate_b.save(update_fields=("hired",))
        self.grant(
            ("onboarding", "view_onboardingcandidate"),
            ("recruitment", "view_candidate"),
            ("hydra_people", "view_person"),
        )
        self.login()

        response = self.client.get(reverse("candidates-view"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.candidate.name)
        self.assertContains(response, delivery.get_status_display())
        self.assertNotContains(response, candidate_b.name)

    def test_other_company_attachment_template_is_rejected(self):
        foreign_template = HydraMailTemplate._base_manager.create(
            title="Foreign portal attachment",
            body="Foreign company content",
            company_id=self.company_b,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("email-send"),
            {
                "ids": [str(self.candidate.pk)],
                "template_attachment_ids": [str(foreign_template.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(OnboardingPortalDelivery.objects.exists())

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_stale_lease_is_recovered_and_same_payload_is_delivered(self, send):
        delivery, _created = self.queue()
        now = timezone.now()
        delivery.status = OnboardingPortalDelivery.Status.SENDING
        delivery.attempts = 1
        delivery.last_attempt_at = now - timedelta(minutes=5)
        delivery.lease_token = uuid4()
        delivery.lease_expires_at = now - timedelta(seconds=1)
        delivery.save(
            update_fields=(
                "status",
                "attempts",
                "last_attempt_at",
                "lease_token",
                "lease_expires_at",
            )
        )

        result = dispatch_portal_emails(limit=1, now=now)

        self.assertEqual(result.leases_recovered, 1)
        self.assertEqual(result.sent, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.SENT)
        self.assertEqual(delivery.attempts, 2)

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_recipient_change_cancels_without_sending(self, send):
        delivery, _created = self.queue()
        portal_token = delivery.portal_token
        self.candidate.email = "new-address@example.test"
        self.candidate.save(update_fields=("email",))

        result = dispatch_portal_emails(limit=1)

        send.assert_not_called()
        self.assertEqual(result.cancelled, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.CANCELLED)
        self.assertEqual(delivery.last_error_code, "RecipientChanged")
        self.assertIsNotNone(delivery.payload_purged_at)
        delivery.portal.refresh_from_db()
        self.assertNotEqual(delivery.portal.token, portal_token)
        self.assertTrue(delivery.portal.used)

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_tampered_attachment_is_never_sent(self, send):
        prepared = prepare_generated_portal_attachment(
            filename="terms.pdf",
            content=b"%PDF-1.4\noriginal\n%%EOF",
        )
        delivery, _created = self.queue(attachments=(prepared,))
        attachment = delivery.attachments.get()
        with attachment.file.storage.open(attachment.file.name, "wb") as handle:
            handle.write(b"%PDF-1.4\ntampered\n%%EOF")

        result = dispatch_portal_emails(limit=1)

        send.assert_not_called()
        self.assertEqual(result.failed, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.RETRY)
        self.assertEqual(delivery.last_error_code, "PortalAttachmentIntegrityError")

    @patch(
        "hydra_arrivals.portal_email.scan_file",
        return_value=ScanResult(clean=True, scanner="clamd", result="clean"),
    )
    def test_uploaded_attachment_is_type_verified_and_scanned(self, scan):
        upload = SimpleUploadedFile(
            "terms.pdf",
            b"%PDF-1.4\nverified\n%%EOF",
            content_type="application/octet-stream",
        )

        prepared = prepare_uploaded_portal_attachments((upload,))

        self.assertEqual(prepared[0].content_type, "application/pdf")
        scan.assert_called_once_with(upload)

    @patch(
        "hydra_arrivals.portal_email.scan_file",
        side_effect=ScannerUnavailable("offline"),
    )
    def test_attachment_upload_fails_closed_when_scanner_is_unavailable(self, scan):
        upload = SimpleUploadedFile(
            "terms.pdf",
            b"%PDF-1.4\nverified\n%%EOF",
            content_type="application/pdf",
        )

        with self.assertRaises(ValidationError):
            prepare_uploaded_portal_attachments((upload,))

        scan.assert_called_once_with(upload)

    @patch("django.core.mail.backends.smtp.EmailBackend.send_messages", return_value=1)
    def test_legacy_mail_log_redacts_sensitive_portal_payload(self, send):
        backend = ConfiguredEmailBackend(fail_silently=False)
        message = EmailMessage(
            subject=f"Hello {self.candidate.name}",
            body="secret-portal-token",
            to=[self.candidate.email],
            connection=backend,
        )
        message.hydra_sensitive = True
        message.hydra_audit_reference = str(uuid4())

        result = backend.send_messages([message])

        self.assertEqual(result, 1)
        log = EmailLog.objects.latest("pk")
        self.assertEqual(log.subject, "Sensitive Hydra email")
        self.assertEqual(log.from_email, "redacted@invalid.local")
        self.assertEqual(log.to, "redacted@invalid.local")
        self.assertNotIn("secret-portal-token", log.body)
        self.assertNotIn(self.candidate.email, log.body)
        self.assertIn("Hydra reference", log.body)
