"""Connect the Rejected Candidates feature to real demo data.

Two candidates already sit in a cancelled-type stage, and two RejectReason
rows already exist, but no RejectedCandidate row ever links them -- the
Rejected Candidates report has nothing to show despite the underlying data
already telling that story everywhere else.
"""

from __future__ import annotations

import logging
from datetime import date

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)


@transaction.atomic
def backfill_rejected_candidates(today: date | None = None) -> int:
    """Ensure every candidate in a cancelled-type stage has a matching
    RejectedCandidate row, cycling through the existing RejectReason catalog."""
    if not apps.is_installed("recruitment"):
        return 0

    from recruitment.models import Candidate, RejectedCandidate, RejectReason

    reject_reason_ids = list(
        RejectReason._base_manager.order_by("id").values_list("id", flat=True)
    )
    if not reject_reason_ids:
        return 0

    cancelled_ids = list(
        Candidate._base_manager.filter(stage_id__stage_type="cancelled")
        .exclude(
            pk__in=RejectedCandidate._base_manager.values_list(
                "candidate_id", flat=True
            )
        )
        .order_by("id")
        .values_list("id", flat=True)
    )

    created = 0
    for i, candidate_id in enumerate(cancelled_ids):
        rejected, was_created = RejectedCandidate._base_manager.get_or_create(
            candidate_id_id=candidate_id,
            defaults={"description": "Not selected to move forward at this time."},
        )
        if was_created:
            rejected.reject_reason_id.add(reject_reason_ids[i % len(reject_reason_ids)])
            created += 1

    logger.info(
        "Recruitment feature backfill: %s rejected candidate(s) linked", created
    )
    return created
