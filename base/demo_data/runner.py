"""Orchestrate the enterprise demo seeder after fixtures load."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from django.conf import settings

from base.demo_data.companies import ensure_companies
from base.demo_data.media import copy_demo_media
from base.demo_data.modules.announcements import refresh_announcements
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

    logger.info("Enterprise demo seeder finished: %s", result)
    return result
