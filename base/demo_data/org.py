"""Organization taxonomy renames (departments, jobs, roles) preserving PKs."""

from __future__ import annotations

import logging

from django.db import transaction

from base.demo_data.catalog import (
    DEPARTMENT_RENAMES,
    JOB_POSITION_RENAMES,
    JOB_ROLE_LABEL_RENAMES,
    JOB_ROLE_RENAMES,
)
from base.models import Department, JobPosition, JobRole

logger = logging.getLogger(__name__)


@transaction.atomic
def standardize_org_taxonomy() -> dict[str, int]:
    """
    Rename departments, job positions, and roles in place by PK.

    In-place renames keep all EmployeeWorkInformation and related FKs valid
    without remapping. Returns counts of updated rows per model.
    """
    dept_updated = 0
    for pk, name in DEPARTMENT_RENAMES.items():
        updated = (
            Department.objects.filter(pk=pk)
            .exclude(department=name)
            .update(department=name)
        )
        dept_updated += updated

    # Ensure Operations (Managers) stays shared across companies
    ops = Department.objects.filter(pk=6).first()
    if ops is not None:
        company_ids = list(ops.company_id.values_list("pk", flat=True))
        if set(company_ids) != {1, 2, 3}:
            from base.models import Company

            ops.company_id.set(Company.objects.filter(pk__in=[1, 2, 3]))

    job_updated = 0
    for pk, name in JOB_POSITION_RENAMES.items():
        updated = (
            JobPosition.objects.filter(pk=pk)
            .exclude(job_position=name)
            .update(job_position=name)
        )
        job_updated += updated

    role_updated = 0
    for pk, name in JOB_ROLE_RENAMES.items():
        role_updated += (
            JobRole.objects.filter(pk=pk).exclude(job_role=name).update(job_role=name)
        )

    for old, new in JOB_ROLE_LABEL_RENAMES.items():
        role_updated += (
            JobRole.objects.filter(job_role=old)
            .exclude(job_role=new)
            .update(job_role=new)
        )

    logger.info(
        "Org taxonomy standardized: departments=%s jobs=%s roles=%s",
        dept_updated,
        job_updated,
        role_updated,
    )
    return {
        "departments": dept_updated,
        "job_positions": job_updated,
        "job_roles": role_updated,
    }
