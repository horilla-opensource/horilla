"""Spread demo Attendance dates across a real trailing 6 months.

Fixture attendance rows ship clustered in a single few-week window. That's
fine for a snapshot list view, but any trailing-6-month chart (absenteeism,
weekly attendance) renders mostly-empty bars for the other five months. This
redistributes each employee's existing rows evenly across the window instead
of creating new ones, since there's already ample volume (~27 rows/employee).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180


@transaction.atomic
def backfill_attendance_spread(today: date | None = None) -> int:
    """
    Reassign each employee's demo Attendance rows to evenly-spaced, distinct
    dates across the trailing ~6 months ending today. Weekends are not
    skipped -- this is spread for chart purposes, not a work-calendar
    simulation. Returns the number of rows updated.
    """
    if not apps.is_installed("attendance"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from attendance.models import Attendance, WorkRecords
    from base.models import EmployeeShiftDay

    # Keep only the first row seen per weekday name -- Attendance.save()'s
    # own lookup uses .get(day=...), i.e. it assumes one canonical row per
    # weekday; mirror that instead of introducing new ambiguity.
    seen_days: dict[str, int] = {}
    for row in EmployeeShiftDay.objects.all().order_by("id"):
        seen_days.setdefault(row.day, row.pk)

    rows = list(
        Attendance._base_manager.order_by("employee_id", "attendance_date").values(
            "id",
            "employee_id",
            "attendance_date",
            "attendance_clock_in_date",
            "attendance_clock_out_date",
        )
    )
    by_employee: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_employee[row["employee_id"]].append(row)

    updated = 0
    for employee_id, emp_rows in by_employee.items():
        count = len(emp_rows)
        if count == 0:
            continue
        # count-1, not count: with N points evenly spaced by TRAILING_DAYS/N,
        # the last one always falls one step short of "today" -- for a
        # low-density employee that gap can swallow the whole current month.
        # Dividing by (count-1) instead anchors point 0 at window_start and
        # the last point exactly at today.
        step = TRAILING_DAYS / max(count - 1, 1)
        last_assigned: date | None = None
        plan = []
        for rank, row in enumerate(emp_rows):
            candidate = window_start + timedelta(days=int(rank * step))
            if last_assigned is not None and candidate <= last_assigned:
                candidate = last_assigned + timedelta(days=1)
            if candidate > today:
                candidate = today
            new_date = candidate
            last_assigned = new_date

            old_date = row["attendance_date"]
            delta_days = (new_date - old_date).days

            new_clock_in_date = (
                row["attendance_clock_in_date"] + timedelta(days=delta_days)
                if row["attendance_clock_in_date"]
                else None
            )
            new_clock_out_date = (
                row["attendance_clock_out_date"] + timedelta(days=delta_days)
                if row["attendance_clock_out_date"]
                else None
            )
            new_shift_day_pk = seen_days.get(new_date.strftime("%A").lower())

            plan.append(
                {
                    "id": row["id"],
                    "old_date": old_date,
                    "new_date": new_date,
                    "attendance_clock_in_date": new_clock_in_date,
                    "attendance_clock_out_date": new_clock_out_date,
                    "attendance_day_id": new_shift_day_pk,
                    # Placeholder keyed by this Attendance row's own pk, far
                    # outside any real date range -- guaranteed unique across
                    # this employee's rows (distinct pks) and never collides
                    # with a real target date.
                    "placeholder": date(1970, 1, 1) + timedelta(days=row["id"]),
                }
            )

        # Phase 1: park every row of this employee at its placeholder date.
        # Freshly-loaded fixture dates (already shifted near "today") and the
        # trailing-180-day target window overlap heavily, so assigning real
        # dates one row at a time regularly lands on some *other* row's
        # still-unprocessed current date -- violating the (employee, date)
        # uniqueness Attendance and WorkRecords both enforce. Vacating every
        # row from the real date range first removes that possibility.
        for item in plan:
            Attendance._base_manager.filter(pk=item["id"]).update(
                attendance_date=item["placeholder"]
            )
            WorkRecords.objects.filter(
                employee_id=employee_id, date=item["old_date"]
            ).update(date=item["placeholder"])

        # Phase 2: move every row from its placeholder to the real target
        # date. Every target date in `plan` is distinct by construction, but
        # WorkRecords isn't 1:1 with Attendance -- some employees have more
        # WorkRecords rows than Attendance rows (leave/holiday/absence days
        # also get a WorkRecords entry with no Attendance row behind them),
        # so a target date can already have its own unrelated WorkRecords
        # row. Drop the now-redundant placeholder one rather than clobber
        # whatever already legitimately represents that day.
        for item in plan:
            update_fields = {
                "attendance_date": item["new_date"],
                "attendance_clock_in_date": item["attendance_clock_in_date"],
                "attendance_clock_out_date": item["attendance_clock_out_date"],
            }
            if item["attendance_day_id"]:
                update_fields["attendance_day_id"] = item["attendance_day_id"]

            Attendance._base_manager.filter(pk=item["id"]).update(**update_fields)

            if WorkRecords.objects.filter(
                employee_id=employee_id, date=item["new_date"]
            ).exists():
                WorkRecords.objects.filter(
                    employee_id=employee_id, date=item["placeholder"]
                ).delete()
            else:
                WorkRecords.objects.filter(
                    employee_id=employee_id, date=item["placeholder"]
                ).update(date=item["new_date"])

            updated += 1

    logger.info(
        "Attendance backfill: spread %s row(s) across %s employee(s) over the trailing %s days",
        updated,
        len(by_employee),
        TRAILING_DAYS,
    )
    return updated
