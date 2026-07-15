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
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=3600,
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
        SECURE_SSL_REDIRECT=False,
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        SECURE_HSTS_SECONDS=0,
    )
    def test_insecure_staging_configuration_fails_closed(self):
        failed_names = {result.name for result in configuration_results() if not result.ok}
        self.assertIn("debug", failed_names)
        self.assertIn("secret_key", failed_names)
        self.assertIn("allowed_hosts", failed_names)
        self.assertIn("legacy_schedulers", failed_names)
        self.assertIn("web_database_initialization", failed_names)

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
