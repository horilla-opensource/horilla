"""Calendar helpers for time/leave metrics (expected working days)."""

from __future__ import annotations

from datetime import date, timedelta


def count_expected_working_days(
    from_date: date,
    to_date: date,
    *,
    employee=None,
) -> int:
    """
    Count expected working days in [from_date, to_date].

    Default schedule is Mon–Fri. Holidays and company leaves are subtracted via
    ``base.methods`` when available. Per-employee shift schedules are used when
    ``employee`` is provided and has a shift with day rows.
    """
    if to_date < from_date:
        return 0

    weekdays = _scheduled_weekdays(employee)
    holiday_dates = _holiday_dates(from_date, to_date, employee=employee)

    count = 0
    day = from_date
    while day <= to_date:
        if day.weekday() in weekdays and day not in holiday_dates:
            if not _is_company_leave(day):
                count += 1
        day += timedelta(days=1)
    return count


def _scheduled_weekdays(employee) -> set[int]:
    """Return Python weekday ints (0=Mon … 6=Sun). Default Mon–Fri."""
    default = {0, 1, 2, 3, 4}
    if employee is None:
        return default
    try:
        wi = getattr(employee, "employee_work_info", None)
        shift = getattr(wi, "shift_id", None) if wi else None
        if not shift:
            return default
        from base.models import EmployeeShiftSchedule

        day_names = list(
            EmployeeShiftSchedule.objects.filter(shift_id=shift).values_list(
                "day__day", flat=True
            )
        )
        if not day_names:
            return default
        mapping = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        mapped = {mapping[d.lower()] for d in day_names if d and d.lower() in mapping}
        return mapped or default
    except Exception:
        return default


def _holiday_dates(from_date: date, to_date: date, employee=None) -> set[date]:
    try:
        from base.methods import get_holiday_dates

        return set(get_holiday_dates(from_date, to_date, employee=employee) or [])
    except Exception:
        return set()


def _is_company_leave(day: date) -> bool:
    try:
        from base.methods import is_company_leave

        return bool(is_company_leave(day))
    except Exception:
        return False
