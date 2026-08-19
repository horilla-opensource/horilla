"""Give every demo company its own Helpdesk lookup data, not just the largest.

DepartmentManager/TicketType/FAQCategory/FAQ all ship 100% scoped to a
single company in helpdesk_scenarios_data.json. Since none of them fall
back to a shared/null-company row, the manager-escalation feature and the
ticket-type/FAQ dropdowns are entirely empty for the other two companies --
not thin, literally nothing to select.
"""

from __future__ import annotations

import logging
from datetime import date

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

# (company_id, ticket type titles, faq category title, faq entries)
NEW_COMPANY_HELPDESK_DATA = [
    (
        2,
        [
            ("IT Support", "service_request", "ITS"),
            ("HR Queries", "service_request", "HRQ"),
        ],
        "General Support",
        [
            (
                "How do I raise a support ticket?",
                "Go to Helpdesk > Tickets > Create and fill out the form.",
            ),
            (
                "Who do I contact for HR queries?",
                "Raise an HR Queries ticket and your local HR team will respond.",
            ),
        ],
    ),
    (
        3,
        [("IT Support", "service_request", "ITS"), ("Facilities", "complaint", "FAC")],
        "General Support",
        [
            (
                "How do I raise a support ticket?",
                "Go to Helpdesk > Tickets > Create and fill out the form.",
            ),
            (
                "Who do I contact about office facilities?",
                "Raise a Facilities ticket describing the issue.",
            ),
        ],
    ),
]


@transaction.atomic
def backfill_company_helpdesk_lookups(today: date | None = None) -> int:
    """Ensure each company in NEW_COMPANY_HELPDESK_DATA has its own
    DepartmentManager, TicketTypes, and FAQ category/entries."""
    if not apps.is_installed("helpdesk"):
        return 0

    today = today or date.today()

    from base.models import Department
    from employee.models import EmployeeWorkInformation
    from helpdesk.models import FAQ, DepartmentManager, FAQCategory, TicketType

    default_department_id = (
        Department.objects.order_by("id").values_list("id", flat=True).first()
    )

    created = 0
    for company_id, ticket_types, faq_category_title, faqs in NEW_COMPANY_HELPDESK_DATA:
        manager_id = (
            EmployeeWorkInformation._base_manager.filter(company_id=company_id)
            .order_by("employee_id")
            .values_list("employee_id", flat=True)
            .first()
        )
        if manager_id and default_department_id:
            DepartmentManager._base_manager.get_or_create(
                manager_id=manager_id,
                department_id=default_department_id,
                defaults={"company_id_id": company_id},
            )

        for title, ticket_type, prefix in ticket_types:
            _, was_created = TicketType._base_manager.get_or_create(
                title=title,
                company_id_id=company_id,
                defaults={"type": ticket_type, "prefix": prefix},
            )
            if was_created:
                created += 1

        category, _ = FAQCategory._base_manager.get_or_create(
            title=faq_category_title,
            company_id_id=company_id,
            defaults={"description": "Common questions for this company."},
        )
        for question, answer in faqs:
            _, was_created = FAQ._base_manager.get_or_create(
                question=question,
                company_id_id=company_id,
                defaults={"answer": answer, "category": category},
            )
            if was_created:
                created += 1

    logger.info(
        "Helpdesk backfill: created %s lookup row(s) across %s new company(ies)",
        created,
        len(NEW_COMPANY_HELPDESK_DATA),
    )
    return created
