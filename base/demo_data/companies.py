"""Company activation and profile cleanup for demo data."""

from __future__ import annotations

import logging

from django.db import transaction

from base.demo_data.catalog import COMPANY_PROFILES
from base.models import Company

logger = logging.getLogger(__name__)


@transaction.atomic
def ensure_companies() -> int:
    """
    Activate the three generic demo companies and normalize address metadata.

    Returns the number of company rows updated.
    """
    updated = 0
    for name, profile in COMPANY_PROFILES.items():
        company = Company.objects.filter(company=name).first()
        if not company:
            logger.warning("Demo company missing: %s", name)
            continue
        changed = False
        for field, value in profile.items():
            if getattr(company, field, None) != value:
                setattr(company, field, value)
                changed = True
        if changed:
            company.save()
            updated += 1
    return updated
