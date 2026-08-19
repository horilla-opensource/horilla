"""Date helpers for demo backfill. No Django imports — keep them testable."""

from __future__ import annotations

from datetime import date, timedelta

PRESENT_TODAY_RATE = 87  # employee_id % 100 < this → checked in today


def weekdays_inclusive(start: date, end: date) -> list[date]:
    """Mon–Fri dates from start through end, inclusive."""
    if end < start:
        return []
    out: list[date] = []
    day = start
    while day <= end:
        if day.weekday() < 5:
            out.append(day)
        day += timedelta(days=1)
    return out


def previous_weekday(day: date) -> date:
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def spaced_dates(
    start: date, end: date, count: int, *, weekdays_only: bool = True
) -> list[date]:
    """`count` distinct dates in [start, end], optionally Mon–Fri only.

    Anchors the first point at the start of the pool and the last at the end
    of the pool so the current month is never left empty when `end` is today.
    """
    if count <= 0:
        return []
    pool: list[date] = []
    day = start
    while day <= end:
        if not weekdays_only or day.weekday() < 5:
            pool.append(day)
        day += timedelta(days=1)
    if not pool:
        return []
    if count >= len(pool):
        return pool[:]
    step = (len(pool) - 1) / max(count - 1, 1)
    used: set[int] = set()
    out: list[date] = []
    for i in range(count):
        idx = min(int(round(i * step)), len(pool) - 1)
        while idx in used:
            idx += 1
            if idx >= len(pool):
                idx = len(pool) - 1
                while idx in used and idx > 0:
                    idx -= 1
                break
        used.add(idx)
        out.append(pool[idx])
    return out


def should_be_present_today(
    employee_id: int, today: date, rate: int = PRESENT_TODAY_RATE
) -> bool:
    """Deterministic ~rate% of staff are present on a weekday. Nobody on weekends."""
    if today.weekday() >= 5:
        return False
    return employee_id % 100 < rate


def attendance_dates_for_employee(
    employee_id: int,
    start: date,
    today: date,
    count: int,
) -> list[date]:
    """Weekday attendance dates in the trailing window, not everyone on `today`."""
    dates = spaced_dates(start, today, count, weekdays_only=True)
    if not dates:
        return dates
    if dates[-1] == today and not should_be_present_today(employee_id, today):
        replacement = previous_weekday(today)
        existing = set(dates[:-1])
        while replacement in existing:
            replacement = previous_weekday(replacement)
        if replacement >= start:
            dates[-1] = replacement
    return dates
