"""
Drop-in replacement for ``migrate`` that also heals databases created BEFORE
migrations were tracked in git.

Such a database already contains almost the full schema (built by the old
migrations that were regenerated on every deploy) but its recorded migration
history does not line up with the now-committed migration files. A normal
``migrate`` then fails with "column ... already exists", while the genuinely new
columns (children_info, the bank fields, verb_ua, the EmployeeLeaveApprover
table, ...) are never created.

This command:

  1. applies migrations one at a time; if a migration fails only because its
     schema objects already exist, it is recorded as applied (faked) and the
     run continues;
  2. adds the handful of columns/tables that are new but bundled inside an
     already-existing table's ``CreateModel`` (so step 1 faked them), using the
     schema editor so types/defaults/FKs/indexes match the models exactly.

On a healthy or fresh database it behaves exactly like ``migrate`` (step 1
applies any pending migrations normally; step 2 is a no-op because the columns
already exist), so it is safe to use in place of ``migrate`` permanently.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

# Errors that mean "the schema object this migration creates is already there".
_ALREADY_EXISTS = ("already exists", "duplicate column", "duplicate table")


class Command(BaseCommand):
    help = "Apply migrations, healing legacy databases whose schema predates committed migrations."

    def handle(self, *args, **options):
        self._apply_or_fake_migrations()
        self._add_missing_columns()

    # 1. migrate, faking only the migrations whose objects already exist
    def _apply_or_fake_migrations(self):
        guard = 0
        while True:
            guard += 1
            if guard > 1000:
                raise RuntimeError("Migration loop did not converge.")
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if not plan:
                self.stdout.write(self.style.SUCCESS("All migrations applied."))
                return
            migration, _backwards = plan[0]
            app_label, name = migration.app_label, migration.name
            try:
                call_command("migrate", app_label, name, verbosity=0)
                self.stdout.write(f"applied {app_label}.{name}")
            except Exception as exc:  # noqa: BLE001 - we re-raise unknown errors
                message = str(exc).lower()
                connection.close()  # clear any aborted transaction state
                if any(token in message for token in _ALREADY_EXISTS):
                    MigrationRecorder(connection).record_applied(app_label, name)
                    self.stdout.write(
                        self.style.WARNING(
                            f"faked {app_label}.{name} (objects already exist)"
                        )
                    )
                else:
                    raise

    # 2. add columns/tables that are new but were faked away in step 1
    def _add_missing_columns(self):
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
            self.stdout.write(self.style.WARNING(f"bank_name nullability skipped: {exc}"))

        if added:
            self.stdout.write(self.style.SUCCESS("Added: " + ", ".join(added)))
        else:
            self.stdout.write(self.style.SUCCESS("Schema already current."))
