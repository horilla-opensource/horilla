"""Create demo historical Ticket rows so the helpdesk monthly trend has data.

No base helpdesk fixture exists -- the only Ticket rows ship in
helpdesk_scenarios_data.json, and those are intentionally future-dated
(near-term "upcoming" tickets for other widgets), left untouched here. This
creates a separate, idempotent (via a title marker) set of historical
tickets spread across the trailing 6 months, reusing existing TicketType and
Employee rows rather than inventing new lookup data.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180
TICKET_COUNT = 16
TITLE_MARKER = "Demo Helpdesk Ticket"
STATUS_CYCLE = ("resolved", "resolved", "in_progress", "new", "on_hold", "resolved")


@transaction.atomic
def backfill_helpdesk_tickets(today: date | None = None) -> int:
    """Ensure TICKET_COUNT historical demo tickets exist, then keep them
    spread across the trailing 6 months on every run."""
    if not apps.is_installed("helpdesk"):
        return 0

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from employee.models import Employee
    from helpdesk.models import Ticket, TicketType

    ticket_type_ids = list(
        TicketType._base_manager.order_by("id").values_list("id", flat=True)[:6]
    )
    employee_ids = list(
        Employee._base_manager.filter(is_active=True)
        .order_by("id")
        .values_list("id", flat=True)[:20]
    )
    if not ticket_type_ids or not employee_ids:
        return 0

    processed = 0
    for i in range(TICKET_COUNT):
        title = f"{TITLE_MARKER} #{i}"
        status = STATUS_CYCLE[i % len(STATUS_CYCLE)]
        # TICKET_COUNT-1: the last ticket lands at exactly today instead of
        # one step short of it, so the current month isn't left empty.
        offset = int(i * TRAILING_DAYS / max(TICKET_COUNT - 1, 1))
        created_date = window_start + timedelta(days=offset)
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
