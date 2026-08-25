"""Connect the Asset Report feature to real demo data.

AssetReport/AssetDocuments exist purely to attach a report and file
attachments to an asset, but ship with zero rows -- the "Report" action on
every asset in the demo has nothing to show.
"""

from __future__ import annotations

import logging
from datetime import date

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TARGET_REPORT_COUNT = 10


@transaction.atomic
def backfill_asset_reports(today: date | None = None) -> int:
    """Ensure a fixed target number of assets have an AssetReport (+ an
    empty AssetDocuments placeholder) attached, capped at
    TARGET_REPORT_COUNT total rather than +N more on every call -- without
    the cap, repeated non-flush reloads would keep adding reports until
    every asset in the demo has one."""
    if not apps.is_installed("asset"):
        return 0

    from asset.models import Asset, AssetDocuments, AssetReport

    already_covered = AssetReport._base_manager.count()
    need = max(0, TARGET_REPORT_COUNT - already_covered)
    if need <= 0:
        return 0

    asset_ids = list(
        Asset._base_manager.exclude(
            pk__in=AssetReport._base_manager.values_list("asset_id", flat=True)
        )
        .order_by("id")
        .values_list("id", flat=True)[:need]
    )

    created = 0
    for asset_id in asset_ids:
        report, was_created = AssetReport._base_manager.get_or_create(
            asset_id_id=asset_id,
            defaults={"title": "Condition check"},
        )
        if was_created:
            AssetDocuments._base_manager.get_or_create(asset_report=report)
            created += 1

    logger.info("Asset feature backfill: %s asset report(s) created", created)
    return created
