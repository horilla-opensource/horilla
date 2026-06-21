"""
One-time reconciliation for databases created BEFORE migrations were tracked
in git.

Such databases already contain almost the full schema (built by the old,
regenerated-on-every-deploy migrations) but their recorded migration history
does not match the now-committed migration files. Running a normal ``migrate``
therefore fails with "column ... already exists", while the genuinely new
columns (children_info, the bank fields, verb_ua, the EmployeeLeaveApprover
table, ...) are still missing.

This command:
  1. marks every committed migration as applied WITHOUT running any DDL
     (``migrate --fake``), aligning the migration history with the existing
     schema; then
  2. adds only the columns/tables that are genuinely new, using Django's schema
     editor so types, defaults, FKs and indexes match the models exactly.

It is idempotent (safe to run more than once). Trigger it for a single deploy
by setting the env var ``RECONCILE_DB=1`` on the service, then remove that
variable so subsequent deploys run a normal ``migrate``.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Reconcile a legacy database with committed migrations (fake + add new columns)."

    def handle(self, *args, **options):
        # Mark every committed migration as applied WITHOUT running any DDL.
        # We record directly (instead of `migrate --fake`) so it works even when
        # the legacy recorded history doesn't perfectly match the committed graph
        # (which otherwise raises InconsistentMigrationHistory).
        self.stdout.write("Recording all migrations as applied (no DDL)...")
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        already_applied = recorder.applied_migrations()
        recorded = 0
        for app_label, name in loader.disk_migrations.keys():
            if (app_label, name) not in already_applied:
                recorder.record_applied(app_label, name)
                recorded += 1
        self.stdout.write(f"  recorded {recorded} migration(s) as applied")

        from employee.models import (
            Employee,
            EmployeeBankDetails,
            EmployeeLeaveApprover,
        )
        from notifications.models import Notification

        def column_names(table):
            with connection.cursor() as cursor:
                return {
                    col.name
                    for col in connection.introspection.get_table_description(
                        cursor, table
                    )
                }

        added = []
        with connection.schema_editor() as editor:
            existing = column_names("employee_employee")
            for name in ("children_info", "np_branch", "np_postomat"):
                if name not in existing:
                    editor.add_field(Employee, Employee._meta.get_field(name))
                    added.append(f"employee_employee.{name}")

            existing = column_names("employee_employeebankdetails")
            for name in (
                "iban",
                "rnokpp",
                "payment_purpose",
                "fop_maintained",
                "card_number",
                "wallet_number",
                "wallet_currency",
            ):
                if name not in existing:
                    editor.add_field(
                        EmployeeBankDetails,
                        EmployeeBankDetails._meta.get_field(name),
                    )
                    added.append(f"employee_employeebankdetails.{name}")

            existing = column_names("notifications_notification")
            if "verb_ua" not in existing:
                editor.add_field(Notification, Notification._meta.get_field("verb_ua"))
                added.append("notifications_notification.verb_ua")

            if (
                "employee_employeeleaveapprover"
                not in connection.introspection.table_names()
            ):
                editor.create_model(EmployeeLeaveApprover)
                added.append("table employee_employeeleaveapprover")

        # bank_name became nullable; DROP NOT NULL is a no-op if already nullable.
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE employee_employeebankdetails "
                    "ALTER COLUMN bank_name DROP NOT NULL;"
                )
        except Exception as exc:  # pragma: no cover - DB-specific / already nullable
            self.stdout.write(self.style.WARNING(f"bank_name nullability: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Reconcile complete. Added: "
                + (", ".join(added) if added else "nothing (schema already current)")
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Now remove the RECONCILE_DB env var so future deploys run a normal migrate."
            )
        )
