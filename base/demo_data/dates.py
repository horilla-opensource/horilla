"""Date helpers for demo backfill. No Django imports — keep them testable."""

from __future__ import annotations

import re
from datetime import date, timedelta

PRESENT_TODAY_RATE = 87  # employee_id % 100 < this → checked in today

# Last attendance_date in load_data/attendance_data.json. Every fixture date
# in 2020–2030 shifts so this day becomes the load day.
FIXTURE_AS_OF = date(2025, 7, 31)
_SHIFT_MIN = date(2020, 1, 1)
_SHIFT_MAX = date(2030, 12, 31)
_DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")

# Keep the last N weekdays in the attendance set so "yesterday" exists after
# the 6-month spread (which would otherwise skip most recent days).
RECENT_ATTENDANCE_WEEKDAYS = 10

DEFAULT_WEEKDAYS = frozenset({0, 1, 2, 3, 4})  # Mon-Fri, Python weekday() ints

_WEEKDAY_NAME_TO_INT = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def scheduled_weekdays_for_shift(day_names) -> set[int]:
    """Map EmployeeShiftSchedule day names to Python weekday() ints.

    Pure (no Django import, matching this module's own constraint) -- the
    caller queries EmployeeShiftSchedule and passes the day-name strings in.
    Falls back to Mon-Fri if `day_names` is empty or nothing maps, mirroring
    report/metrics/_calendar.py's _scheduled_weekdays default.
    """
    mapped = {
        _WEEKDAY_NAME_TO_INT[d.lower()]
        for d in day_names or []
        if d and d.lower() in _WEEKDAY_NAME_TO_INT
    }
    return mapped or set(DEFAULT_WEEKDAYS)


def shift_fixture_dates_text(content: str, today: date | None = None) -> str | None:
    """Shift YYYY-MM-DD (and ISO datetime prefixes) so FIXTURE_AS_OF → today.

    Dates outside 2020–2030 (DOBs, etc.) are left alone. Returns None when
    today is the snapshot day (no rewrite needed).
    """
    today = today or date.today()
    delta = (today - FIXTURE_AS_OF).days
    if delta == 0:
        return None

    def _shift(match: re.Match[str]) -> str:
        raw = match.group(1)
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return raw
        if _SHIFT_MIN <= d <= _SHIFT_MAX:
            return (d + timedelta(days=delta)).isoformat()
        return raw

    return _DATE_RE.sub(_shift, content)


def weekdays_inclusive(
    start: date, end: date, weekdays: set[int] | None = None
) -> list[date]:
    """Scheduled-weekday dates from start through end, inclusive. Defaults to Mon-Fri."""
    weekdays = weekdays if weekdays is not None else DEFAULT_WEEKDAYS
    if end < start:
        return []
    out: list[date] = []
    day = start
    while day <= end:
        if day.weekday() in weekdays:
            out.append(day)
        day += timedelta(days=1)
    return out


def holiday_on_year(d: date, year: int) -> date:
    """Keep month/day, move to `year`. Feb 29 → Feb 28 on non-leap years."""
    try:
        return d.replace(year=year)
    except ValueError:
        return date(year, d.month, 28)


def clamp_date(d: date | None, today: date) -> date | None:
    """A-class helper: historical dates never after `today`."""
    if d is None:
        return None
    return d if d <= today else today


def previous_weekday(day: date) -> date:
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def spaced_dates(
    start: date,
    end: date,
    count: int,
    *,
    weekdays_only: bool = True,
    weekdays: set[int] | None = None,
) -> list[date]:
    """`count` distinct dates in [start, end], optionally scheduled-weekdays only.

    Anchors the first point at the start of the pool and the last at the end
    of the pool so the current month is never left empty when `end` is today.
    `weekdays` defaults to Mon-Fri when `weekdays_only` is set; pass an
    employee's actual scheduled weekday set (see scheduled_weekdays_for_shift)
    for shift-aware selection.
    """
    if count <= 0:
        return []
    allowed = (
        (weekdays if weekdays is not None else DEFAULT_WEEKDAYS)
        if weekdays_only
        else None
    )
    pool: list[date] = []
    day = start
    while day <= end:
        if allowed is None or day.weekday() in allowed:
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
    employee_id: int,
    today: date,
    rate: int = PRESENT_TODAY_RATE,
    weekdays: set[int] | None = None,
) -> bool:
    """Deterministic ~rate% of staff are present on a scheduled day. Nobody on days off."""
    allowed = weekdays if weekdays is not None else DEFAULT_WEEKDAYS
    if today.weekday() not in allowed:
        return False
    return employee_id % 100 < rate


def _recent_weekdays(
    today: date, start: date, n: int, weekdays: set[int] | None = None
) -> list[date]:
    allowed = weekdays if weekdays is not None else DEFAULT_WEEKDAYS
    end = today
    while end.weekday() not in allowed and end > start:
        end -= timedelta(days=1)
    pin: list[date] = []
    day = end
    while len(pin) < n and day >= start:
        if day.weekday() in allowed:
            pin.append(day)
        day -= timedelta(days=1)
    pin.reverse()
    return pin


def attendance_dates_for_employee(
    employee_id: int,
    start: date,
    today: date,
    count: int,
    weekdays: set[int] | None = None,
) -> list[date]:
    """Scheduled-weekday attendance dates in the trailing window, not everyone on `today`.

    The last few scheduled days are always included (except `today` for the
    ~13% who are off) so a load on Thursday still has Wednesday punches.
    `weekdays` defaults to Mon-Fri; pass an employee's actual scheduled
    weekday set (see scheduled_weekdays_for_shift) for shift-aware selection,
    e.g. a Mon-Sat shift correctly gets Saturday attendance too.
    """
    dates = spaced_dates(start, today, count, weekdays_only=True, weekdays=weekdays)
    if not dates:
        return dates
    pin = _recent_weekdays(
        today, start, min(RECENT_ATTENDANCE_WEEKDAYS, count), weekdays=weekdays
    )
    if not should_be_present_today(employee_id, today, weekdays=weekdays):
        pin = [d for d in pin if d != today]
    pin_set = set(pin)
    head = [d for d in dates if d not in pin_set]
    need = count - len(pin)
    return (head[:need] if need > 0 else []) + pin
