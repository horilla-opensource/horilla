import os
import tempfile
import traceback
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from base.demo_data import run_enterprise_demo_seeder
from base.demo_data.fixtures import demo_fixture_files
from base.demo_data.media import copy_demo_media
from base.demo_roles import assign_demo_user_groups
from base.views import (
    _shift_fixture_dates,
    normalize_demo_payslips,
    reset_backfilled_rows_before_reload,
)


class Command(BaseCommand):
    help = (
        "Load demo fixture data with dates shifted relative to today, then apply "
        "the enterprise demo seeder. Use --flush to wipe the database first."
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

        load_dir = Path(settings.BASE_DIR) / "load_data"
        media_stats = copy_demo_media(load_dir)
        if media_stats.get("icons") or media_stats.get("avatars"):
            self.stdout.write(
                self.style.SUCCESS(
                    "  Copied media: "
                    f"{media_stats.get('icons', 0)} icon(s), "
                    f"{media_stats.get('avatars', 0)} avatar(s)."
                )
            )

        data_files = demo_fixture_files()

        loaded = 0
        errors = 0

        for fname in data_files:
            file_path = load_dir / fname
            if not file_path.exists():
                self.stdout.write(self.style.WARNING(f"  Skipped (not found): {fname}"))
                continue

            tmp = None
            try:
                reset_backfilled_rows_before_reload(fname)
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

        try:
            seed_result = run_enterprise_demo_seeder(
                load_dir=load_dir, copy_media=False, scrub_side_files=True
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "  Enterprise seeder applied: "
                    f"companies={seed_result.get('companies', 0)}, "
                    f"announcements={seed_result.get('announcements', 0)}, "
                    f"org={seed_result.get('org', {})}."
                )
            )
        except Exception:
            # The seeder is one long sequence of ~25 steps -- without this,
            # an exception from any one of them would crash the whole
            # command before normalize_demo_payslips()/assign_demo_user_groups()
            # below ever run. Mirrors the web-UI reload path's same
            # warn-and-continue behavior (base/views.py's load_demo_database)
            # instead of leaving the two entry points asymmetric.
            self.stderr.write(
                self.style.ERROR("  Enterprise demo seeder failed partway through:")
            )
            self.stderr.write(self.style.ERROR(traceback.format_exc()))

        normalized = normalize_demo_payslips()
        if normalized:
            self.stdout.write(
                self.style.SUCCESS(f"  Re-anchored {normalized} demo payslip(s).")
            )

        try:
            assigned = assign_demo_user_groups()
            if assigned:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Assigned demo roles to {assigned} membership(s)."
                    )
                )
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"  Demo roles skipped: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {loaded} fixture(s) loaded, {errors} error(s)."
            )
        )
