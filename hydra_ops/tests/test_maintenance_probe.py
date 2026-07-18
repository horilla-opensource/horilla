from unittest.mock import patch

import psycopg2
from django.test import SimpleTestCase

from hydra_ops.maintenance_probe import maintenance_probe


PROBE_ENVIRONMENT = {
    "DB_NAME": "hydra",
    "DB_USER": "hydra_app",
    "DB_PASSWORD": "test-only-database-password",  # pragma: allowlist secret
    "DB_HOST": "db",
    "DB_PORT": "5432",
    "HYDRA_MAINTENANCE_STALE_SECONDS": "120",
    "HYDRA_MAINTENANCE_MAX_FAILURES": "5",
}


class MaintenanceProbeTests(SimpleTestCase):
    @patch.dict("os.environ", PROBE_ENVIRONMENT, clear=True)
    @patch("hydra_ops.maintenance_probe.psycopg2.connect")
    def test_probe_checks_fresh_heartbeat_and_failure_threshold(self, connect):
        connection = connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True, True)

        self.assertTrue(maintenance_probe())

        connect.assert_called_once_with(
            dbname="hydra",
            user="hydra_app",
            password="test-only-database-password",  # pragma: allowlist secret
            host="db",
            port="5432",
            connect_timeout=5,
            options="-c statement_timeout=5000",
        )
        parameters = cursor.execute.call_args.args[1]
        self.assertEqual(parameters, (120, 5))

    @patch.dict("os.environ", PROBE_ENVIRONMENT, clear=True)
    @patch("hydra_ops.maintenance_probe.psycopg2.connect")
    def test_probe_rejects_stale_or_failed_worker_state(self, connect):
        connection = connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (False, True)

        self.assertFalse(maintenance_probe())

    @patch.dict("os.environ", PROBE_ENVIRONMENT, clear=True)
    @patch("hydra_ops.maintenance_probe.psycopg2.connect")
    def test_probe_fails_closed_without_exposing_database_error(self, connect):
        connect.side_effect = psycopg2.OperationalError("private database detail")

        self.assertFalse(maintenance_probe())
