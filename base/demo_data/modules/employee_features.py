"""Connect fully-built Employee/Base features to real demo data.

Each of these is a real, live feature with zero demo rows connecting it to
anything: bank details, employee notes, the shift roster, announcement
read-receipts, and the one configured multi-level leave approval condition
(which has no approvers, so it's "on" but can never actually route to
anyone). A demo walkthrough that opens any of these sees a working feature
with nothing in it.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

BANK_DETAILS_COUNT = 40
NOTES_COUNT = 30
ROSTER_DAYS = 7
ROSTER_EMPLOYEES_PER_DEPARTMENT = 8


@transaction.atomic
def backfill_employee_feature_coverage(today: date | None = None) -> dict[str, int]:
    """Ensure a handful of demo rows exist for each of the features listed
    in the module docstring."""
    today = today or date.today()
    result = {
        "bank_details": 0,
        "notes": 0,
        "roster_entries": 0,
        "roster_publish_logs": 0,
        "announcement_views": 0,
        "approval_managers": 0,
    }
    if not apps.is_installed("employee"):
        return result

    from employee.models import Employee, EmployeeBankDetails, EmployeeNote

    # Bounded against a fixed target, not "+BANK_DETAILS_COUNT more every
    # call" -- excluding already-covered employees without also capping
    # how many are added would let repeated non-flush reloads keep growing
    # coverage indefinitely instead of holding steady at the target.
    already_covered = EmployeeBankDetails._base_manager.count()
    need = max(0, BANK_DETAILS_COUNT - already_covered)
    employee_ids = list(
        Employee._base_manager.filter(is_active=True)
        .exclude(
            pk__in=EmployeeBankDetails._base_manager.values_list(
                "employee_id", flat=True
            )
        )
        .order_by("id")
        .values_list("id", flat=True)[:need]
    )
    for i, employee_id in enumerate(employee_ids):
        EmployeeBankDetails._base_manager.get_or_create(
            employee_id_id=employee_id,
            defaults={
                "bank_name": "Demo National Bank",
                "account_number": f"HRDEMO{employee_id:06d}",
                "branch": "Main Branch",
                "country": "Demo",
            },
        )
        result["bank_details"] += 1

    note_employee_ids = list(
        Employee._base_manager.filter(is_active=True)
        .order_by("id")
        .values_list("id", flat=True)[:NOTES_COUNT]
    )
    for employee_id in note_employee_ids:
        _, created = EmployeeNote._base_manager.get_or_create(
            employee_id_id=employee_id,
            description="Demo onboarding checklist reviewed and complete.",
            defaults={"updated_by_id": employee_id},
        )
        if created:
            result["notes"] += 1

    if apps.is_installed("base"):
        from base.models import (
            Announcement,
            AnnouncementView,
            Department,
            EmployeeShift,
            MultipleApprovalCondition,
            MultipleApprovalManagers,
            Roster,
            RosterPublishLog,
        )
        from employee.models import EmployeeWorkInformation
        from horilla_auth.models import HorillaUser

        # Roster: a week-ahead published schedule for a few employees per
        # department, so the "My Roster" / roster-planning views have
        # something to show instead of a permanently empty calendar.
        default_shift_id = (
            EmployeeShift._base_manager.order_by("id")
            .values_list("id", flat=True)
            .first()
        )
        for department_id in Department._base_manager.order_by("id").values_list(
            "id", flat=True
        ):
            dept_employee_ids = list(
                EmployeeWorkInformation._base_manager.filter(
                    department_id=department_id
                ).values_list("employee_id", flat=True)[
                    :ROSTER_EMPLOYEES_PER_DEPARTMENT
                ]
            )
            if not dept_employee_ids:
                continue
            start = today
            end = today + timedelta(days=ROSTER_DAYS - 1)
            for employee_id in dept_employee_ids:
                for offset in range(ROSTER_DAYS):
                    roster_date = today + timedelta(days=offset)
                    is_off = roster_date.weekday() >= 5
                    _, created = Roster._base_manager.get_or_create(
                        employee_id=employee_id,
                        date=roster_date,
                        defaults={
                            "shift_id": default_shift_id,
                            "department_id": department_id,
                            "is_published": True,
                            "is_off": is_off,
                        },
                    )
                    if created:
                        result["roster_entries"] += 1
            RosterPublishLog._base_manager.get_or_create(
                department_id=department_id,
                from_date=start,
                to_date=end,
                defaults={"published_by_id": dept_employee_ids[0]},
            )
            result["roster_publish_logs"] += 1

        # AnnouncementView: a realistic partial read-receipt spread across
        # the existing announcements, not "everyone has seen everything" or
        # "no one has seen anything."
        user_ids = list(
            HorillaUser._base_manager.filter(is_active=True)
            .order_by("id")
            .values_list("id", flat=True)[:20]
        )
        announcement_ids = list(
            Announcement._base_manager.order_by("id").values_list("id", flat=True)
        )
        for i, announcement_id in enumerate(announcement_ids):
            viewers = (
                user_ids[: max(1, (i + 1) * 2 % len(user_ids))] if user_ids else []
            )
            for user_id in viewers:
                _, created = AnnouncementView._base_manager.get_or_create(
                    user_id=user_id,
                    announcement_id=announcement_id,
                    defaults={"viewed": True},
                )
                if created:
                    result["announcement_views"] += 1

        # The one configured multi-level leave-approval condition currently
        # has no approvers at all, so it's "on" but can never route to
        # anyone. Give it a real manager from the same department/company.
        condition = MultipleApprovalCondition._base_manager.filter(
            pk__in=MultipleApprovalCondition._base_manager.exclude(
                pk__in=MultipleApprovalManagers._base_manager.values_list(
                    "condition_id", flat=True
                )
            ).values_list("pk", flat=True)
        ).first()
        if condition is not None:
            manager_employee_id = (
                EmployeeWorkInformation._base_manager.filter(
                    department_id=condition.department_id,
                    company_id=condition.company_id_id,
                )
                .order_by("employee_id")
                .values_list("employee_id", flat=True)
                .first()
            )
            if manager_employee_id:
                MultipleApprovalManagers._base_manager.get_or_create(
                    condition_id=condition,
                    sequence=1,
                    defaults={"employee_id": manager_employee_id},
                )
                result["approval_managers"] += 1

    logger.info("Employee feature backfill: %s", result)
    return result
