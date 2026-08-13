"""Orchestrate the enterprise demo seeder after fixtures load."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from django.apps import apps
from django.conf import settings

from base.demo_data.companies import ensure_companies
from base.demo_data.media import copy_demo_media
from base.demo_data.modules.announcements import refresh_announcements
from base.demo_data.modules.attendance_trend import backfill_attendance_spread
from base.demo_data.modules.employee_lifecycle import backfill_employee_lifecycle
from base.demo_data.modules.helpdesk_trend import backfill_helpdesk_tickets
from base.demo_data.modules.leave_trend import backfill_leave_spread
from base.demo_data.modules.offboarding_trend import backfill_offboarding_letters
from base.demo_data.modules.onboarding_trend import backfill_onboarding_pipeline
from base.demo_data.modules.pms_trend import backfill_pms_objectives
from base.demo_data.modules.project_trend import backfill_project_trend
from base.demo_data.modules.recruitment import seed_recruitment_catalog
from base.demo_data.org import standardize_org_taxonomy
from base.demo_data.sanitize import sanitize_loaded_records, scrub_side_fixture_files

logger = logging.getLogger(__name__)


def run_enterprise_demo_seeder(
    *,
    load_dir: Path | None = None,
    today: date | None = None,
    copy_media: bool = True,
    scrub_side_files: bool = True,
) -> dict:
    """
    Standardize demo data after JSON fixtures are loaded.

    Safe to call repeatedly (idempotent renames / upserts). Does not create
    or delete employees — only activates companies, renames org taxonomy,
    refreshes announcements, and sanitizes vendor-specific labels.
    """
    today = today or date.today()
    root = Path(load_dir) if load_dir else Path(settings.BASE_DIR) / "load_data"
    result: dict = {"ok": True}

    if copy_media:
        result["media"] = copy_demo_media(root)

    if scrub_side_files:
        result["side_fixtures"] = scrub_side_fixture_files(root)

    result["companies"] = ensure_companies()
    result["org"] = standardize_org_taxonomy()
    result["announcements"] = refresh_announcements(today)
    result["recruitment"] = seed_recruitment_catalog()
    result["sanitized"] = sanitize_loaded_records()

    # Trailing-6-month dashboard backfill -- every function below computes
    # dates purely from `today`, so charts stay populated on every load
    # regardless of when it runs. Employee lifecycle runs before offboarding
    # since the latter reuses its chosen exit-employee ids.
    result["attendance_backfill"] = backfill_attendance_spread(today)
    result["leave_backfill"] = backfill_leave_spread(today)
    employee_lifecycle = backfill_employee_lifecycle(today)
    result["employee_lifecycle"] = employee_lifecycle
    result["project_backfill"] = backfill_project_trend(today)
    result["onboarding_backfill"] = backfill_onboarding_pipeline(today)
    result["offboarding_backfill"] = backfill_offboarding_letters(
        today, employee_lifecycle.get("exit_employee_ids")
    )
    result["pms_backfill"] = backfill_pms_objectives(today)
    result["helpdesk_backfill"] = backfill_helpdesk_tickets(today)

    # System ReportTemplate rows (Explorer's pre-built pivot layouts) aren't
    # part of any load_data/*.json fixture, so a --flush reload wipes them
    # silently unless they're re-seeded here too.
    if apps.is_installed("report"):
        from report.management.commands.seed_standard_report_templates import (
            seed_standard_report_templates,
        )

        created, updated = seed_standard_report_templates()
        result["report_templates"] = {"created": created, "updated": updated}

    logger.info("Enterprise demo seeder finished: %s", result)
    return result
