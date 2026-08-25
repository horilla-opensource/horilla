"""Create demo historical Ticket rows so the helpdesk monthly trend has data.

No base helpdesk fixture exists -- the only Ticket rows ship in
helpdesk_scenarios_data.json. Those are re-anchored by
`reanchor_helpdesk_scenarios` below, not left untouched: their static dates
were authored one calendar year off, so the generic whole-file date shift
(`_shift_fixture_dates`) landed them in the future roughly as often as not,
which a ticket's `created_date`/`resolved_date` must never be.

This module also creates a separate, idempotent (via a title marker) set of
historical tickets spread across the trailing 6 months, reusing existing
TicketType and Employee rows rather than inventing new lookup data.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180
TICKETS_PER_COMPANY = 8
TITLE_MARKER = "Demo Helpdesk Ticket"
STATUS_CYCLE = ("resolved", "resolved", "in_progress", "new", "on_hold", "resolved")


@transaction.atomic
def backfill_helpdesk_tickets(today: date | None = None) -> int:
    """Ensure a per-company set of historical demo tickets exists, then keep
    them spread across the trailing 6 months on every run."""
    if not apps.is_installed("helpdesk"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from employee.models import Employee, EmployeeWorkInformation
    from helpdesk.models import Ticket, TicketType

    types_by_company: dict[int, list[int]] = {}
    for ticket_type_id, company_id in TicketType._base_manager.values_list(
        "id", "company_id"
    ):
        if company_id:
            types_by_company.setdefault(company_id, []).append(ticket_type_id)

    employees_by_company: dict[int, list[int]] = {}
    work_info = dict(
        EmployeeWorkInformation._base_manager.filter(
            employee_id__in=Employee._base_manager.filter(is_active=True)
        ).values_list("employee_id", "company_id")
    )
    for employee_id, company_id in work_info.items():
        if company_id:
            employees_by_company.setdefault(company_id, []).append(employee_id)

    processed = 0
    for company_id, employee_ids in employees_by_company.items():
        ticket_type_ids = types_by_company.get(company_id) or [
            t for types in types_by_company.values() for t in types
        ]
        if not ticket_type_ids or not employee_ids:
            continue
        for i in range(TICKETS_PER_COMPANY):
            title = f"{TITLE_MARKER} C{company_id} #{i}"
            status = STATUS_CYCLE[i % len(STATUS_CYCLE)]
            offset = int(i * TRAILING_DAYS / max(TICKETS_PER_COMPANY - 1, 1))
            created_date = window_start + timedelta(days=offset)
            if created_date > today:
                created_date = today
            resolved_date = None
            if status == "resolved":
                resolved_date = min(created_date + timedelta(days=3), today)

            ticket, _ = Ticket._base_manager.get_or_create(
                title=title,
                defaults={
                    "employee_id_id": employee_ids[i % len(employee_ids)],
                    "ticket_type_id": ticket_type_ids[i % len(ticket_type_ids)],
                    "description": "Auto-generated demo ticket for trend backfill.",
                    "priority": "medium",
                    "assigning_type": "department",
                    "raised_on": "1",
                    "status": status,
                },
            )
            Ticket._base_manager.filter(pk=ticket.pk).update(
                created_date=created_date, resolved_date=resolved_date, status=status
            )
            processed += 1

    logger.info(
        "Helpdesk backfill: %s historical ticket(s) spread over the trailing %s days",
        processed,
        TRAILING_DAYS,
    )
    return processed


SCENARIO_PK_FLOOR = 1001


@transaction.atomic
def reanchor_helpdesk_scenarios(today: date | None = None) -> int:
    """Re-anchor helpdesk_scenarios_data.json's static tickets/comments to `today`.

    The generic whole-file shift only guarantees the fixture's authored
    center lands near `today` -- not that every date stays <= `today`,
    which a real created/resolved timestamp must. Translates the whole
    scenario cluster (tickets + comments) by a single delta so every
    relative gap authored between them is preserved exactly; only the
    latest creation-relevant date is pinned to `today - 1`. `deadline` is
    legitimately forward-looking and shifts by the same delta rather than
    being clamped.
    """
    if not apps.is_installed("helpdesk"):
        return 0

    today = today or date.today()

    from helpdesk.models import Comment, Ticket

    tickets = list(Ticket._base_manager.filter(pk__gte=SCENARIO_PK_FLOOR))
    if not tickets:
        return 0

    creation_dates = [t.created_date for t in tickets if t.created_date] + [
        t.resolved_date for t in tickets if t.resolved_date
    ]
    if not creation_dates:
        return 0

    shift = (today - timedelta(days=1)) - max(creation_dates)
    if shift == timedelta(0):
        return 0

    for ticket in tickets:
        Ticket._base_manager.filter(pk=ticket.pk).update(
            created_date=ticket.created_date + shift if ticket.created_date else None,
            resolved_date=(
                ticket.resolved_date + shift if ticket.resolved_date else None
            ),
            deadline=ticket.deadline + shift if ticket.deadline else None,
        )

    comments = list(Comment._base_manager.filter(pk__gte=SCENARIO_PK_FLOOR))
    for comment in comments:
        Comment._base_manager.filter(pk=comment.pk).update(date=comment.date + shift)

    logger.info(
        "Helpdesk scenario re-anchor: shifted %s ticket(s) and %s comment(s) by %s day(s)",
        len(tickets),
        len(comments),
        shift.days,
    )
    return len(tickets)
