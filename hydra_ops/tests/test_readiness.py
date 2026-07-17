import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from horilla.scheduling import should_start_schedulers
from hydra_ops.readiness import ReadinessResult, configuration_results, readiness_payload
from hydra_ops.middleware import DisableDatabaseInitializationMiddleware


class ConfigurationReadinessTests(SimpleTestCase):
    @override_settings(
        HYDRA_ENVIRONMENT="staging",
        DEBUG=False,
        SECRET_KEY="x" * 64,
        ALLOWED_HOSTS=["staging.example.test"],
        CSRF_TRUSTED_ORIGINS=["https://staging.example.test"],
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}},
        HYDRA_DISABLE_SCHEDULERS=True,
        HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION=False,
        HYDRA_DEPLOYMENT_REVISION="test-revision",
        HYDRA_PORTAL_URL="https://portal.example.test/",
        HYDRA_ONBOARDING_PORTAL_BASE_URL="https://onboarding.example.test/",
        HYDRA_NOTIFICATION_BASE_URL="https://hydra.example.test/",
        MEDIA_ROOT="/srv/hydra/public",
        HYDRA_PORTAL_EMAIL_MEDIA_ROOT="/srv/hydra/outbox",
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=3600,
        HYDRA_DOCUMENT_SCANNER="clamd",
        HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS=365,
        HYDRA_IMPORT_PREVIEW_RETENTION_HOURS=72,
        HYDRA_IMPORT_APPLIED_RETENTION_HOURS=24,
        HYDRA_DOCUMENT_QUARANTINE_HOURS=72,
        HYDRA_NOTIFICATION_MAX_ATTEMPTS=10,
        HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS=60,
        HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS=3600,
        HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS=120,
        EMAIL_HOST="smtp.example.test",
        EMAIL_PORT=587,
        EMAIL_HOST_USER="hydra-smtp",
        EMAIL_HOST_PASSWORD="strong-test-password",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        EMAIL_USE_TLS=True,
        EMAIL_USE_SSL=False,
        EMAIL_FAIL_SILENTLY=False,
        EMAIL_TIMEOUT=30,
        HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=8,
        HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS=60,
        HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS=3600,
        HYDRA_PORTAL_EMAIL_LEASE_SECONDS=120,
        HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS=72,
        HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS=8,
        HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES=10 * 1024 * 1024,
        HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES=25 * 1024 * 1024,
        HYDRA_MAINTENANCE_INTERVAL_SECONDS=30,
        HYDRA_MAINTENANCE_STALE_SECONDS=120,
        HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS=3600,
        HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE=100,
        HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=25,
        HYDRA_MAINTENANCE_MAX_FAILURES=5,
        HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS=(30, 7, 1),
        HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS=(90, 30, 7),
        HYDRA_ARRIVAL_REMINDER_MINUTES=(1440, 120),
    )
    def test_hardened_staging_configuration_passes(self):
        self.assertTrue(all(result.ok for result in configuration_results()))

    @override_settings(
        HYDRA_ENVIRONMENT="staging",
        DEBUG=True,
        SECRET_KEY="django-insecure-change-me",
        ALLOWED_HOSTS=["*"],
        CSRF_TRUSTED_ORIGINS=["http://staging.example.test"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
        HYDRA_DISABLE_SCHEDULERS=False,
        HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION=True,
        HYDRA_DEPLOYMENT_REVISION="",
        HYDRA_PORTAL_URL="http://portal.example.test/",
        HYDRA_ONBOARDING_PORTAL_BASE_URL="http://onboarding.example.test/",
        HYDRA_NOTIFICATION_BASE_URL="http://hydra.example.test/",
        MEDIA_ROOT="/srv/hydra/public",
        HYDRA_PORTAL_EMAIL_MEDIA_ROOT="/srv/hydra/public/outbox",
        SECURE_SSL_REDIRECT=False,
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        SECURE_HSTS_SECONDS=0,
        HYDRA_DOCUMENT_SCANNER="disabled",
        HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS=0,
        HYDRA_IMPORT_PREVIEW_RETENTION_HOURS=0,
        HYDRA_IMPORT_APPLIED_RETENTION_HOURS=0,
        HYDRA_DOCUMENT_QUARANTINE_HOURS=0,
        HYDRA_NOTIFICATION_MAX_ATTEMPTS=0,
        HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS=0,
        HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS=0,
        HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS=0,
        EMAIL_HOST="",
        EMAIL_PORT=0,
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
        DEFAULT_FROM_EMAIL="invalid",
        EMAIL_USE_TLS=False,
        EMAIL_USE_SSL=False,
        EMAIL_FAIL_SILENTLY=True,
        EMAIL_TIMEOUT=0,
        HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=0,
        HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS=0,
        HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS=0,
        HYDRA_PORTAL_EMAIL_LEASE_SECONDS=0,
        HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS=0,
        HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS=0,
        HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES=0,
        HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES=0,
        HYDRA_MAINTENANCE_INTERVAL_SECONDS=0,
        HYDRA_MAINTENANCE_STALE_SECONDS=0,
        HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS=0,
        HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=0,
        HYDRA_MAINTENANCE_MAX_FAILURES=0,
        HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS=(0, 7, 7),
        HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS=(),
        HYDRA_ARRIVAL_REMINDER_MINUTES=(0, 120, 120),
    )
    def test_insecure_staging_configuration_fails_closed(self):
        failed_names = {result.name for result in configuration_results() if not result.ok}
        self.assertIn("debug", failed_names)
        self.assertIn("secret_key", failed_names)
        self.assertIn("allowed_hosts", failed_names)
        self.assertIn("legacy_schedulers", failed_names)
        self.assertIn("web_database_initialization", failed_names)
        self.assertIn("document_scanner", failed_names)
        self.assertIn("document_retention", failed_names)
        self.assertIn("candidate_import_retention", failed_names)
        self.assertIn("quarantine_retention", failed_names)
        self.assertIn("notification_retry_limit", failed_names)
        self.assertIn("notification_base_url", failed_names)
        self.assertIn("notification_email_policy", failed_names)
        self.assertIn("onboarding_portal_url", failed_names)
        self.assertIn("portal_email_storage", failed_names)
        self.assertIn("portal_email_policy", failed_names)
        self.assertIn("smtp_configuration", failed_names)
        self.assertIn("maintenance_policy", failed_names)
        self.assertIn("legalization_automation_policy", failed_names)
        self.assertIn("arrival_automation_policy", failed_names)

    @override_settings(HYDRA_DISABLE_SCHEDULERS=False)
    def test_management_commands_never_start_legacy_schedulers(self):
        self.assertFalse(should_start_schedulers(["manage.py", "check"]))
        self.assertTrue(should_start_schedulers(["gunicorn"]))

    @override_settings(HYDRA_DISABLE_SCHEDULERS=True)
    def test_disable_flag_blocks_all_legacy_schedulers(self):
        self.assertFalse(should_start_schedulers(["gunicorn"]))

    @override_settings(HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION=False)
    def test_database_initialization_routes_are_hidden(self):
        middleware = DisableDatabaseInitializationMiddleware(lambda request: HttpResponse("ok"))
        request = RequestFactory().get("/initialize-database")
        self.assertEqual(middleware(request).status_code, 404)

    @override_settings(HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION=True)
    def test_database_initialization_routes_remain_available_in_development(self):
        middleware = DisableDatabaseInitializationMiddleware(lambda request: HttpResponse("ok"))
        request = RequestFactory().get("/initialize-database")
        self.assertEqual(middleware(request).status_code, 200)


class ReadinessEndpointTests(TestCase):
    @patch("hydra_ops.views.collect_readiness")
    def test_ready_endpoint_returns_only_public_status(self, collect):
        collect.return_value = [ReadinessResult("database", True, "secret detail")]
        response = self.client.get(reverse("hydra-readiness"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})
        self.assertEqual(response["Cache-Control"], "no-store")

    @patch("hydra_ops.views.collect_readiness")
    def test_ready_endpoint_returns_503_without_details(self, collect):
        collect.return_value = [ReadinessResult("database", False, "internal detail")]
        response = self.client.get(reverse("hydra-readiness"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "not_ready"})
        self.assertNotContains(response, "internal detail", status_code=503)

    @patch("hydra_ops.management.commands.hydra_readiness.collect_readiness")
    def test_management_command_json_and_failure_exit(self, collect):
        collect.return_value = [ReadinessResult("database", False, "unavailable")]
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("hydra_readiness", "--json", stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "not_ready")

    def test_payload_is_ready_only_when_every_check_passes(self):
        payload = readiness_payload(
            [ReadinessResult("database", True, "ok"), ReadinessResult("migrations", True, "ok")]
        )
        self.assertEqual(payload["status"], "ready")
