"""
clock_in_out.py

Endpoints & helpers for check-in / check-out in single-session mode:

- One Attendance + one AttendanceActivity per (employee, attendance_date)
- Grace time resolution: schedule -> shift -> default
- Cutoff check-in: block after cutoff
- Cutoff check-out: block after cutoff (must submit request)
- Check-out is allowed even if check-in is missing (creates an incomplete skeleton);
  check-in can be fixed later via Attendance Request.

Hybrid-mode extensions (used by mobile/biometric integrations):
- Persist IN/OUT mode (wfo/wfa/on_duty) when fields exist on models.
- Persist IN/OUT location payload (JSON) when fields exist on models.
- Link attendance/activity to a WorkModeRequest when provided.
- Support presence-only punches (On Duty) without hour/overtime calculation.
- Support optional "no update" behavior for check-out (On Duty).
"""

import ipaddress
import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext_lazy as _

from employee.models import EmployeeWorkInformation

from attendance.methods.utils import (
    employee_exists,
    format_time,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    GraceTime,
)
from attendance.views.views import attendance_validate
from attendance.services.attendance_window_rules import (
    WindowConfig,
    compute_checkin_window,
    compute_checkout_window_wfo_wfa,
)
from base.context_processors import (
    enable_late_come_early_out_tracking,
    timerunner_enabled,
)
from base.models import AttendanceAllowedIP, Company, EmployeeShiftDay, EmployeeShiftSchedule
from horilla.decorators import hx_request_required, login_required

logger = logging.getLogger(__name__)

# Optional (hybrid) models/choices – keep imports safe across versions.
try:
    from attendance.models import AttendanceWorkMode, WorkModeRequest  # type: ignore
except Exception:  # pragma: no cover
    AttendanceWorkMode = None  # type: ignore
    WorkModeRequest = None  # type: ignore


# ---------------------------------------------------------------------
# Helpers: time, schedule, cutoff, grace time
# ---------------------------------------------------------------------
def _now_local() -> datetime:
    """Return current datetime for business rules (local time when USE_TZ=True)."""
    if getattr(settings, "USE_TZ", False):
        return dj_timezone.localtime(dj_timezone.now())
    return datetime.now()


def _ensure_local(dt: datetime) -> datetime:
    """
    Normalize dt to the project's local business time:
    - USE_TZ=True  -> tz-aware local time
    - USE_TZ=False -> tz-naive local time
    """
    if getattr(settings, "USE_TZ", False):
        if dj_timezone.is_naive(dt):
            dt = dj_timezone.make_aware(dt, dj_timezone.get_current_timezone())
        return dj_timezone.localtime(dt)

    # USE_TZ=False
    if dj_timezone.is_aware(dt):
        dt = dj_timezone.make_naive(dt, dj_timezone.get_current_timezone())
    return dt


def _get_request_datetime(request=None) -> datetime:
    """
    Return a datetime to use for attendance rules.

    If request.datetime exists (biometric/mobile injection), use it; else use server local now.
    """
    injected = getattr(request, "datetime", None) if request is not None else None
    if injected:
        return _ensure_local(injected)
    return _now_local()


def _combine_local_datetime(d: date, t: time) -> datetime:
    """Combine date+time into a datetime consistent with USE_TZ setting."""
    dt = datetime.combine(d, t)
    return _ensure_local(dt) if getattr(settings, "USE_TZ", False) else dt


def _get_schedule(shift, day):
    """Return EmployeeShiftSchedule for the given shift and day."""
    return EmployeeShiftSchedule.objects.filter(shift_id=shift, day=day).first()


def _resolve_grace_time(schedule, shift):
    """
    Resolve grace time in priority order:
    1) schedule.grace_time_id (day-level override)
    2) shift.grace_time_id
    3) default GraceTime (is_default=True)
    """
    if schedule and getattr(schedule, "grace_time_id", None) and schedule.grace_time_id.is_active:
        return schedule.grace_time_id
    if shift and getattr(shift, "grace_time_id", None) and shift.grace_time_id.is_active:
        return shift.grace_time_id
    return GraceTime.objects.filter(is_default=True, is_active=True).first()


def _resolve_window_config(schedule) -> WindowConfig:
    """Resolve window config from schedule with safe defaults.

    The schedule model may not have the new fields in older deployments,
    so we probe attributes and fall back to defaults.
    """

    def _get_int(name: str, default: int) -> int:
        try:
            val = getattr(schedule, name, None) if schedule is not None else None
            if val is None:
                return int(default)
            v = int(val)
            return v if v >= 0 else int(default)
        except Exception:
            return int(default)

    return WindowConfig(
        early_checkin_minutes=_get_int("early_checkin_minutes", 120),
        late_checkin_minutes=_get_int("late_checkin_minutes", 120),
        early_checkout_grace_minutes=_get_int("early_checkout_grace_minutes", 0),
        max_late_checkout_hours=_get_int("max_late_checkout_hours", 12),
    )


def _compute_shift_datetimes(
    *,
    attendance_date: date,
    start_time: Optional[time],
    end_time: Optional[time],
    is_night_shift: bool,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Return (shift_start_dt, shift_end_dt) in local business time."""
    if not start_time:
        return None, None

    shift_start_dt = _combine_local_datetime(attendance_date, start_time)

    if not end_time:
        return shift_start_dt, None

    end_date = attendance_date + timedelta(days=1) if is_night_shift else attendance_date
    shift_end_dt = _combine_local_datetime(end_date, end_time)
    return shift_start_dt, shift_end_dt


def _has_model_field(model_cls, field_name: str) -> bool:
    try:
        model_cls._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _time_like_to_hhmm(time_like) -> Optional[str]:
    """Accept TimeField, datetime, or string ("HH:MM" / "HH:MM:SS") and return "HH:MM"."""
    if not time_like:
        return None

    if hasattr(time_like, "strftime"):
        return time_like.strftime("%H:%M")

    if isinstance(time_like, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(time_like, fmt).strftime("%H:%M")
            except ValueError:
                continue
        return None

    return None


def _seconds_to_time(seconds: Optional[int]) -> Optional[time]:
    if seconds is None:
        return None
    try:
        sec = int(seconds) % 86400
    except Exception:
        return None
    hh = sec // 3600
    mm = (sec % 3600) // 60
    ss = sec % 60
    return time(hour=hh, minute=mm, second=ss)


def _parse_time(value: Any) -> Optional[time]:
    """Parse a TimeField-like value into datetime.time."""
    if not value:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, int):
        return _seconds_to_time(value)
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return None


def _get_schedule_time(schedule, *field_candidates: str) -> Optional[time]:
    """Try multiple attribute names on schedule and parse as time."""
    if not schedule:
        return None
    for name in field_candidates:
        if hasattr(schedule, name):
            t = _parse_time(getattr(schedule, name))
            if t:
                return t
    return None


def _calc_cutoff_in_dt(
    attendance_date: date,
    schedule,
    shift,
    start_time_sec: Optional[int] = None,
) -> Optional[datetime]:
    """
    Return the last allowed datetime for clock-in.

    Priority:
    1) Absolute cutoff time fields on schedule (if present):
         - schedule.cutoff_in_time / schedule.check_in_cutoff_time / schedule.cutoff_in
    2) Offset fields on schedule (Horilla v2 style):
         - schedule.cutoff_check_in_offset_secs (preferred)
         - schedule.cutoff_check_in_offset (HH:MM:SS)
       Cutoff = start_time + offset
    3) Fallback: start_time + grace_time (schedule->shift->default)
    4) Fallback: start_time_sec + grace_time (if schedule.start_time not available)

    Notes:
    - Offset-based cutoff is independent of grace time.
    """
    # 1) Absolute cutoff (time-of-day)
    cutoff_in_time = _get_schedule_time(schedule, "cutoff_in_time", "check_in_cutoff_time", "cutoff_in")
    if cutoff_in_time:
        return _combine_local_datetime(attendance_date, cutoff_in_time)

    # Resolve start_time (needed for offset/grace)
    start_time = _get_schedule_time(schedule, "start_time", "clock_in", "check_in")
    if not start_time:
        start_time = _seconds_to_time(start_time_sec)
    if not start_time:
        return None

    base_dt = _combine_local_datetime(attendance_date, start_time)

    # 2) Offset fields (duration from start_time)
    offset_secs = None
    if schedule is not None:
        offset_secs = getattr(schedule, "cutoff_check_in_offset_secs", None)
        if offset_secs is None:
            off_str = getattr(schedule, "cutoff_check_in_offset", None)
            if off_str:
                try:
                    hh, mm, ss = [int(x) for x in str(off_str).strip().split(":")]
                    offset_secs = hh * 3600 + mm * 60 + ss
                except Exception:
                    offset_secs = None

    if offset_secs is not None:
        try:
            return base_dt + timedelta(seconds=int(offset_secs))
        except Exception:
            pass

    # 3) Fallback: grace time
    grace = _resolve_grace_time(schedule, shift)
    grace_secs = int(grace.allowed_time_in_secs) if (grace and grace.allowed_clock_in) else 0
    return base_dt + timedelta(seconds=grace_secs)

def _calc_cutoff_out_dt(
    attendance_date: date,
    schedule,
    shift,
    end_time_sec: Optional[int] = None,
    is_night_shift: bool = False,
) -> Optional[datetime]:
    """
    Return the last allowed datetime for clock-out.

    This project uses offset-based cutoff rules only:
        Cutoff = end_time (+1 day if night shift) + offset

    Supported offset fields on schedule (Horilla v2 style):
        - schedule.cutoff_check_out_offset_secs (preferred, int seconds)
        - schedule.cutoff_check_out_offset (HH:MM:SS)

    Fallback:
        - If no offset is configured, cutoff defaults to end_time (+1 day if night shift).
        - If end_time is not available on schedule, `end_time_sec` is used.
    """
    # Base time: end_time (time-of-day)
    end_time = _get_schedule_time(schedule, "end_time", "clock_out", "check_out")
    if not end_time:
        end_time = _seconds_to_time(end_time_sec)
    if not end_time:
        return None

    out_dt = _combine_local_datetime(attendance_date, end_time)

    # Night shifts end on the next calendar day.
    if is_night_shift:
        out_dt = out_dt + timedelta(days=1)

    # Offset fields (duration from end_time)
    offset_secs = None
    if schedule is not None:
        offset_secs = getattr(schedule, "cutoff_check_out_offset_secs", None)
        if offset_secs is None:
            off_str = getattr(schedule, "cutoff_check_out_offset", None)
            if off_str:
                try:
                    hh, mm, ss = [int(x) for x in str(off_str).strip().split(":")]
                    offset_secs = hh * 3600 + mm * 60 + ss
                except Exception:
                    offset_secs = None

    if offset_secs is not None:
        try:
            out_dt = out_dt + timedelta(seconds=int(offset_secs))
        except Exception:
            pass

    return out_dt

# ---------------------------------------------------------------------
# Late come / Early out tracking (grace time schedule-level)
# ---------------------------------------------------------------------
def late_come_create(attendance):
    obj = AttendanceLateComeEarlyOut.objects.filter(type="late_come", attendance_id=attendance).first()
    if not obj:
        obj = AttendanceLateComeEarlyOut()
    obj.type = "late_come"
    obj.attendance_id = attendance
    obj.employee_id = attendance.employee_id
    obj.save()
    return obj


def late_come(attendance, start_time, end_time, shift, schedule=None):
    """Mark late check-in using grace time resolution: schedule -> shift -> default."""
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return
    if getattr(attendance, "is_presensi_only", False):
        return

    hhmm = _time_like_to_hhmm(attendance.attendance_clock_in)
    if not hhmm:
        return

    now_sec = strtime_seconds(hhmm)
    mid_day_sec = strtime_seconds("12:00")

    grace_time = _resolve_grace_time(schedule, shift)
    if grace_time and grace_time.allowed_clock_in:
        now_sec -= grace_time.allowed_time_in_secs

    # Night shift logic
    if start_time > end_time and start_time != end_time:
        if now_sec < mid_day_sec:
            late_come_create(attendance)
        elif now_sec > start_time:
            late_come_create(attendance)
    elif start_time < now_sec:
        late_come_create(attendance)

    return True


def early_out_create(attendance):
    obj = AttendanceLateComeEarlyOut.objects.filter(type="early_out", attendance_id=attendance).first()
    if not obj:
        obj = AttendanceLateComeEarlyOut()
    obj.type = "early_out"
    obj.attendance_id = attendance
    obj.employee_id = attendance.employee_id
    obj.save()
    return obj


def early_out(attendance, start_time, end_time, shift, schedule=None):
    """Mark early check-out using grace time resolution: schedule -> shift -> default."""
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return
    if getattr(attendance, "is_presensi_only", False):
        return

    hhmm = _time_like_to_hhmm(attendance.attendance_clock_out)
    if not hhmm:
        return

    now_sec = strtime_seconds(hhmm)
    mid_day_sec = strtime_seconds("12:00")

    grace_time = _resolve_grace_time(schedule, shift)
    if grace_time and grace_time.allowed_clock_out:
        now_sec += grace_time.allowed_time_in_secs

    # Existing Horilla logic
    if start_time > end_time:
        # Night shift
        if now_sec < mid_day_sec:
            if now_sec < end_time:
                early_out_create(attendance)
        else:
            early_out_create(attendance)
        return

    if end_time > now_sec:
        early_out_create(attendance)

    return



def get_shift_rules(
    attendance_date: date,
    shift,
    day=None,
    *,
    start_time_sec: Optional[int] = None,
    end_time_sec: Optional[int] = None,
) -> dict:
    """
    Public helper to compute shift-related rules for a given attendance date.

    Returns a dict with:
      - schedule: EmployeeShiftSchedule | None
      - start_time: datetime.time | None
      - end_time: datetime.time | None
      - grace_seconds: int  (check-in grace in seconds; 0 if not applicable)
      - cutoff_in_dt: datetime | None (legacy: last allowed check-in time)
      - cutoff_out_dt: datetime | None (legacy: last allowed check-out time)
      - is_night_shift: bool
      - shift_start_dt / shift_end_dt: datetime | None
      - check_in_window_start_dt / check_in_window_end_dt: datetime | None
      - check_out_window_start_dt / check_out_window_end_dt: datetime | None
      - window_config: dict (minutes/hours used)
    """
    schedule = None
    try:
        schedule = _get_schedule(shift, day) if (shift and day) else None
    except Exception:
        schedule = None

    # Resolve start/end times for display (best-effort).
    start_time = _get_schedule_time(schedule, "start_time", "clock_in", "check_in", "start")
    if not start_time:
        start_time = _seconds_to_time(start_time_sec)

    end_time = _get_schedule_time(schedule, "end_time", "clock_out", "check_out", "end")
    if not end_time:
        end_time = _seconds_to_time(end_time_sec)

    # Grace time (for check-in)
    grace = _resolve_grace_time(schedule, shift)
    grace_seconds = int(grace.allowed_time_in_secs) if (grace and getattr(grace, "allowed_clock_in", False)) else 0

    # Night shift detection:
    # - Prefer explicit schedule flag when available.
    # - Fallback to start/end comparison (supports legacy schedules without `is_night_shift`).
    is_night_shift = False
    try:
        if start_time and end_time and start_time != end_time and start_time > end_time:
            is_night_shift = True
        elif (
            start_time_sec is not None
            and end_time_sec is not None
            and start_time_sec != end_time_sec
            and start_time_sec > end_time_sec
        ):
            is_night_shift = True
    except Exception:
        is_night_shift = False

    if schedule and bool(getattr(schedule, "is_night_shift", False)):
        is_night_shift = True

    cutoff_in_dt = None
    cutoff_out_dt = None
    try:
        cutoff_in_dt = _calc_cutoff_in_dt(
            attendance_date,
            schedule,
            shift,
            start_time_sec=start_time_sec,
        )
    except Exception:
        cutoff_in_dt = None

    try:
        cutoff_out_dt = _calc_cutoff_out_dt(
            attendance_date,
            schedule,
            shift,
            end_time_sec=end_time_sec,
            is_night_shift=is_night_shift,
        )
    except Exception:
        cutoff_out_dt = None

    # Window config (FINAL spec)
    window_cfg = _resolve_window_config(schedule)
    shift_start_dt, shift_end_dt = _compute_shift_datetimes(
        attendance_date=attendance_date,
        start_time=start_time,
        end_time=end_time,
        is_night_shift=is_night_shift,
    )

    check_in_window_start_dt, check_in_window_end_dt = compute_checkin_window(
        shift_start_dt=shift_start_dt,
        cutoff_in_dt=cutoff_in_dt,
        cfg=window_cfg,
    )

    check_out_window_start_dt, check_out_window_end_dt = compute_checkout_window_wfo_wfa(
        shift_end_dt=shift_end_dt,
        cutoff_out_dt=cutoff_out_dt,
        cfg=window_cfg,
    )

    return {
        "schedule": schedule,
        "start_time": start_time,
        "end_time": end_time,
        "grace_seconds": grace_seconds,
        "cutoff_in_dt": cutoff_in_dt,
        "cutoff_out_dt": cutoff_out_dt,
        "is_night_shift": is_night_shift,

        # Shift dt + windows (FINAL spec)
        "shift_start_dt": shift_start_dt,
        "shift_end_dt": shift_end_dt,
        "check_in_window_start_dt": check_in_window_start_dt,
        "check_in_window_end_dt": check_in_window_end_dt,
        "check_out_window_start_dt": check_out_window_start_dt,
        "check_out_window_end_dt": check_out_window_end_dt,
        "window_config": {
            "early_checkin_minutes": window_cfg.early_checkin_minutes,
            "late_checkin_minutes": window_cfg.late_checkin_minutes,
            "early_checkout_grace_minutes": window_cfg.early_checkout_grace_minutes,
            "max_late_checkout_hours": window_cfg.max_late_checkout_hours,
        },
    }



# ---------------------------------------------------------------------
# Core DB writers (used by API + web)
# ---------------------------------------------------------------------
@transaction.atomic
def clock_in_attendance_and_activity(
    employee,
    date_today: date,
    attendance_date: date,
    day,
    now_hhmm: str,
    shift,
    minimum_hour: str,
    start_time_sec: int,
    end_time_sec: int,
    in_datetime: datetime,
    *,
    clock_in_image=None,
    clock_in_mode: Optional[str] = None,
    clock_in_location: Optional[dict] = None,
    work_mode_request=None,
    is_presensi_only: bool = False,
):
    """
    Single-session mode:
    - Create ONE AttendanceActivity per (employee, attendance_date).
    - If already exists, do NOT create a new one (no-op).
    - Attendance summary remains one per (employee, attendance_date).

    Hybrid additions:
    - Persist mode/location/request if model fields exist.
    - Presence-only (On Duty) sets is_presensi_only and keeps hours 00:00.
    """
    in_datetime = _ensure_local(in_datetime) if getattr(settings, "USE_TZ", False) else in_datetime

    # 1) AttendanceActivity: create once
    activity, created = AttendanceActivity.objects.get_or_create(
        employee_id=employee,
        attendance_date=attendance_date,
        defaults={
            "clock_in_date": date_today,
            "shift_day": day,
            "clock_in": in_datetime.time(),
            "in_datetime": in_datetime,
            "clock_in_image": clock_in_image,
        },
    )

    # Patch activity (keep original check-in; store metadata if missing / new)
    act_updates = []
    if getattr(activity, "shift_day_id", None) != day.id:
        activity.shift_day = day
        act_updates.append("shift_day")
    if clock_in_image and not getattr(activity, "clock_in_image", None):
        activity.clock_in_image = clock_in_image
        act_updates.append("clock_in_image")

    if clock_in_mode and _has_model_field(AttendanceActivity, "clock_in_mode"):
        if getattr(activity, "clock_in_mode", None) != clock_in_mode:
            activity.clock_in_mode = clock_in_mode
            act_updates.append("clock_in_mode")
    if clock_in_location is not None and _has_model_field(AttendanceActivity, "clock_in_location"):
        activity.clock_in_location = clock_in_location
        act_updates.append("clock_in_location")
    if work_mode_request is not None and _has_model_field(AttendanceActivity, "work_mode_request_id"):
        activity.work_mode_request_id = work_mode_request
        act_updates.append("work_mode_request_id")

    if act_updates:
        activity.save(update_fields=list(dict.fromkeys(act_updates)))  # de-dup

    # 2) Attendance summary: create once
    attendance_defaults = {
        "shift_id": shift,
        "work_type_id": employee.employee_work_info.work_type_id,
        "attendance_day": day,
        "attendance_clock_in": now_hhmm,
        "attendance_clock_in_date": date_today,
        "minimum_hour": minimum_hour,
        "attendance_clock_in_image": clock_in_image if clock_in_image else None,
    }

    if is_presensi_only and _has_model_field(Attendance, "is_presensi_only"):
        attendance_defaults["is_presensi_only"] = True  # type: ignore

    attendance, attendance_created = Attendance.objects.get_or_create(
        employee_id=employee,
        attendance_date=attendance_date,
        defaults=attendance_defaults,
    )

    # Dynamic earliest checkout (WFO/WFA): follow actual check-in time (clamped) instead of static shift_end.
    # Window END stays governed by cutoff_out elsewhere; here we only compute the earliest allowed OUT time.
    if not is_presensi_only:
        try:
            clock_in_t2 = getattr(attendance, "attendance_clock_in", None)
            in_date2 = getattr(attendance, "attendance_clock_in_date", None) or attendance_date
            shift_end_dt = rules.get("shift_end_dt")
            if clock_in_t2 and shift_start_dt and shift_end_dt:
                in_dt2 = _combine_local_datetime(in_date2, clock_in_t2)

                grace_sec = int(rules.get("grace_seconds") or 0)
                min_start = shift_start_dt
                max_start = shift_start_dt + timedelta(seconds=grace_sec)

                eff_in = in_dt2
                if eff_in < min_start:
                    eff_in = min_start
                elif grace_sec > 0 and eff_in > max_start:
                    eff_in = max_start

                shift_duration = shift_end_dt - shift_start_dt
                dyn_end = eff_in + shift_duration

                early_grace_min = int(((rules.get("window_config") or {}).get("early_checkout_grace_minutes")) or 0)
                earliest_checkout_dt = dyn_end - timedelta(minutes=early_grace_min)
        except Exception:
            pass

    # Self-healing / metadata update (DO NOT overwrite check-in time/date)
    att_updates = []
    if not attendance.attendance_day_id or attendance.attendance_day_id != day.id:
        attendance.attendance_day = day
        att_updates.append("attendance_day")
    if attendance.shift_id_id != (shift.id if shift else None):
        attendance.shift_id = shift
        att_updates.append("shift_id")
    if attendance.minimum_hour != minimum_hour:
        attendance.minimum_hour = minimum_hour
        att_updates.append("minimum_hour")
    if not attendance.work_type_id:
        attendance.work_type_id = employee.employee_work_info.work_type_id
        att_updates.append("work_type_id")
    if clock_in_image and not getattr(attendance, "attendance_clock_in_image", None):
        attendance.attendance_clock_in_image = clock_in_image
        att_updates.append("attendance_clock_in_image")

    if clock_in_mode and _has_model_field(Attendance, "attendance_clock_in_mode"):
        if getattr(attendance, "attendance_clock_in_mode", None) != clock_in_mode:
            attendance.attendance_clock_in_mode = clock_in_mode
            att_updates.append("attendance_clock_in_mode")

    if clock_in_location is not None and _has_model_field(Attendance, "attendance_clock_in_location"):
        attendance.attendance_clock_in_location = clock_in_location
        att_updates.append("attendance_clock_in_location")

    if work_mode_request is not None and _has_model_field(Attendance, "work_mode_request_id"):
        attendance.work_mode_request_id = work_mode_request
        att_updates.append("work_mode_request_id")

    # Option B (per-punch audit)
    if work_mode_request is not None and _has_model_field(Attendance, "in_related_work_type_request_id"):
        attendance.in_related_work_type_request_id = getattr(work_mode_request, 'id', work_mode_request)
        att_updates.append("in_related_work_type_request_id")
    if _has_model_field(Attendance, "in_attendance_status"):
        attendance.in_attendance_status = 'VALID'
        att_updates.append("in_attendance_status")
    if _has_model_field(Attendance, "in_attendance_reject_reason_code"):
        attendance.in_attendance_reject_reason_code = None
        att_updates.append("in_attendance_reject_reason_code")

    if is_presensi_only and _has_model_field(Attendance, "is_presensi_only"):
        if not getattr(attendance, "is_presensi_only", False):
            attendance.is_presensi_only = True
            att_updates.append("is_presensi_only")

    if att_updates:
        attendance.save(update_fields=list(dict.fromkeys(att_updates)))  # de-dup

    # Late come only once on first Attendance creation (and not presence-only)
    if attendance_created and not getattr(attendance, "is_presensi_only", False):
        attendance = Attendance.find(attendance.id)
        schedule = _get_schedule(shift, day)
        late_come(
            attendance=attendance,
            start_time=start_time_sec,
            end_time=end_time_sec,
            shift=shift,
            schedule=schedule,
        )

    return attendance


@transaction.atomic
def clock_out_attendance_and_activity(
    employee,
    attendance_date: date,
    shift,
    minimum_hour: str,
    out_datetime: datetime,
    *,
    day=None,
    clock_out_image=None,
    clock_out_mode: Optional[str] = None,
    clock_out_location: Optional[dict] = None,
    work_mode_request=None,
    is_presensi_only: bool = False,
    allow_update_clock_out: bool = True,
    raise_if_already_clocked_out: bool = False,
):
    """
    Single-session mode:
    - Allow check-out even if check-in is missing.
    - Ensure Attendance + AttendanceActivity exist for (employee, attendance_date).
    - If check-in is missing, create placeholder: clock_in = first clock_out (duration becomes 0);
      subsequent check-outs will create duration between first and last check-out.
    - Keep the latest check-out (last punch wins) when allow_update_clock_out=True.
    - Return (attendance, missing_check_in_flag_original).
    """
    out_datetime = _ensure_local(out_datetime) if getattr(settings, "USE_TZ", False) else out_datetime

    # Ensure day exists (avoid FK null issues)
    if day is None:
        day_name = attendance_date.strftime("%A").lower()
        day = EmployeeShiftDay.objects.get(day=day_name)

    out_date = out_datetime.date()
    out_time = out_datetime.time()

    # Shift context (used for early checkout rejection + worked hours start)
    # Best-effort: when schedule missing, rules may omit window boundaries.
    start_time_sec = None
    end_time_sec = None
    try:
        _min_h, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)
    except Exception:
        start_time_sec = None
        end_time_sec = None

    try:
        rules = get_shift_rules(
            attendance_date,
            shift,
            day,
            start_time_sec=start_time_sec,
            end_time_sec=end_time_sec,
        )
    except Exception:
        rules = {}

    shift_start_dt = rules.get("shift_start_dt")
    cutoff_in_dt = rules.get("cutoff_in_dt")
    if is_presensi_only:
        # ON_DUTY: earliest check-out starts AFTER check-in cutoff (avoid overlap at exact cutoff)
        earliest_checkout_dt = (cutoff_in_dt + timedelta(minutes=1)) if cutoff_in_dt else None
    else:
        earliest_checkout_dt = rules.get("check_out_window_start_dt")

    # 1) Ensure Attendance exists (skeleton allowed)
    attendance_defaults = {
        "shift_id": shift,
        "work_type_id": employee.employee_work_info.work_type_id,
        "minimum_hour": minimum_hour,
        "attendance_day": day,
        "attendance_clock_in": None,
        "attendance_clock_in_date": None,
        "attendance_validated": False,
    }
    if is_presensi_only and _has_model_field(Attendance, "is_presensi_only"):
        attendance_defaults["is_presensi_only"] = True  # type: ignore

    attendance, _ = Attendance.objects.get_or_create(
        employee_id=employee,
        attendance_date=attendance_date,
        defaults=attendance_defaults,
    )

    # Original missing check-in (before we may fill placeholder)
    missing_check_in_original = not attendance.attendance_clock_in or not attendance.attendance_clock_in_date

    # If "no update" check-out and already checked-out -> reject/no-op
    if (
        not allow_update_clock_out
        and attendance.attendance_clock_out
        and attendance.attendance_clock_out_date
    ):
        if raise_if_already_clocked_out:
            raise ValidationError(_("Check-out already recorded for this date."))
        return attendance, missing_check_in_original

    # Sync critical fields
    updates = []
    if attendance.shift_id_id != (shift.id if shift else None):
        attendance.shift_id = shift
        updates.append("shift_id")
    if not attendance.work_type_id:
        attendance.work_type_id = employee.employee_work_info.work_type_id
        updates.append("work_type_id")
    if attendance.minimum_hour != minimum_hour:
        attendance.minimum_hour = minimum_hour
        updates.append("minimum_hour")
    if not attendance.attendance_day_id or attendance.attendance_day_id != day.id:
        attendance.attendance_day = day
        updates.append("attendance_day")

    # If missing check-in, set placeholder check-in = FIRST check-out (so later updates can compute duration)
    if missing_check_in_original and (attendance.attendance_clock_in is None or attendance.attendance_clock_in_date is None):
        attendance.attendance_clock_in_date = out_date
        attendance.attendance_clock_in = out_time
        updates.extend(["attendance_clock_in_date", "attendance_clock_in"])

    if clock_out_mode and _has_model_field(Attendance, "attendance_clock_out_mode"):
        attendance.attendance_clock_out_mode = clock_out_mode
        updates.append("attendance_clock_out_mode")
    if clock_out_location is not None and _has_model_field(Attendance, "attendance_clock_out_location"):
        attendance.attendance_clock_out_location = clock_out_location
        updates.append("attendance_clock_out_location")
    if work_mode_request is not None and _has_model_field(Attendance, "work_mode_request_id"):
        attendance.work_mode_request_id = work_mode_request
        updates.append("work_mode_request_id")

    # Option B (per-punch audit)
    if work_mode_request is not None and _has_model_field(Attendance, "out_related_work_type_request_id"):
        attendance.out_related_work_type_request_id = getattr(work_mode_request, "id", work_mode_request)
        updates.append("out_related_work_type_request_id")
    if _has_model_field(Attendance, "out_attendance_status"):
        attendance.out_attendance_status = "VALID"
        updates.append("out_attendance_status")
    if _has_model_field(Attendance, "out_attendance_reject_reason_code"):
        attendance.out_attendance_reject_reason_code = None
        updates.append("out_attendance_reject_reason_code")
    if is_presensi_only and _has_model_field(Attendance, "is_presensi_only"):
        if not getattr(attendance, "is_presensi_only", False):
            attendance.is_presensi_only = True
            updates.append("is_presensi_only")

    if updates:
        attendance.save(update_fields=list(dict.fromkeys(updates)))

    # 2) Ensure AttendanceActivity exists (clock_in NOT NULL -> placeholder if missing)
    placeholder_in_date = attendance.attendance_clock_in_date or attendance_date
    placeholder_in_time = attendance.attendance_clock_in or out_time
    placeholder_in_dt = _combine_local_datetime(placeholder_in_date, placeholder_in_time)

    activity, created = AttendanceActivity.objects.get_or_create(
        employee_id=employee,
        attendance_date=attendance_date,
        defaults={
            "shift_day": day,
            "clock_in_date": placeholder_in_date,
            "clock_in": placeholder_in_time,
            "in_datetime": placeholder_in_dt,
        },
    )

    # Patch activity placeholder if needed
    act_updates = []
    if activity.shift_day_id != day.id:
        activity.shift_day = day
        act_updates.append("shift_day")
    if not activity.clock_in_date:
        activity.clock_in_date = placeholder_in_date
        act_updates.append("clock_in_date")
    if not activity.clock_in:
        activity.clock_in = placeholder_in_time
        act_updates.append("clock_in")
    if not activity.in_datetime and activity.clock_in_date and activity.clock_in:
        activity.in_datetime = _combine_local_datetime(activity.clock_in_date, activity.clock_in)
        act_updates.append("in_datetime")

    if clock_out_mode and _has_model_field(AttendanceActivity, "clock_out_mode"):
        activity.clock_out_mode = clock_out_mode
        act_updates.append("clock_out_mode")
    if clock_out_location is not None and _has_model_field(AttendanceActivity, "clock_out_location"):
        activity.clock_out_location = clock_out_location
        act_updates.append("clock_out_location")
    if work_mode_request is not None and _has_model_field(AttendanceActivity, "work_mode_request_id"):
        activity.work_mode_request_id = work_mode_request
        act_updates.append("work_mode_request_id")

    if act_updates:
        activity.save(update_fields=list(dict.fromkeys(act_updates)))

    # 3) Last punch wins: ignore older punches (when updates allowed)
    if allow_update_clock_out:
        existing_out_dt = activity.out_datetime
        if not existing_out_dt and activity.clock_out_date and activity.clock_out:
            existing_out_dt = _combine_local_datetime(activity.clock_out_date, activity.clock_out)

        if existing_out_dt and out_datetime <= existing_out_dt:
            return attendance, missing_check_in_original
    else:
        # No update allowed: if already has activity out, ignore
        if activity.clock_out_date and activity.clock_out:
            if raise_if_already_clocked_out:
                raise ValidationError(_("Check-out already recorded for this date."))
            return attendance, missing_check_in_original

    # 4) Update activity OUT
    activity.clock_out_date = out_date
    activity.clock_out = out_time
    activity.out_datetime = out_datetime
    if clock_out_image:
        activity.clock_out_image = clock_out_image

    # Also persist mode/location on first write for safety
    if clock_out_mode and _has_model_field(AttendanceActivity, "clock_out_mode"):
        activity.clock_out_mode = clock_out_mode
    if clock_out_location is not None and _has_model_field(AttendanceActivity, "clock_out_location"):
        activity.clock_out_location = clock_out_location
    activity.save()

    # 5) Update Attendance OUT
    attendance.attendance_clock_out_date = out_date
    attendance.attendance_clock_out = out_time
    if clock_out_image:
        attendance.attendance_clock_out_image = clock_out_image

    if clock_out_mode and _has_model_field(Attendance, "attendance_clock_out_mode"):
        attendance.attendance_clock_out_mode = clock_out_mode
    if clock_out_location is not None and _has_model_field(Attendance, "attendance_clock_out_location"):
        attendance.attendance_clock_out_location = clock_out_location

    if work_mode_request is not None and _has_model_field(Attendance, "work_mode_request_id"):
        attendance.work_mode_request_id = work_mode_request

    # Option B (per-punch audit)
    if work_mode_request is not None and _has_model_field(Attendance, "out_related_work_type_request_id"):
        attendance.out_related_work_type_request_id = getattr(work_mode_request, 'id', work_mode_request)
    if _has_model_field(Attendance, "out_attendance_status"):
        attendance.out_attendance_status = 'VALID'
    if _has_model_field(Attendance, "out_attendance_reject_reason_code"):
        attendance.out_attendance_reject_reason_code = None

    # -----------------------------------------------------------------
    # EARLY CHECK-OUT REJECT (FINAL spec)
    # Store OUT for audit, but mark as REJECTED when outside the allowed window.
    # - WFO/WFA: earliest = shift_end - grace
    # - ON_DUTY: earliest = cutoff_in_dt + 1 minute
    # -----------------------------------------------------------------
    is_early_checkout = False
    try:
        if earliest_checkout_dt and out_datetime < earliest_checkout_dt:
            is_early_checkout = True
    except Exception:
        is_early_checkout = False

    if is_early_checkout:
        if _has_model_field(Attendance, "out_attendance_status"):
            attendance.out_attendance_status = 'REJECTED'
        if _has_model_field(Attendance, "out_attendance_reject_reason_code"):
            attendance.out_attendance_reject_reason_code = (
                'EARLY_CHECKOUT_BEFORE_CUTOFF_IN'
                if is_presensi_only
                else 'EARLY_CHECKOUT_BEFORE_SHIFT_END'
            )

    # Presence-only: keep hours 00:00
    if is_presensi_only or getattr(attendance, "is_presensi_only", False):
        if _has_model_field(Attendance, "is_presensi_only"):
            attendance.is_presensi_only = True
        attendance.attendance_worked_hour = "00:00"
        attendance.attendance_overtime = "00:00"
        attendance.attendance_validated = False
        attendance.save()
        return attendance, missing_check_in_original

    # If OUT is REJECTED (early checkout), do NOT compute valid worked hours.
    # Keep record for audit, but payroll/KPI should rely on VALID OUT.
    if getattr(attendance, "out_attendance_status", None) == "REJECTED":
        attendance.attendance_worked_hour = "00:00"
        attendance.attendance_overtime = "00:00"
        attendance.attendance_validated = False
        attendance.save()
        return attendance, missing_check_in_original

    # Compute worked hours from Attendance summary.
    # FINAL spec: if IN earlier than shift_start, start counting from shift_start.
    if attendance.attendance_clock_in_date and attendance.attendance_clock_in:
        in_dt = _combine_local_datetime(attendance.attendance_clock_in_date, attendance.attendance_clock_in)
        out_dt = _combine_local_datetime(attendance.attendance_clock_out_date, attendance.attendance_clock_out)

        worked_start_dt = in_dt
        try:
            if shift_start_dt:
                worked_start_dt = max(in_dt, shift_start_dt)
        except Exception:
            worked_start_dt = in_dt

        duration_seconds = int((out_dt - worked_start_dt).total_seconds())
        if duration_seconds < 0:
            duration_seconds = 0

        attendance.attendance_worked_hour = format_time(duration_seconds)
        attendance.attendance_overtime = overtime_calculation(attendance)
        attendance.attendance_validated = attendance_validate(attendance)
    else:
        attendance.attendance_worked_hour = "00:00"
        attendance.attendance_overtime = "00:00"
        attendance.attendance_validated = False

    attendance.save()
    return attendance, missing_check_in_original


# ---------------------------------------------------------------------
# Views: clock_in / clock_out (web UI only)
# ---------------------------------------------------------------------
@login_required
@hx_request_required
def clock_in(request):
    """
    Web clock-in button (HTMX).
    Note: you stated "no web attendance"; keep enable_check_in disabled to block normal users.
    """
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(company_id=None).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(company_id=company).first()

    # Check feature enabled OR injected datetime (biometric/mobile server-side call)
    if not (
        (attendance_general_settings and attendance_general_settings.enable_check_in)
        or request.__dict__.get("datetime")
        or (request.__dict__.get("date") and request.__dict__.get("time"))
    ):
        messages.error(request, _("Check in/Check out feature is not enabled."))
        return HttpResponse("<script>location.reload();</script>")

    # IP restriction (only for normal web requests)
    allowed_attendance_ips = AttendanceAllowedIP.objects.first()
    if (
        not request.__dict__.get("datetime")
        and not (request.__dict__.get("date") and request.__dict__.get("time"))
        and allowed_attendance_ips
        and allowed_attendance_ips.is_enabled
    ):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = request.META.get("REMOTE_ADDR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]

        allowed_ips = (allowed_attendance_ips.additional_data or {}).get("allowed_ips", [])
        ip_allowed = False
        for allowed_ip in allowed_ips:
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(allowed_ip, strict=False):
                    ip_allowed = True
                    break
            except ValueError:
                continue

        if not ip_allowed:
            return HttpResponse(_("You cannot mark attendance from this network"))

    employee, work_info = employee_exists(request)
    if not employee or work_info is None:
        return HttpResponse(
            _("You Don't have work information filled or your employee detail neither entered ")
        )

    # Customization: reporting managers are approver-only and must not punch attendance.
    try:
        if EmployeeWorkInformation.objects.filter(reporting_manager_id=employee).only("id").exists():
            return HttpResponse(_("Attendance is disabled for reporting managers (approver-only)."))
    except Exception:
        pass

    # Customization: reporting managers are approver-only and must not punch attendance.
    try:
        if EmployeeWorkInformation.objects.filter(reporting_manager_id=employee).only("id").exists():
            return HttpResponse(_("Attendance is disabled for reporting managers (approver-only)."))
    except Exception:
        pass

    shift = work_info.shift_id
    datetime_now = _get_request_datetime(request)
    date_today = datetime_now.date()
    now_hhmm = datetime_now.strftime("%H:%M")

    # Determine attendance_date + day (night shift rule)
    attendance_date = date_today
    day = EmployeeShiftDay.objects.get(day=date_today.strftime("%A").lower())

    now_sec = strtime_seconds(now_hhmm)
    mid_day_sec = strtime_seconds("12:00")

    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)

    is_night_shift = start_time_sec > end_time_sec and start_time_sec != end_time_sec

    # Night shift: if punch before noon, attendance belongs to yesterday
    if is_night_shift and mid_day_sec > now_sec:
        date_yesterday = date_today - timedelta(days=1)
        day = EmployeeShiftDay.objects.get(day=date_yesterday.strftime("%A").lower())
        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)
        attendance_date = date_yesterday

    # Cutoff IN enforcement
    schedule = _get_schedule(shift, day)
    cutoff_in_dt = _calc_cutoff_in_dt(attendance_date, schedule, shift, start_time_sec=start_time_sec)
    if cutoff_in_dt and datetime_now > cutoff_in_dt:
        messages.error(
            request,
            _("Check-in cut-off has passed. Last allowed: %(t)s")
            % {"t": cutoff_in_dt.strftime("%Y-%m-%d %H:%M")},
        )
        return HttpResponse(
            _("Check-in is not allowed after cut-off time (%(t)s).")
            % {"t": cutoff_in_dt.strftime("%H:%M")}
        )

    clock_in_image = getattr(request, "image", None)

    clock_in_attendance_and_activity(
        employee=employee,
        date_today=date_today,
        attendance_date=attendance_date,
        day=day,
        now_hhmm=now_hhmm,
        shift=shift,
        minimum_hour=minimum_hour,
        start_time_sec=start_time_sec,
        end_time_sec=end_time_sec,
        in_datetime=datetime_now,
        clock_in_image=clock_in_image,
        clock_in_mode=getattr(AttendanceWorkMode, "WFO", None) if AttendanceWorkMode else "wfo",
    )

    # UI response
    script = ""
    hidden_label = ""
    mouse_in = ""
    mouse_out = ""
    if timerunner_enabled(request)["enabled_timerunner"]:
        script = """
        <script>
            $(".time-runner").removeClass("stop-runner");
            run = 1;
            at_work_seconds = {at_work_seconds_forecasted};
        </script>
        """.format(
            at_work_seconds_forecasted=employee.get_forecasted_at_work()["forecasted_at_work_seconds"]
        )
        hidden_label = 'style="display:none"'
        mouse_in = """ onmouseenter="$(this).find('span').show();$(this).find('.time-runner').hide();" """
        mouse_out = """ onmouseleave="$(this).find('span').hide();$(this).find('.time-runner').show();" """

    return HttpResponse(
        """
        <button class="oh-btn oh-btn--warning-outline check-in mr-2"
            {mouse_in}
            {mouse_out}
            hx-get="/attendance/clock-out"
            hx-target='#attendance-activity-container'
            hx-swap='innerHTML'>
            <ion-icon class="oh-navbar__clock-icon mr-2 text-warning" name="exit-outline"></ion-icon>
            <span {hidden_label} class="hr-check-in-out-text">{check_out}</span>
            <div class="time-runner"></div>
        </button>
        {script}
        """.format(
            check_out=_("Check-Out"),
            script=script,
            hidden_label=hidden_label,
            mouse_in=mouse_in,
            mouse_out=mouse_out,
        )
    )


@login_required
@hx_request_required
def clock_out(request):
    """
    Web clock-out button (HTMX).
    Note: you stated "no web attendance"; keep enable_check_in disabled to block normal users.
    """
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(company_id=None).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(company_id=company).first()

    if not (
        (attendance_general_settings and attendance_general_settings.enable_check_in)
        or request.__dict__.get("datetime")
        or (request.__dict__.get("date") and request.__dict__.get("time"))
    ):
        messages.error(request, _("Check in/Check out feature is not enabled."))
        return HttpResponse("<script>location.reload();</script>")

    employee, work_info = employee_exists(request)
    if not employee or work_info is None:
        return HttpResponse(
            _("You Don't have work information filled or your employee detail neither entered ")
        )

    shift = work_info.shift_id
    datetime_now = _get_request_datetime(request)
    date_today = datetime_now.date()
    now_hhmm = datetime_now.strftime("%H:%M")

    # Determine attendance_date + day (night shift rule)
    attendance_date = date_today
    day = EmployeeShiftDay.objects.get(day=date_today.strftime("%A").lower())

    now_sec = strtime_seconds(now_hhmm)
    mid_day_sec = strtime_seconds("12:00")

    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)
    is_night_shift = start_time_sec > end_time_sec and start_time_sec != end_time_sec

    # Night shift: if punch before noon, attendance belongs to yesterday
    if is_night_shift and mid_day_sec > now_sec:
        date_yesterday = date_today - timedelta(days=1)
        day = EmployeeShiftDay.objects.get(day=date_yesterday.strftime("%A").lower())
        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(day=day, shift=shift)
        attendance_date = date_yesterday

    # Cutoff OUT enforcement (strict block)
    schedule = _get_schedule(shift, day)
    cutoff_out_dt = _calc_cutoff_out_dt(
        attendance_date,
        schedule,
        shift,
        end_time_sec=end_time_sec,
        is_night_shift=is_night_shift,
    )
    if cutoff_out_dt and datetime_now > cutoff_out_dt:
        messages.error(request, _("Check-out cut-off has passed. Please submit an attendance request."))
        return HttpResponse("<script>location.reload();</script>")

    clock_out_image = getattr(request, "image", None)

    attendance, missing_check_in = clock_out_attendance_and_activity(
        employee=employee,
        attendance_date=attendance_date,
        day=day,
        shift=shift,
        minimum_hour=minimum_hour,
        out_datetime=datetime_now,
        clock_out_image=clock_out_image,
        clock_out_mode=getattr(AttendanceWorkMode, "WFO", None) if AttendanceWorkMode else "wfo",
        allow_update_clock_out=True,
    )

    if not attendance:
        messages.error(request, _("Unable to record check-out. Please contact admin."))
        return HttpResponse("<script>location.reload();</script>")

    if missing_check_in:
        messages.warning(
            request,
            _("Check-out recorded, but check-in is missing. Please submit an attendance request later.")
        )
        # Skip early_out for incomplete attendance (missing)
    else:
        # Because check-out can be updated multiple times, always re-evaluate early_out
        attendance.late_come_early_out.filter(type="early_out").delete()

        next_date = attendance.attendance_date + timedelta(days=1)

        if is_night_shift:
            # Horilla night-shift condition (noon-to-noon)
            if (attendance.attendance_date == date_today) or (
                strtime_seconds("12:00") >= now_sec and date_today == next_date
            ):
                schedule = _get_schedule(shift, day)
                early_out(
                    attendance=attendance,
                    start_time=start_time_sec,
                    end_time=end_time_sec,
                    shift=shift,
                    schedule=schedule,
                )
        else:
            if attendance.attendance_date == date_today:
                schedule = _get_schedule(shift, day)
                early_out(
                    attendance=attendance,
                    start_time=start_time_sec,
                    end_time=end_time_sec,
                    shift=shift,
                    schedule=schedule,
                )

    # UI response
    script = ""
    hidden_label = ""
    mouse_in = ""
    mouse_out = ""

    if timerunner_enabled(request)["enabled_timerunner"]:
        script = """
        <script>
            $(document).ready(function () {{
                $('.at-work-seconds').html(secondsToDuration({at_work_seconds_forecasted}))
            }});
            run = 0;
            at_work_seconds = {at_work_seconds_forecasted};
        </script>
        """.format(
            at_work_seconds_forecasted=employee.get_forecasted_at_work()["forecasted_at_work_seconds"]
        )
        hidden_label = 'style="display:none"'
        mouse_in = """ onmouseenter="$(this).find('div.at-work-seconds').hide();$(this).find('span').show();" """
        mouse_out = """ onmouseleave="$(this).find('div.at-work-seconds').show();$(this).find('span').hide();" """

    return HttpResponse(
        """
        <button class="oh-btn oh-btn--success-outline mr-2"
            {mouse_in}
            {mouse_out}
            hx-get="/attendance/clock-in"
            hx-target='#attendance-activity-container'
            hx-swap='innerHTML'>
            <ion-icon class="oh-navbar__clock-icon mr-2 text-success" name="enter-outline"></ion-icon>
            <span class="hr-check-in-out-text" {hidden_label}>{check_in}</span>
            <div class="at-work-seconds"></div>
        </button>
        {script}
        """.format(
            check_in=_("Check-In"),
            script=script,
            hidden_label=hidden_label,
            mouse_in=mouse_in,
            mouse_out=mouse_out,
        )
    )
