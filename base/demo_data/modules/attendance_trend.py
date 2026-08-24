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

from base.demo_data.dates import attendance_dates_for_employee

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180

MONTH_NAMES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]


@transaction.atomic
def backfill_attendance_spread(today: date | None = None) -> int:
    """
    Reassign each employee's demo Attendance rows to evenly-spaced, distinct
    dates across the trailing ~6 months ending today. Weekends are not
    skipped -- this is spread for chart purposes, not a work-calendar
    simulation. Returns the number of rows updated.

    On re-load: if attendance data exists, advance all dates by the delta
    between the max existing date and today, so stale demo data stays current.
    """
    if not apps.is_installed("attendance"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from attendance.models import Attendance, WorkRecords
    from base.models import EmployeeShiftDay

    # Check if attendance data already exists and if it's stale (from an earlier date)
    existing_max_date = (
        Attendance._base_manager.order_by("-attendance_date")
        .values_list("attendance_date", flat=True)
        .first()
    )
    if existing_max_date and existing_max_date < today:
        # Data exists but is from an earlier date; advance all records to today
        delta_days = (today - existing_max_date).days
        from django.db.models import F

        # Update all attendance records with the date delta
        update_count = Attendance._base_manager.all().update(
            attendance_date=F("attendance_date") + timedelta(days=delta_days),
            attendance_clock_in_date=F("attendance_clock_in_date")
            + timedelta(days=delta_days),
            attendance_clock_out_date=F("attendance_clock_out_date")
            + timedelta(days=delta_days),
        )

        logger.info(
            "Advanced %d stale attendance records by %d days (was up to %s, now up to %s)",
            update_count,
            delta_days,
            existing_max_date,
            today,
        )
        return update_count

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
        target_dates = attendance_dates_for_employee(
            employee_id, window_start, today, count
        )
        if not target_dates:
            continue
        plan = []
        for row, new_date in zip(emp_rows, target_dates):
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
            # Clock-out is a fact that already happened. Overnight shifts may
            # spill to the next calendar day, but never into the future, and
            # never past tomorrow relative to the attendance day.
            if new_clock_in_date and new_clock_in_date > today:
                new_clock_in_date = today
            if new_clock_out_date:
                new_clock_out_date = min(
                    new_clock_out_date,
                    today,
                    new_date + timedelta(days=1),
                )
                if new_date == today:
                    new_clock_out_date = today
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


def _trailing_month_year_pairs(today: date, count: int) -> list[tuple[str, str]]:
    """Return `count` (month_name, year) pairs for the `count` months ending
    at today's month (inclusive), oldest first."""
    pairs = []
    year, month = today.year, today.month
    for _ in range(count):
        pairs.append((MONTH_NAMES[month - 1], str(year)))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(pairs))


@transaction.atomic
def backfill_attendance_overtime(today: date | None = None) -> int:
    """
    Remap AttendanceOverTime's (month, year) buckets into the same trailing
    window backfill_attendance_spread just moved Attendance into.

    Attendance.not_validated_hrs()/not_approved_ot_hrs() filter Attendance
    by the exact (month, year) an AttendanceOverTime row names -- once the
    spread above moves every Attendance row out of the fixture's original
    months, those methods permanently return 0 for every OT row, and the
    Hour Account / OT-approval screens render empty despite having rows.
    Old bucket years are always the fixture's fixed authored year (never
    the real current year), so mapping them onto the real trailing months
    can't collide with an unprocessed old bucket mid-loop.
    """
    if not apps.is_installed("attendance"):
        return 0

    today = today or date.today()

    from attendance.models import AttendanceOverTime

    old_buckets = sorted(
        AttendanceOverTime._base_manager.values_list("month", "year").distinct(),
        key=lambda my: (int(my[1]), MONTH_NAMES.index(my[0])),
    )
    if not old_buckets:
        return 0

    new_buckets = _trailing_month_year_pairs(today, len(old_buckets))

    updated = 0
    for (old_month, old_year), (new_month, new_year) in zip(old_buckets, new_buckets):
        if (old_month, old_year) == (new_month, new_year):
            continue
        rows = AttendanceOverTime._base_manager.filter(month=old_month, year=old_year)
        count = rows.count()
        rows.update(
            month=new_month,
            year=new_year,
            month_sequence=MONTH_NAMES.index(new_month),
        )
        updated += count

    logger.info(
        "AttendanceOverTime backfill: remapped %s row(s) across %s month bucket(s)",
        updated,
        len(old_buckets),
    )
    return updated


NEW_COVERAGE_ROW_COUNT = 26  # matches the ~27 rows/employee density elsewhere
NEW_COVERAGE_CLOCK_IN = "09:00:00"
NEW_COVERAGE_CLOCK_OUT = "18:00:00"
NEW_COVERAGE_WORKED_HOUR = "09:00"
NEW_COVERAGE_MINIMUM_HOUR = "08:00"


@transaction.atomic
def backfill_zero_coverage_attendance(today: date | None = None) -> int:
    """
    Create a modest, evenly-spaced set of Attendance rows for any active
    employee who has none at all.

    backfill_attendance_spread above only *redistributes* rows that already
    exist -- an employee added after the original ~126-employee attendance
    fixture was authored (most of the largest company's headcount) has
    nothing to redistribute, so that company's attendance screens render
    mostly empty for the majority of its own staff while looking fully
    populated for smaller companies that fit inside the original range.
    """
    if not apps.is_installed("attendance"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from attendance.models import Attendance
    from base.models import EmployeeShiftDay
    from employee.models import Employee, EmployeeWorkInformation

    # Same workaround as backfill_attendance_spread: Attendance.save()'s own
    # attendance_day lookup uses .get(day=...), which raises
    # MultipleObjectsReturned if more than one EmployeeShiftDay row shares a
    # weekday name -- resolve it here and pass it in explicitly instead.
    seen_days: dict[str, int] = {}
    for row in EmployeeShiftDay.objects.all().order_by("id"):
        seen_days.setdefault(row.day, row.pk)

    covered_ids = set(
        Attendance._base_manager.values_list("employee_id", flat=True).distinct()
    )
    work_info_by_employee = {
        wi["employee_id"]: wi
        for wi in EmployeeWorkInformation._base_manager.values(
            "employee_id", "shift_id", "work_type_id"
        )
    }
    uncovered_ids = [
        emp_id
        for emp_id in Employee._base_manager.filter(is_active=True)
        .order_by("id")
        .values_list("id", flat=True)
        if emp_id not in covered_ids and emp_id in work_info_by_employee
    ]
    if not uncovered_ids:
        return 0

    created = 0
    for employee_id in uncovered_ids:
        work_info = work_info_by_employee[employee_id]
        for attendance_date in attendance_dates_for_employee(
            employee_id, window_start, today, NEW_COVERAGE_ROW_COUNT
        ):
            shift_day_pk = seen_days.get(attendance_date.strftime("%A").lower())

            Attendance._base_manager.create(
                employee_id_id=employee_id,
                attendance_date=attendance_date,
                shift_id_id=work_info.get("shift_id"),
                work_type_id_id=work_info.get("work_type_id"),
                attendance_day_id=shift_day_pk,
                attendance_clock_in_date=attendance_date,
                attendance_clock_in=NEW_COVERAGE_CLOCK_IN,
                attendance_clock_out_date=attendance_date,
                attendance_clock_out=NEW_COVERAGE_CLOCK_OUT,
                attendance_worked_hour=NEW_COVERAGE_WORKED_HOUR,
                minimum_hour=NEW_COVERAGE_MINIMUM_HOUR,
                attendance_validated=True,
            )
            created += 1

    logger.info(
        "Attendance backfill: created %s row(s) for %s previously-uncovered employee(s)",
        created,
        len(uncovered_ids),
    )
    return created


@transaction.atomic
def reconcile_attendance_with_leave(today: date | None = None) -> int:
    """Drop attendance on days an employee is already on approved leave.

    Present-today / weekly charts otherwise double-count the same person as
    both in office and on leave.
    """
    if not apps.is_installed("attendance") or not apps.is_installed("leave"):
        return 0

    from attendance.models import Attendance, WorkRecords
    from leave.models import LeaveRequest

    removed = 0
    leaves = LeaveRequest._base_manager.filter(status="approved").values(
        "id", "employee_id", "start_date", "end_date"
    )
    for leave in leaves:
        start = leave["start_date"]
        end = leave["end_date"] or start
        qs = Attendance._base_manager.filter(
            employee_id=leave["employee_id"],
            attendance_date__gte=start,
            attendance_date__lte=end,
        )
        att_ids = list(qs.values_list("id", flat=True))
        if not att_ids:
            continue
        WorkRecords._base_manager.filter(attendance_id__in=att_ids).update(
            is_attendance_record=False,
            is_leave_record=True,
            attendance_id=None,
            work_record_type="ABS",
            leave_request_id=leave["id"],
        )
        removed += qs.delete()[0]

    # Historical facts never live in the future (overnight clamp is not enough
    # if a leftover fixture row was never in the spread set).
    cap = today or date.today()
    future = Attendance._base_manager.filter(attendance_date__gt=cap)
    future_ids = list(future.values_list("id", flat=True))
    if future_ids:
        WorkRecords._base_manager.filter(attendance_id__in=future_ids).delete()
        removed += future.delete()[0]
    Attendance._base_manager.filter(attendance_clock_out_date__gt=cap).update(
        attendance_clock_out_date=cap
    )

    logger.info(
        "Attendance/leave reconcile: removed %s conflicting attendance row(s)", removed
    )
    return removed
