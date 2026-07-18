import hashlib
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from hydra_ops.load_test import ROLE_WEIGHTS, object_prefix, username_for, validate_run_id
from hydra_ops.load_views import _read_profile


User = get_user_model()


def _explain_select(sql):
    normalized = sql.lstrip().upper()
    if connection.vendor != "postgresql" or not normalized.startswith(("SELECT", "WITH")):
        return None
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        return cursor.fetchone()[0]


class Command(BaseCommand):
    help = "Profile isolated Hydra load reads and emit PostgreSQL execution plans."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True)

    def handle(self, *args, **options):
        run_id = validate_run_id(options["run_id"])
        if (
            not getattr(settings, "HYDRA_LOAD_TEST_ENABLED", False)
            or getattr(settings, "HYDRA_LOAD_TEST_RUN_ID", "") != run_id
            or getattr(settings, "HYDRA_ENVIRONMENT", "development")
            not in {"staging", "test"}
        ):
            raise CommandError("Query profiling requires the matching isolated load boundary.")

        profiles = {}
        for role in ROLE_WEIGHTS:
            try:
                user = User.objects.get(username=username_for(run_id, role, 1))
            except User.DoesNotExist as exc:
                raise CommandError(f"Missing seeded account for role {role}.") from exc
            with CaptureQueriesContext(connection) as captured:
                result = _read_profile(
                    user=user,
                    role=role,
                    query=object_prefix(run_id),
                )
            queries = []
            for query in captured.captured_queries:
                sql = query["sql"]
                try:
                    plan = _explain_select(sql)
                except Exception as exc:
                    raise CommandError(
                        f"EXPLAIN ANALYZE failed for role {role} ({type(exc).__name__})."
                    ) from exc
                queries.append(
                    {
                        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                        "recorded_seconds": float(query.get("time") or 0),
                        "explain_analyze_buffers": plan,
                    }
                )
            profiles[role] = {
                "query_count": len(queries),
                "recorded_seconds": sum(row["recorded_seconds"] for row in queries),
                "result_count": result.get("count", result.get("people", 0)),
                "queries": queries,
            }
        self.stdout.write(
            json.dumps(
                {
                    "run_id": run_id,
                    "database_vendor": connection.vendor,
                    "explain_analyze_buffers": connection.vendor == "postgresql",
                    "profiles": profiles,
                },
                sort_keys=True,
            )
        )
