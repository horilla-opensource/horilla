"""Final A/B date clamp after the enterprise demo seeder.

A-class (historical facts): never after today.
B-class (requests / planned): pending till/end in the past gets bumped;
completed rows stay in the past. Holidays re-anchor to the current year.

Attendance future rows are deleted in reconcile_attendance_with_leave;
this pass clamps leftover fields via update() so model validators never run.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from base.demo_data.dates import holiday_on_year

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180

# Historical facts: never after today. Attendance.attendance_date is deleted
# (not clamped) so unique_together is not violated.
A_CLASS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "attendance",
        "Attendance",
        ("attendance_clock_in_date", "attendance_clock_out_date"),
    ),
    (
        "attendance",
        "AttendanceActivity",
        ("attendance_date", "clock_in_date", "clock_out_date"),
    ),
    ("attendance", "WorkRecords", ("date",)),
    ("payroll", "WorkRecord", ("date",)),
    ("project", "TimeSheet", ("date",)),
    ("helpdesk", "Ticket", ("created_date", "resolved_date")),
    ("asset", "AssetAssignment", ("assigned_date", "return_date")),
    ("onboarding", "CandidateStage", ("onboarding_end_date",)),
    ("payroll", "Contract", ("contract_start_date",)),
    ("payroll", "LoanAccount", ("provided_date", "installment_start_date")),
    ("base", "RotatingShiftAssign", ("start_date",)),
    ("base", "RotatingWorkTypeAssign", ("start_date",)),
)

A_CLASS_DATETIME: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("payroll", "LoanAccount", ("settled_date",)),
    ("payroll", "Contract", ("created_at",)),
    ("attendance", "AttendanceActivity", ("in_datetime", "out_datetime")),
)


@transaction.atomic
def clamp_demo_dates(today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    result = {
        "a_class": 0,
        "a_class_datetime": 0,
        "holidays": 0,
        "loans": 0,
        "assignments": 0,
        "rotating": 0,
        "b_class": 0,
        "payslips": 0,
        "interviews": 0,
        "exits": 0,
    }
    result["holidays"] = _reanchor_holidays(today)
    result["loans"] = _reanchor_loans(today)
    result["assignments"] = _reanchor_assignments(today)
    result["rotating"] = _reanchor_rotating(today)
    result["a_class"] = _clamp_a_class(today)
    result["a_class_datetime"] = _clamp_a_class_datetime()
    result["b_class"] = _bump_stale_pending(today)
    result["payslips"] = _demote_future_paid_payslips(today)
    result["interviews"] = _clamp_completed_interviews(today)
    result["exits"] = _clamp_completed_exits(today)
    logger.info("Demo date clamp: %s", result)
    return result


def _clamp_a_class(today: date) -> int:
    updated = 0
    for app, model, fields in A_CLASS:
        if not apps.is_installed(app):
            continue
        Model = apps.get_model(app, model)
        for field in fields:
            updated += Model._base_manager.filter(**{f"{field}__gt": today}).update(
                **{field: today}
            )
    return updated


def _clamp_a_class_datetime() -> int:
    now = timezone.now()
    updated = 0
    for app, model, fields in A_CLASS_DATETIME:
        if not apps.is_installed(app):
            continue
        Model = apps.get_model(app, model)
        for field in fields:
            updated += Model._base_manager.filter(**{f"{field}__gt": now}).update(
                **{field: now}
            )
    return updated


def _reanchor_holidays(today: date) -> int:
    if not apps.is_installed("base"):
        return 0
    from base.models import Holidays

    updated = 0
    for holiday in Holidays._base_manager.all():
        if not holiday.start_date:
            continue
        span = 0
        if holiday.end_date:
            span = (holiday.end_date - holiday.start_date).days
        new_start = holiday_on_year(holiday.start_date, today.year)
        new_end = new_start + timedelta(days=span) if holiday.end_date else None
        if new_start == holiday.start_date and new_end == holiday.end_date:
            continue
        Holidays._base_manager.filter(pk=holiday.pk).update(
            start_date=new_start, end_date=new_end
        )
        updated += 1
    return updated


def _reanchor_loans(today: date) -> int:
    if not apps.is_installed("payroll"):
        return 0
    from payroll.models.models import LoanAccount

    window_start = today - timedelta(days=TRAILING_DAYS)
    rows = list(LoanAccount._base_manager.order_by("id"))
    if not rows:
        return 0
    step = TRAILING_DAYS / max(len(rows), 1)
    updated = 0
    for i, loan in enumerate(rows):
        provided = window_start + timedelta(days=int(i * step))
        if provided > today:
            provided = today
        start = min(provided + timedelta(days=7), today)
        fields = {"provided_date": provided, "installment_start_date": start}
        if loan.settled:
            when = datetime.combine(today - timedelta(days=1), time(12, 0))
            if timezone.is_naive(when):
                try:
                    when = timezone.make_aware(when)
                except Exception:
                    pass
            fields["settled_date"] = when
        LoanAccount._base_manager.filter(pk=loan.pk).update(**fields)
        updated += 1
    return updated


def _reanchor_assignments(today: date) -> int:
    if not apps.is_installed("asset"):
        return 0
    from asset.models import AssetAssignment

    updated = 0
    for i, row in enumerate(AssetAssignment._base_manager.order_by("id")):
        assigned = today - timedelta(days=14 + (i * 7) % TRAILING_DAYS)
        fields = {"assigned_date": assigned}
        if row.return_date:
            fields["return_date"] = min(assigned + timedelta(days=21), today)
        AssetAssignment._base_manager.filter(pk=row.pk).update(**fields)
        updated += 1
    return updated


def _reanchor_rotating(today: date) -> int:
    if not apps.is_installed("base"):
        return 0
    from base.models import RotatingShiftAssign, RotatingWorkTypeAssign

    updated = 0
    for Model in (RotatingShiftAssign, RotatingWorkTypeAssign):
        for i, row in enumerate(Model._base_manager.order_by("id")):
            start = today - timedelta(days=30 + i % 60)
            nxt = today + timedelta(days=3 + i % 18)
            Model._base_manager.filter(pk=row.pk).update(
                start_date=start, next_change_date=nxt
            )
            updated += 1
    return updated


def _bump_stale_pending(today: date) -> int:
    """B-class: pending requests whose till/end already lapsed."""
    updated = 0
    if apps.is_installed("base"):
        from base.models import ShiftRequest, WorkTypeRequest

        till = today + timedelta(days=14)
        updated += ShiftRequest._base_manager.filter(
            approved=False, canceled=False, requested_till__lt=today
        ).update(requested_till=till)
        updated += WorkTypeRequest._base_manager.filter(
            approved=False, canceled=False, requested_till__lt=today
        ).update(requested_till=till)
    if apps.is_installed("leave"):
        from leave.models import LeaveRequest

        # Leave pending may start up to 21 days ago; only bump the stale tail.
        stale = today - timedelta(days=21)
        pending = LeaveRequest._base_manager.filter(
            status="requested", end_date__lt=stale
        )
        for i, req in enumerate(pending):
            start = today + timedelta(days=7 + i)
            LeaveRequest._base_manager.filter(pk=req.pk).update(
                start_date=start,
                end_date=start + timedelta(days=1),
                requested_date=today - timedelta(days=1),
            )
            updated += 1
    return updated


def _demote_future_paid_payslips(today: date) -> int:
    if not apps.is_installed("payroll"):
        return 0
    from payroll.models.models import Payslip

    return Payslip._base_manager.filter(
        status__in=("paid", "confirmed"), start_date__gt=today
    ).update(status="draft")


def _clamp_completed_interviews(today: date) -> int:
    if not apps.is_installed("recruitment"):
        return 0
    from recruitment.models import InterviewSchedule

    return InterviewSchedule._base_manager.filter(
        completed=True, interview_date__gt=today
    ).update(interview_date=today)


def _clamp_completed_exits(today: date) -> int:
    if not apps.is_installed("offboarding"):
        return 0
    from offboarding.models import OffboardingEmployee, OffboardingStage

    archived = OffboardingStage._base_manager.filter(type="archived").values_list(
        "id", flat=True
    )
    return OffboardingEmployee._base_manager.filter(
        stage_id__in=archived, notice_period_ends__gt=today
    ).update(notice_period_ends=today)
