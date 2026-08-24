"""Spread demo LeaveRequest dates across a real trailing 6 months.

The fixture only ships ~49 leave requests across ~41 employees -- mostly one
each -- all within about a month and a half. That's too thin for a 6-month
trend either way, so this pads the pool with a modest set of synthetic
requests (idempotent via a marker in `description`) and then spreads the
WHOLE pool -- original and padded alike -- evenly across the trailing
window on every run. Ranking is global, not per-employee: with most
employees holding only one request, per-employee ranking would pin every
single one of them to the exact same start-of-window day instead of
spreading them out.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180
PAD_TARGET = 80
PAD_MARKER = "[Demo seed]"

# Still-"requested" rows are unactioned: realistically someone submitted
# them recently, for dates that may be imminent or still ahead -- not
# months-old and unresolved, and not confined to the past the way an
# already-actioned (approved/rejected/cancelled) request is.
PENDING_WINDOW_DAYS = 21
PENDING_LOOKAHEAD_DAYS = 14


@transaction.atomic
def backfill_leave_spread(today: date | None = None) -> int:
    """Pad thin demo leave data, then spread it across the trailing 6 months."""
    if not apps.is_installed("leave"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from leave.models import LeaveRequest

    _pad_leave_requests(today)

    rows = list(
        LeaveRequest._base_manager.order_by("id").values(
            "id", "start_date", "end_date", "status"
        )
    )
    if not rows:
        return 0

    # Ranking the whole pool together by id put every low-id pending row
    # (the original fixture's first ~16 rows are *all* "requested") at the
    # oldest end of the trailing window and made a future-dated request
    # structurally impossible (the spread never exceeds `today`). Give
    # pending rows their own short, today-straddling window instead;
    # settled (already-actioned) rows keep the original past-only spread.
    pending_rows = [r for r in rows if r["status"] == "requested"]
    settled_rows = [r for r in rows if r["status"] != "requested"]

    updated = _spread_rows(settled_rows, window_start, today)
    updated += _spread_rows(
        pending_rows,
        today - timedelta(days=PENDING_WINDOW_DAYS),
        today + timedelta(days=PENDING_LOOKAHEAD_DAYS),
    )
    updated += _pin_current_and_upcoming_leave(today)
    updated += _ensure_leave_status_mix()

    logger.info(
        "Leave backfill: spread %s row(s) over the trailing %s days",
        updated,
        TRAILING_DAYS,
    )
    return updated


def _spread_rows(rows: list[dict], window_start: date, window_end: date) -> int:
    """Evenly space `rows` (already ordered) across [window_start, window_end].

    count-1, not count: N evenly-spaced points spanning [0, step*(N-1)]
    anchors the first row at window_start and the last at exactly
    window_end, instead of falling one step short of it (which, for a
    small N, is enough to leave the most recent bucket empty).
    """
    from leave.models import LeaveRequest

    count = len(rows)
    if count == 0:
        return 0

    span_days = (window_end - window_start).days
    step = span_days / max(count - 1, 1)
    for i, row in enumerate(rows):
        new_start = window_start + timedelta(days=int(i * step))

        new_end = None
        if row["end_date"]:
            span = (row["end_date"] - row["start_date"]).days
            new_end = new_start + timedelta(days=max(span, 0))

        LeaveRequest._base_manager.filter(pk=row["id"]).update(
            start_date=new_start,
            end_date=new_end,
            requested_date=new_start - timedelta(days=2),
        )

    return count


def _pin_current_and_upcoming_leave(today: date) -> int:
    """Guarantee each company has someone on leave today and a pending future request.

    Uniform spreading can miss "today" entirely depending on row count, which
    makes the on-leave KPI and upcoming-leave widgets look empty.
    """
    from employee.models import EmployeeWorkInformation
    from leave.models import LeaveRequest

    company_employees: dict[int, list[int]] = {}
    for employee_id, company_id in EmployeeWorkInformation._base_manager.values_list(
        "employee_id", "company_id"
    ):
        if company_id:
            company_employees.setdefault(company_id, []).append(employee_id)

    updated = 0
    for company_id, employee_ids in company_employees.items():
        approved = list(
            LeaveRequest._base_manager.filter(
                status="approved", employee_id__in=employee_ids
            ).order_by("id")[:2]
        )
        for i, req in enumerate(approved):
            start = today - timedelta(days=i)
            LeaveRequest._base_manager.filter(pk=req.pk).update(
                start_date=start,
                end_date=start + timedelta(days=1),
                requested_days=2.0,
                requested_date=start - timedelta(days=3),
            )
            updated += 1

        pending = list(
            LeaveRequest._base_manager.filter(
                status="requested", employee_id__in=employee_ids
            ).order_by("-id")[:2]
        )
        for i, req in enumerate(pending):
            start = today + timedelta(days=7 + i * 7)
            LeaveRequest._base_manager.filter(pk=req.pk).update(
                start_date=start,
                end_date=start + timedelta(days=1),
                requested_days=2.0,
                requested_date=today - timedelta(days=1),
            )
            updated += 1

    return updated


def _pad_leave_requests(today: date) -> int:
    """Create synthetic leave requests up to PAD_TARGET, skipped if already seeded."""
    from base.models import Company
    from employee.models import Employee, EmployeeWorkInformation
    from leave.models import LeaveRequest, LeaveType

    existing = LeaveRequest._base_manager.filter(
        description__startswith=PAD_MARKER
    ).count()
    to_create = PAD_TARGET - existing
    if to_create <= 0:
        return 0

    # The org-wide leave trend is company-scoped by session, defaulting to
    # the lowest-id company on a fresh login -- bias padded requests toward
    # its employees first so that chart isn't thin just because the round
    # -robin pool happened to land mostly in other companies.
    default_company_id = (
        Company._base_manager.order_by("id").values_list("id", flat=True).first()
    )
    same_company_ids = set(
        EmployeeWorkInformation._base_manager.filter(
            company_id=default_company_id
        ).values_list("employee_id", flat=True)
    )
    all_active_ids = list(
        Employee._base_manager.filter(is_active=True)
        .order_by("id")
        .values_list("id", flat=True)
    )
    employee_ids = [i for i in all_active_ids if i in same_company_ids][:40] + [
        i for i in all_active_ids if i not in same_company_ids
    ][:20]
    leave_type_ids = list(LeaveType.objects.values_list("id", flat=True))
    if not employee_ids or not leave_type_ids:
        return 0

    statuses = ["approved", "approved", "requested", "rejected", "cancelled"]
    created = 0
    for i in range(to_create):
        idx = existing + i
        employee_id = employee_ids[idx % len(employee_ids)]
        leave_type_id = leave_type_ids[idx % len(leave_type_ids)]
        span_days = (idx % 3) + 1
        start = today - timedelta(days=(idx * 5) % 170)
        end = start + timedelta(days=span_days - 1)
        LeaveRequest._base_manager.create(
            employee_id_id=employee_id,
            leave_type_id_id=leave_type_id,
            start_date=start,
            end_date=end,
            requested_days=float(span_days),
            status=statuses[idx % len(statuses)],
            description=f"{PAD_MARKER} #{idx} auto-generated demo leave request.",
            created_by_id=employee_id,
        )
        created += 1

    logger.info("Leave backfill: created %s padding leave request(s)", created)
    return created


def _ensure_leave_status_mix() -> int:
    """Guarantee cancelled rows exist even when padding was already at target."""
    from leave.models import LeaveRequest

    if LeaveRequest._base_manager.filter(status="cancelled").exists():
        return 0
    ids = list(
        LeaveRequest._base_manager.filter(status="rejected")
        .order_by("id")
        .values_list("id", flat=True)[:3]
    )
    if not ids:
        return 0
    return LeaveRequest._base_manager.filter(pk__in=ids).update(status="cancelled")


# The original fixture's ~126 employees all carry exactly these two leave
# types, at these totals -- matched here for the previously-uncovered set.
NEW_COVERAGE_LEAVE_TYPES = {2: 12.0, 3: 10.0}  # {leave_type_id: total_leave_days}


@transaction.atomic
def backfill_zero_coverage_available_leave(today: date | None = None) -> int:
    """
    Give any active employee with zero AvailableLeave rows the same
    Casual/Sick leave types every other employee already has.

    LeaveRequest.clean() hard-requires an AvailableLeave row before a leave
    type can be requested at all -- an employee with none literally cannot
    apply for leave in the demo, which is the case for most of the largest
    company's staff (the fixture's leave data was authored against the same
    ~126-employee universe attendance was).
    """
    if not apps.is_installed("leave"):
        return 0

    today = today or date.today()

    from employee.models import Employee
    from leave.models import AvailableLeave

    covered_ids = set(
        AvailableLeave._base_manager.values_list("employee_id", flat=True).distinct()
    )
    uncovered_ids = list(
        Employee._base_manager.filter(is_active=True)
        .exclude(pk__in=covered_ids)
        .order_by("id")
        .values_list("id", flat=True)
    )
    if not uncovered_ids:
        return 0

    reset_date = date(today.year, 1, 1)
    created = 0
    for employee_id in uncovered_ids:
        for leave_type_id, total_days in NEW_COVERAGE_LEAVE_TYPES.items():
            AvailableLeave._base_manager.get_or_create(
                employee_id_id=employee_id,
                leave_type_id_id=leave_type_id,
                defaults={
                    "available_days": total_days,
                    "carryforward_days": 0.0,
                    "total_leave_days": total_days,
                    "assigned_date": today,
                    "reset_date": reset_date,
                },
            )
            created += 1

    logger.info(
        "Leave backfill: created AvailableLeave rows for %s previously-uncovered employee(s)",
        len(uncovered_ids),
    )
    return created
