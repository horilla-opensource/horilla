"""Prove the mail-template rebrand upgrades data without renaming its table."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_DIR = ROOT / ".local" / "verification"
DATABASE_PATH = VERIFICATION_DIR / "rebrand-migration.sqlite3"
LEGACY_PREFIX = "hori" + "lla"

sys.path.insert(0, str(ROOT))
VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
if DATABASE_PATH.exists():
    DATABASE_PATH.unlink()

print("[1/4] Initializing Django for the isolated migration database...", flush=True)

os.environ["DB_ENGINE"] = "django.db.backends.sqlite3"
os.environ["DB_NAME"] = str(DATABASE_PATH)
os.environ["DJANGO_SETTINGS_MODULE"] = "hydra.settings"
os.environ["HYDRA_DISABLE_SCHEDULERS"] = "True"
os.environ["HYDRA_ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "hydra-migration-verification"  # pragma: allowlist secret

import django  # noqa: E402

django.setup()

from django.db import connection, connections  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402


def main() -> int:
    try:
        print("[2/4] Migrating to the pre-rebrand state...", flush=True)
        executor = MigrationExecutor(connection)
        old_target = [("base", "0002_initial")]
        executor.migrate(old_target)
        old_state = executor.loader.project_state(old_target)

        OldTemplate = old_state.apps.get_model(
            "base", LEGACY_PREFIX.title() + "MailTemplate"
        )
        ContentType = old_state.apps.get_model("contenttypes", "ContentType")
        Permission = old_state.apps.get_model("auth", "Permission")

        OldTemplate._base_manager.create(title="upgrade-probe", body="probe")
        content_type = ContentType.objects.create(
            app_label="base", model=LEGACY_PREFIX + "mailtemplate"
        )
        Permission.objects.create(
            content_type=content_type,
            codename="view_" + LEGACY_PREFIX + "mailtemplate",
            name="Can view " + LEGACY_PREFIX.title() + " mail template",
        )

        print("[3/4] Migrating the database to the current graph...", flush=True)
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

        print("[4/4] Verifying data, permissions, and physical tables...", flush=True)
        from base.models import HydraMailTemplate
        from django.contrib.auth.models import Permission as CurrentPermission
        from django.contrib.contenttypes.models import ContentType as CurrentContentType

        assert HydraMailTemplate._base_manager.filter(title="upgrade-probe").exists()
        assert CurrentContentType.objects.filter(
            app_label="base", model="hydramailtemplate"
        ).exists()
        assert not CurrentContentType.objects.filter(
            app_label="base", model=LEGACY_PREFIX + "mailtemplate"
        ).exists()
        assert CurrentPermission.objects.filter(
            content_type__app_label="base", codename="view_hydramailtemplate"
        ).exists()
        tables = set(connection.introspection.table_names())
        assert "base_" + LEGACY_PREFIX + "mailtemplate" in tables
        assert "base_hydramailtemplate" not in tables

        print("Verified rebrand migration: data, permission, and physical table preserved.")
        return 0
    finally:
        connections.close_all()
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
