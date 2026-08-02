"""Recruitment module demo catalog cleanup."""

from __future__ import annotations

import logging

from django.apps import apps
from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)

TEMPLATE_OVERRIDES = {
    1: (
        "Python Skills Assessment",
        "General Python proficiency questions for engineering roles.",
    ),
    2: (
        "Software Engineer Assessment",
        "Structured interview assessment covering software engineering "
        "fundamentals, backend development, and problem-solving skills.",
    ),
    3: (
        "Backend Engineer Assessment",
        "Interview assessment focused on backend frameworks, APIs, "
        "databases, and application architecture.",
    ),
}


@transaction.atomic
def seed_recruitment_catalog() -> int:
    """Ensure recruitment survey templates use enterprise-standard titles."""
    if not apps.is_installed("recruitment"):
        return 0

    from recruitment.models import SurveyTemplate

    updated = 0
    for pk, (title, description) in TEMPLATE_OVERRIDES.items():
        tmpl = SurveyTemplate.objects.filter(pk=pk).first()
        if not tmpl:
            continue
        tmpl.title = title
        tmpl.description = description
        tmpl.save()
        updated += 1

    leftover = SurveyTemplate.objects.filter(
        Q(title__icontains="Odoo")
        | Q(title__icontains="Django Developer")
        | Q(title__icontains="Cybrosys")
    ).exclude(pk__in=TEMPLATE_OVERRIDES.keys())
    for extra in leftover:
        extra.title = "Technical Skills Assessment"
        extra.description = (
            "General technical assessment for engineering and product roles."
        )
        extra.save()
        updated += 1

    logger.info("Recruitment catalog updated: %s", updated)
    return updated
