"""Spread demo EmployeeObjective dates across a real trailing 6 months.

Only 8 EmployeeObjective rows exist across the base + scenarios fixtures,
clustered around a single month roughly 10-14 months before any reasonable
"today" -- well outside a 6-month trailing window regardless of the anchor
shift. The PMS progress trend groups by `updated_at`, which is `auto_now=True`
-- a plain `.save()` always resets it to today, so this must go through
`.filter().update()` (which bypasses `auto_now`, same as normalize_demo_payslips).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180


@transaction.atomic
def backfill_pms_objectives(today: date | None = None) -> int:
    """Spread every EmployeeObjective's updated_at (and start/end_date, shifted
    by the same delta) across the trailing 6 months."""
    if not apps.is_installed("pms"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from pms.models import EmployeeObjective

    rows = list(
        EmployeeObjective._base_manager.order_by("id").values(
            "id", "start_date", "end_date", "updated_at"
        )
    )
    count = len(rows)
    updated = 0
    for i, row in enumerate(rows):
        # count-1: the last objective lands at exactly today instead of one
        # step short of it, so the current month isn't left empty.
        offset = int(i * TRAILING_DAYS / max(count - 1, 1))
        new_updated_at = window_start + timedelta(days=offset)
        delta_days = (
            (new_updated_at - row["updated_at"]).days if row["updated_at"] else 0
        )
        new_start = (
            row["start_date"] + timedelta(days=delta_days)
            if row["start_date"]
            else None
        )
        new_end = (
            row["end_date"] + timedelta(days=delta_days) if row["end_date"] else None
        )
        EmployeeObjective._base_manager.filter(pk=row["id"]).update(
            updated_at=new_updated_at, start_date=new_start, end_date=new_end
        )
        updated += 1

    logger.info(
        "PMS backfill: spread %s objective(s) over the trailing %s days",
        updated,
        TRAILING_DAYS,
    )
    return updated
