"""Create demo CandidateStage rows so the onboarding completion trend has data.

No CandidateStage row exists in any fixture today -- only the OnboardingStage
*definitions* were ever loaded, so `onboarding_end_date` (what the trend
chart groups by) has nothing to read. Recruitment #1 is the only recruitment
with a full onboarding pipeline (5 stages, one final), so this attaches
stage progress to its hired candidates, flipping a few more to hired=True
first since only 5 exist there by default -- too few for 6 months of spread.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180
RECRUITMENT_ID = 1
FINAL_STAGE_PK = 7  # "First Task Assignment" -- the only is_final_stage=True row
MID_STAGE_PK = 5  # "Technical Setup" -- a plausible still-in-progress stage
EXTRA_HIRE_CANDIDATE_IDS = (1, 2, 3, 5)


@transaction.atomic
def backfill_onboarding_pipeline(today: date | None = None) -> int:
    """Ensure a CandidateStage row exists for each hired recruitment-#1 candidate,
    spread across the trailing 6 months, with a realistic in-progress fraction.
    """
    if not apps.is_installed("onboarding") or not apps.is_installed("recruitment"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from onboarding.models import CandidateStage, OnboardingStage
    from recruitment.models import Candidate

    final_stage = OnboardingStage._base_manager.filter(
        pk=FINAL_STAGE_PK, recruitment_id=RECRUITMENT_ID, is_final_stage=True
    ).first()
    if not final_stage:
        logger.warning(
            "Onboarding backfill: expected final stage pk=%s not found, skipping",
            FINAL_STAGE_PK,
        )
        return 0
    mid_stage = (
        OnboardingStage._base_manager.filter(
            pk=MID_STAGE_PK, recruitment_id=RECRUITMENT_ID
        ).first()
        or final_stage
    )

    Candidate._base_manager.filter(
        pk__in=EXTRA_HIRE_CANDIDATE_IDS, recruitment_id=RECRUITMENT_ID
    ).update(hired=True)

    hired_ids = list(
        Candidate._base_manager.filter(recruitment_id=RECRUITMENT_ID, hired=True)
        .order_by("id")
        .values_list("id", flat=True)
    )
    if not hired_ids:
        return 0

    count = len(hired_ids)
    processed = 0
    for i, candidate_id in enumerate(hired_ids):
        # Roughly one in three still mid-pipeline -- except the very last
        # candidate (the one landing at exactly today), which always
        # completes, so the current month's bucket is never empty.
        in_progress = i % 3 == 2 and i != count - 1
        target_stage = mid_stage if in_progress else final_stage

        stage_row, _ = CandidateStage._base_manager.get_or_create(
            candidate_id_id=candidate_id,
            defaults={"onboarding_stage_id_id": target_stage.pk},
        )

        # count-1: the last candidate lands at exactly today instead of one
        # step short of it, so the current month isn't left empty.
        offset = int(i * TRAILING_DAYS / max(count - 1, 1))
        completion_date = None if in_progress else window_start + timedelta(days=offset)

        CandidateStage._base_manager.filter(pk=stage_row.pk).update(
            onboarding_stage_id_id=target_stage.pk,
            onboarding_end_date=completion_date,
        )
        processed += 1

    logger.info(
        "Onboarding backfill: %s candidate stage(s) spread over the trailing %s days",
        processed,
        TRAILING_DAYS,
    )
    return processed
