"""Connect fully-built Payroll features to real demo data.

SalaryStructure and the Federal Tax Bracket system are complete, live
features with real business logic (Contract.set_salary_structure(),
progressive tax computation in payroll_calculation()) but ship with zero
demo data connecting them to any employee -- a demo walkthrough that opens
either page sees a working feature with nothing in it.
"""

from __future__ import annotations

import logging
from datetime import date

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

# Reuses the existing Allowance/Deduction catalog (see payroll_data.json)
# rather than inventing new lookup data.
SALARY_STRUCTURE_ALLOWANCE_TITLES = ("House Rent Allowance (HRA)", "Meal Allowance")
SALARY_STRUCTURE_DEDUCTION_TITLES = ("Provident Fund (PF)", "Professional Tax")
CONTRACTS_PER_COMPANY = 5


@transaction.atomic
def backfill_payroll_feature_coverage(today: date | None = None) -> dict[str, int]:
    """Ensure one SalaryStructure per company (attached to a few real active
    contracts) and a FilingStatus assigned to a few contracts per company."""
    if not apps.is_installed("payroll"):
        return {
            "salary_structures": 0,
            "contracts_with_structure": 0,
            "contracts_with_filing_status": 0,
        }

    from base.models import Company
    from employee.models import EmployeeWorkInformation
    from payroll.models.models import (
        Allowance,
        Contract,
        Deduction,
        FilingStatus,
        SalaryStructure,
    )

    allowances = list(
        Allowance._base_manager.filter(title__in=SALARY_STRUCTURE_ALLOWANCE_TITLES)
    )
    deductions = list(
        Deduction._base_manager.filter(title__in=SALARY_STRUCTURE_DEDUCTION_TITLES)
    )
    default_filing_status = FilingStatus._base_manager.order_by("id").first()

    company_ids = list(
        Company._base_manager.order_by("id").values_list("id", flat=True)
    )

    structures_created = 0
    contracts_with_structure = 0
    contracts_with_filing_status = 0

    for company_id in company_ids:
        structure, created = SalaryStructure._base_manager.get_or_create(
            title="Standard Compensation Package",
            company_id_id=company_id,
        )
        if created:
            structures_created += 1
        if allowances:
            structure.allowances.add(*allowances)
        if deductions:
            structure.deductions.add(*deductions)

        contract_ids = list(
            Contract._base_manager.filter(
                contract_status="active",
                employee_id__in=EmployeeWorkInformation._base_manager.filter(
                    company_id=company_id
                ).values_list("employee_id", flat=True),
            )
            .order_by("id")
            .values_list("id", flat=True)[:CONTRACTS_PER_COMPANY]
        )
        for contract in Contract._base_manager.filter(pk__in=contract_ids):
            if contract.salary_structure_id_id != structure.pk:
                contract.set_salary_structure(structure)
                contracts_with_structure += 1
            if default_filing_status and not contract.filing_status_id:
                Contract._base_manager.filter(pk=contract.pk).update(
                    filing_status_id=default_filing_status.pk
                )
                contracts_with_filing_status += 1

    logger.info(
        "Payroll feature backfill: %s structure(s), %s contract(s) attached, "
        "%s contract(s) given a filing status",
        structures_created,
        contracts_with_structure,
        contracts_with_filing_status,
    )
    return {
        "salary_structures": structures_created,
        "contracts_with_structure": contracts_with_structure,
        "contracts_with_filing_status": contracts_with_filing_status,
    }
