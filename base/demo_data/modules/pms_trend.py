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
    by the same delta) across the trailing 6 months, then cascade that same
    per-objective delta to EmployeeKeyResult, Comment, and Feedback so they
    don't drift out of sync with the objective's own re-dated window (e.g. a
    comment landing 1.5 years before the objective it's attached to)."""
    if not apps.is_installed("pms"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from pms.models import Comment, EmployeeKeyResult, EmployeeObjective, Feedback

    rows = list(
        EmployeeObjective._base_manager.order_by("id").values(
            "id", "start_date", "end_date", "updated_at"
        )
    )
    count = len(rows)
    updated = 0
    objective_deltas: dict[int, int] = {}
    for i, row in enumerate(rows):
        # count-1: the last objective lands at exactly today instead of one
        # step short of it, so the current month isn't left empty.
        offset = int(i * TRAILING_DAYS / max(count - 1, 1))
        new_updated_at = window_start + timedelta(days=offset)
        delta_days = (
            (new_updated_at - row["updated_at"]).days if row["updated_at"] else 0
        )
        objective_deltas[row["id"]] = delta_days
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

    key_result_deltas: dict[int, int] = {}
    for kr in EmployeeKeyResult._base_manager.filter(
        employee_objective_id__in=objective_deltas
    ).values("id", "employee_objective_id", "start_date", "end_date"):
        delta_days = objective_deltas[kr["employee_objective_id"]]
        EmployeeKeyResult._base_manager.filter(pk=kr["id"]).update(
            start_date=(
                kr["start_date"] + timedelta(days=delta_days)
                if kr["start_date"]
                else None
            ),
            end_date=(
                kr["end_date"] + timedelta(days=delta_days) if kr["end_date"] else None
            ),
        )
        key_result_deltas[kr["id"]] = delta_days

    for comment in Comment._base_manager.filter(
        employee_objective_id__in=objective_deltas
    ).values("id", "employee_objective_id", "created_at"):
        if not comment["created_at"]:
            continue
        delta_days = objective_deltas[comment["employee_objective_id"]]
        Comment._base_manager.filter(pk=comment["id"]).update(
            created_at=comment["created_at"] + timedelta(days=delta_days)
        )

    # Feedback links to an objective only indirectly, via its M2M set of
    # EmployeeKeyResult rows -- use whichever linked key result's delta is
    # found first (a Feedback spanning key results from more than one
    # objective isn't a scenario this small demo dataset produces).
    if key_result_deltas:
        for feedback in Feedback._base_manager.filter(
            employee_key_results_id__in=list(key_result_deltas)
        ).distinct():
            linked_kr_id = next(
                (
                    kr.id
                    for kr in feedback.employee_key_results_id.all()
                    if kr.id in key_result_deltas
                ),
                None,
            )
            if linked_kr_id is None:
                continue
            delta_days = key_result_deltas[linked_kr_id]
            Feedback._base_manager.filter(pk=feedback.pk).update(
                start_date=(
                    feedback.start_date + timedelta(days=delta_days)
                    if feedback.start_date
                    else None
                ),
                end_date=(
                    feedback.end_date + timedelta(days=delta_days)
                    if feedback.end_date
                    else None
                ),
            )

    logger.info(
        "PMS backfill: spread %s objective(s) over the trailing %s days",
        updated,
        TRAILING_DAYS,
    )
    return updated
