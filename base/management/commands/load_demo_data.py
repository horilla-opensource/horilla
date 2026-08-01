import os
import shutil
import tempfile
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from base.views import _shift_fixture_dates, normalize_demo_payslips


class Command(BaseCommand):
    help = (
        "Load demo fixture data with dates shifted relative to today. "
        "Use --flush to wipe the database first (full demo reset)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush all existing data before loading (full reset).",
        )
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Do not prompt for confirmation.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            if options["interactive"]:
                confirm = input(
                    "This will DELETE all data in the database and reload demo fixtures.\n"
                    "Are you sure? [yes/no]: "
                )
                if confirm.lower() != "yes":
                    self.stdout.write("Aborted.")
                    return
            self.stdout.write("Flushing database...")
            call_command("flush", "--no-input", verbosity=0)
            self.stdout.write(self.style.SUCCESS("Database flushed."))

        self._copy_demo_icons(load_dir=Path(settings.BASE_DIR) / "load_data")

        data_files = [
            "user_data.json",
            "employee_info_data.json",
            "base_data.json",
            "work_info_data.json",
        ]
        optional_apps = [
            ("attendance", "attendance_data.json"),
            ("leave", "leave_data.json"),
            ("asset", "asset_data.json"),
            ("recruitment", "recruitment_data.json"),
            ("onboarding", "onboarding_data.json"),
            ("offboarding", "offboarding_data.json"),
            ("pms", "pms_data.json"),
            ("payroll", "payroll_data.json"),
            ("payroll", "payroll_loanaccount_data.json"),
            ("project", "project_data.json"),
        ]
        data_files += [f for app, f in optional_apps if apps.is_installed(app)]

        load_dir = Path(settings.BASE_DIR) / "load_data"
        loaded = 0
        errors = 0

        for fname in data_files:
            file_path = load_dir / fname
            if not file_path.exists():
                self.stdout.write(self.style.WARNING(f"  Skipped (not found): {fname}"))
                continue

            tmp = None
            try:
                shifted = _shift_fixture_dates(str(file_path))
                if shifted is not None:
                    suffix = file_path.suffix
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=suffix, delete=False, encoding="utf-8"
                    ) as tmp_f:
                        tmp_f.write(shifted)
                        tmp = tmp_f.name
                    call_command("loaddata", tmp, verbosity=0)
                else:
                    call_command("loaddata", str(file_path), verbosity=0)
                self.stdout.write(self.style.SUCCESS(f"  Loaded: {fname}"))
                loaded += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Error loading {fname}: {e}"))
                errors += 1
            finally:
                if tmp and os.path.exists(tmp):
                    os.remove(tmp)

        normalized = normalize_demo_payslips()
        if normalized:
            self.stdout.write(
                self.style.SUCCESS(f"  Re-anchored {normalized} demo payslip(s).")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {loaded} fixture(s) loaded, {errors} error(s)."
            )
        )

    def _copy_demo_icons(self, load_dir: Path):
        """Copy bundled company icons to MEDIA_ROOT so fixture image paths resolve."""
        icons_src = load_dir / "icons"
        if not icons_src.exists():
            return

        dest_dir = Path(settings.MEDIA_ROOT) / "base" / "icon"
        dest_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for icon_file in icons_src.glob("*.png"):
            dest = dest_dir / icon_file.name
            shutil.copy2(icon_file, dest)
            copied += 1

        if copied:
            self.stdout.write(
                self.style.SUCCESS(f"  Copied {copied} company icon(s) to media.")
            )
