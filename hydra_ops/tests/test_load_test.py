import csv
import json
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from requests.cookies import RequestsCookieJar, create_cookie

from hydra_ops.load_test import ROLE_WEIGHTS, group_name, role_counts, username_for
from hydra_ops.load_views import _read_profile
from hydra_people.models import CandidateStageTransition
from load_tests.cookies import prepare_internal_http_cookies
from load_tests.summarize import summarize_run


User = get_user_model()


class LoadTestContractTests(TestCase):
    def test_private_http_hop_reenables_only_hydra_secure_cookies(self):
        jar = RequestsCookieJar()
        for name in ("hydra_csrftoken", "hydra_sessionid", "unrelated"):
            jar.set_cookie(create_cookie(name, "opaque", secure=True))

        prepare_internal_http_cookies(jar)

        secure_by_name = {cookie.name: cookie.secure for cookie in jar}
        self.assertFalse(secure_by_name["hydra_csrftoken"])
        self.assertFalse(secure_by_name["hydra_sessionid"])
        self.assertTrue(secure_by_name["unrelated"])

    def test_role_weights_match_the_required_business_profile(self):
        self.assertEqual(sum(ROLE_WEIGHTS.values()), 100)
        self.assertEqual(
            role_counts(200),
            {
                "recruiter": 50,
                "hr_admin": 40,
                "coordination": 30,
                "employee": 30,
                "legal_housing": 20,
                "onboarding": 20,
                "dashboard": 10,
            },
        )

    def test_role_counts_cover_every_required_stage_without_dropping_users(self):
        expected = {
            20: (5, 4, 3, 3, 2, 2, 1),
            50: (13, 10, 8, 7, 5, 5, 2),
            100: (25, 20, 15, 15, 10, 10, 5),
            150: (38, 30, 23, 22, 15, 15, 7),
            200: (50, 40, 30, 30, 20, 20, 10),
        }
        for users, counts in expected.items():
            with self.subTest(users=users):
                actual = role_counts(users)
                self.assertEqual(tuple(actual.values()), counts)
                self.assertEqual(sum(actual.values()), users)

    def test_account_and_group_names_are_deterministic(self):
        self.assertEqual(
            username_for("test-run", "recruiter", 3),
            "hydra-load-test-run-recruiter-003",
        )
        self.assertEqual(
            group_name("test-run", "recruiter"),
            "HYDRA_LOAD:test-run:recruiter",
        )

    def test_machine_summary_enforces_duration_users_safety_and_latency_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary)
            fieldnames = (
                "Type",
                "Name",
                "Request Count",
                "Failure Count",
                "Requests/s",
                "50%",
                "95%",
                "99%",
            )
            rows = [
                ("", "Aggregated", 1000, 0, 25, 100, 400, 900),
                ("GET", "GET /login/ [login]", 20, 0, 1, 100, 300, 500),
                ("GET", "dashboard [typical-read]", 50, 0, 3, 100, 300, 500),
                ("GET", "role [list-filter]", 700, 0, 18, 100, 400, 700),
                ("POST", "role [business-write]", 230, 0, 3, 150, 500, 900),
            ]
            with (artifacts / "locust_stats.csv").open("w", newline="", encoding="utf-8") as target:
                writer = csv.DictWriter(target, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(zip(fieldnames, row)))
            with (artifacts / "locust_stats_history.csv").open("w", newline="", encoding="utf-8") as target:
                writer = csv.DictWriter(target, fieldnames=("Name", "User Count"))
                writer.writeheader()
                writer.writerow({"Name": "Aggregated", "User Count": 20})
            (artifacts / "resources.csv").write_text(
                "cpu_percent,memory_percent,db_connections,redis_used_memory_bytes\n"
                "55.5,60.5,12,1000000\n",
                encoding="utf-8",
            )
            (artifacts / "run-evidence.json").write_text(
                json.dumps(
                    {
                        "elapsed_seconds": 900,
                        "full_concurrency_seconds": 900,
                        "web_replicas": 2,
                        "safety_stop_triggered": False,
                        "readiness_failures": 0,
                        "oom_count": 0,
                        "restart_loop_count": 0,
                        "db_connection_safety_limit": 50,
                        "integrity_before": True,
                        "integrity_after": True,
                        "controlled_restart_completed": False,
                        "think_time_min_seconds": 15,
                        "think_time_max_seconds": 25,
                    }
                ),
                encoding="utf-8",
            )
            summary = summarize_run(
                artifacts=artifacts,
                stage="20",
                users=20,
                duration_seconds=900,
            )
            self.assertTrue(summary["overall_pass"])
            self.assertEqual(summary["max_active_users"], 20)
            self.assertEqual(summary["topology"], {"web_replicas": 2})
            self.assertEqual(summary["resource_peaks"]["db_connections"], 12)
            self.assertEqual(
                summary["workload"],
                {"think_time_min_seconds": 15, "think_time_max_seconds": 25},
            )
            self.assertTrue(summary["acceptance"]["committed_business_pacing"])
            self.assertTrue(
                summary["acceptance"]["web_replica_count_between_2_and_4"]
            )


@override_settings(
    HYDRA_ENVIRONMENT="test",
    HYDRA_LOAD_TEST_ENABLED=True,
    HYDRA_LOAD_TEST_RUN_ID="test-run",
)
class LoadTestSeedAndEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with patch.dict(
            os.environ,
            {"HYDRA_LOAD_TEST_PASSWORD": "test-only-load-password"},  # pragma: allowlist secret
        ):
            call_command(
                "hydra_load_seed",
                "--run-id=test-run",
                "--users=20",
                stdout=StringIO(),
            )

    def test_seeded_data_passes_integrity(self):
        output = StringIO()
        call_command(
            "hydra_load_integrity",
            "--run-id=test-run",
            "--users=20",
            "--json",
            stdout=output,
        )
        self.assertIn('"status": "ok"', output.getvalue())

    def test_candidate_transition_integrity_uses_one_database_snapshot(self):
        output = StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command(
                "hydra_load_integrity",
                "--run-id=test-run",
                "--users=20",
                "--json",
                stdout=output,
            )

        transition_table = CandidateStageTransition._meta.db_table
        transition_queries = [
            query["sql"] for query in queries if transition_table in query["sql"]
        ]
        self.assertEqual(len(transition_queries), 1)
        self.assertIn("SELECT", transition_queries[0].upper())
        self.assertIn('"status": "ok"', output.getvalue())

    def test_query_profiler_covers_every_role_without_raw_sql(self):
        output = StringIO()
        call_command(
            "hydra_load_profile_queries",
            "--run-id=test-run",
            stdout=output,
        )
        payload = json.loads(output.getvalue())
        self.assertEqual(set(payload["profiles"]), set(ROLE_WEIGHTS))
        self.assertTrue(
            all(profile["query_count"] > 0 for profile in payload["profiles"].values())
        )
        self.assertNotIn("SELECT ", output.getvalue())

    def test_role_reads_stay_within_a_bounded_query_budget(self):
        for role in ROLE_WEIGHTS:
            with self.subTest(role=role):
                user = User.objects.get(username=f"hydra-load-test-run-{role}-001")
                user.get_all_permissions()
                with CaptureQueriesContext(connection) as queries:
                    result = _read_profile(
                        user=user,
                        role=role,
                        query="HYDRA_LOAD_TEST_RUN",
                    )
                self.assertIsInstance(result, dict)
                self.assertLessEqual(
                    len(queries),
                    20,
                    f"{role} read exceeded its N+1 regression budget",
                )

    def test_recruiter_has_separate_session_and_real_stage_write(self):
        user = User.objects.get(username="hydra-load-test-run-recruiter-001")
        self.client.force_login(user)
        read_url = reverse("hydra-load-test-read", kwargs={"role": "recruiter"})
        response = self.client.get(read_url, {"q": "HYDRA_LOAD_TEST_RUN"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)
        write_url = reverse("hydra-load-test-write", kwargs={"role": "recruiter"})
        response = self.client.post(write_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "candidate_stage")

    def test_seeded_password_establishes_a_real_authenticated_session(self):
        self.assertTrue(
            self.client.login(
                username="hydra-load-test-run-dashboard-001",
                password="test-only-load-password",  # pragma: allowlist secret
            )
        )
        response = self.client.get(
            reverse("hydra-load-test-read", kwargs={"role": "dashboard"})
        )
        self.assertEqual(response.status_code, 200)

    def test_every_writing_role_executes_a_real_domain_service(self):
        expected_actions = {
            "recruiter": "candidate_stage",
            "hr_admin": "person_contact",
            "coordination": "team_assignment",
            "employee": "task_status",
            "legal_housing": "housing_review",
            "onboarding": "onboarding_content",
        }
        for role, expected_action in expected_actions.items():
            with self.subTest(role=role):
                self.client.logout()
                user = User.objects.get(username=f"hydra-load-test-run-{role}-001")
                self.client.force_login(user)
                response = self.client.post(
                    reverse("hydra-load-test-write", kwargs={"role": role})
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["action"], expected_action)

    def test_wrong_role_is_hidden(self):
        user = User.objects.get(username="hydra-load-test-run-recruiter-001")
        self.client.force_login(user)
        response = self.client.get(
            reverse("hydra-load-test-read", kwargs={"role": "hr_admin"})
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(HYDRA_LOAD_TEST_ENABLED=False)
    def test_disabled_endpoint_is_hidden(self):
        user = User.objects.get(username="hydra-load-test-run-recruiter-001")
        self.client.force_login(user)
        response = self.client.get(
            reverse("hydra-load-test-read", kwargs={"role": "recruiter"})
        )
        self.assertEqual(response.status_code, 404)
