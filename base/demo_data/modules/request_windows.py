"""Re-date request-style demo rows so pending items sit around today / the future.

Historical events (attendance, timesheets, resolved tickets) stay in the past.
Requests that a person would file ahead of time — leave already handled in
leave_trend, plus shift/work-type/allocation/asset/interviews/meetings — get
a realistic mix of recent pending and upcoming dates.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@transaction.atomic
def backfill_request_windows(today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    result = {
        "shift_requests": 0,
        "work_type_requests": 0,
        "leave_allocations": 0,
        "asset_requests": 0,
        "interviews": 0,
        "meetings": 0,
        "timesheets_clamped": 0,
        "tickets_clamped": 0,
        "assets_expiry": 0,
        "attendance_validations": 0,
    }

    result["shift_requests"] = _shift_requests(today)
    result["work_type_requests"] = _work_type_requests(today)
    result["leave_allocations"] = _leave_allocations(today)
    result["asset_requests"] = _asset_requests(today)
    result["interviews"] = _interviews(today)
    result["meetings"] = _meetings(today)
    result["timesheets_clamped"] = _clamp_timesheets(today)
    result["tickets_clamped"] = _clamp_tickets(today)
    result["assets_expiry"] = _fix_asset_expiry(today)
    result["attendance_validations"] = _pending_attendance_validations(today)

    logger.info("Request windows backfill: %s", result)
    return result


def _shift_requests(today: date) -> int:
    if not apps.is_installed("base"):
        return 0
    from base.models import ShiftRequest

    updated = 0
    for i, req in enumerate(ShiftRequest._base_manager.order_by("id")):
        if req.canceled:
            requested = today - timedelta(days=40 + i)
            till = requested + timedelta(days=14)
        elif req.approved:
            requested = today - timedelta(days=60 + i * 7)
            till = requested + timedelta(days=21)
        else:
            requested = today - timedelta(days=2)
            till = today + timedelta(days=14 + (i % 14))
        ShiftRequest._base_manager.filter(pk=req.pk).update(
            requested_date=requested, requested_till=till
        )
        updated += 1
    return updated


def _work_type_requests(today: date) -> int:
    if not apps.is_installed("base"):
        return 0
    from base.models import WorkTypeRequest

    updated = 0
    for i, req in enumerate(WorkTypeRequest._base_manager.order_by("id")):
        if req.canceled:
            requested = today - timedelta(days=35 + i)
            till = requested + timedelta(days=10)
        elif req.approved:
            requested = today - timedelta(days=50 + i * 7)
            till = requested + timedelta(days=14)
        else:
            requested = today - timedelta(days=1)
            till = today + timedelta(days=10 + (i % 10))
        WorkTypeRequest._base_manager.filter(pk=req.pk).update(
            requested_date=requested, requested_till=till
        )
        updated += 1
    return updated


def _leave_allocations(today: date) -> int:
    if not apps.is_installed("leave"):
        return 0
    from leave.models import LeaveAllocationRequest

    updated = 0
    for i, req in enumerate(LeaveAllocationRequest._base_manager.order_by("id")):
        if req.status == "requested":
            requested = today - timedelta(days=1 + i)
        else:
            requested = today - timedelta(days=40 + i * 10)
        LeaveAllocationRequest._base_manager.filter(pk=req.pk).update(
            requested_date=requested
        )
        updated += 1
    return updated


def _asset_requests(today: date) -> int:
    if not apps.is_installed("asset"):
        return 0
    from asset.models import AssetRequest

    # auto_now_add dates go stale; bump pending rows to recently requested.
    pending = AssetRequest._base_manager.filter(asset_request_status="Requested")
    count = pending.update(asset_request_date=today - timedelta(days=2))
    AssetRequest._base_manager.filter(asset_request_status="Approved").update(
        asset_request_date=today - timedelta(days=20)
    )
    AssetRequest._base_manager.filter(asset_request_status="Rejected").update(
        asset_request_date=today - timedelta(days=12)
    )
    return count


def _interviews(today: date) -> int:
    if not apps.is_installed("recruitment"):
        return 0
    from recruitment.models import Candidate, InterviewSchedule

    updated = 0
    for i, interview in enumerate(InterviewSchedule._base_manager.order_by("id")):
        if interview.completed:
            interview_date = today - timedelta(days=14 + i)
        else:
            interview_date = today + timedelta(days=3 + i * 2)
        InterviewSchedule._base_manager.filter(pk=interview.pk).update(
            interview_date=interview_date
        )
        updated += 1

    # Upcoming interviews for candidates currently in an interview stage.
    interview_candidates = Candidate._base_manager.filter(
        stage_id__stage_type="interview", hired=False, canceled=False
    ).order_by("id")[:6]
    for i, candidate in enumerate(interview_candidates):
        exists = InterviewSchedule._base_manager.filter(
            candidate_id=candidate, completed=False
        ).exists()
        if exists:
            continue
        InterviewSchedule._base_manager.create(
            candidate_id=candidate,
            interview_date=today + timedelta(days=4 + i * 3),
            interview_time=time(10, 30),
            description="Demo interview scheduled with the hiring panel.",
            completed=False,
        )
        updated += 1
    return updated


def _meetings(today: date) -> int:
    if not apps.is_installed("pms"):
        return 0
    from pms.models import Meetings

    updated = 0
    for i, meeting in enumerate(Meetings._base_manager.order_by("id")):
        has_minutes = bool(meeting.response)
        day = (
            today - timedelta(days=10 + i * 7)
            if has_minutes
            else today + timedelta(days=5 + i * 3)
        )
        when = datetime.combine(day, time(11, 0))
        if (
            timezone.is_aware(when) is False
            and timezone.get_current_timezone() is not None
        ):
            try:
                when = timezone.make_aware(when)
            except Exception:
                pass
        Meetings._base_manager.filter(pk=meeting.pk).update(date=when)
        updated += 1
    return updated


def _clamp_timesheets(today: date) -> int:
    if not apps.is_installed("project"):
        return 0
    from project.models import TimeSheet

    qs = TimeSheet._base_manager.filter(date__gt=today)
    return qs.update(date=today - timedelta(days=1))


def _clamp_tickets(today: date) -> int:
    if not apps.is_installed("helpdesk"):
        return 0
    from helpdesk.models import Ticket

    updated = 0
    for ticket in Ticket._base_manager.filter(created_date__gt=today):
        Ticket._base_manager.filter(pk=ticket.pk).update(created_date=today)
        updated += 1
    for ticket in Ticket._base_manager.filter(resolved_date__gt=today):
        Ticket._base_manager.filter(pk=ticket.pk).update(resolved_date=today)
        updated += 1
    return updated


def _fix_asset_expiry(today: date) -> int:
    if not apps.is_installed("asset"):
        return 0
    from asset.models import Asset

    updated = 0
    for i, asset in enumerate(
        Asset._base_manager.exclude(expiry_date=None).order_by("id")
    ):
        purchase = asset.asset_purchase_date
        if not purchase:
            continue
        # A few expire soon so the "expiring" widget has a positive path;
        # the rest last two years from purchase so they aren't already dead.
        if i % 8 == 0:
            expiry = today + timedelta(days=20 + (i % 10))
        else:
            expiry = purchase + timedelta(days=730)
        if expiry <= purchase:
            expiry = purchase + timedelta(days=730)
        Asset._base_manager.filter(pk=asset.pk).update(expiry_date=expiry)
        updated += 1
    return updated


def _pending_attendance_validations(today: date) -> int:
    """A handful of past punches waiting for validation — never future dates."""
    if not apps.is_installed("attendance"):
        return 0
    from attendance.models import Attendance

    ids = list(
        Attendance._base_manager.filter(
            attendance_date__lt=today,
            is_validate_request=False,
        )
        .order_by("-attendance_date")
        .values_list("id", flat=True)[:8]
    )
    if not ids:
        return 0
    return Attendance._base_manager.filter(pk__in=ids).update(
        is_validate_request=True,
        is_validate_request_approved=False,
        attendance_validated=False,
    )
