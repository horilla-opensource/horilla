"""Give underrepresented companies a fairer share of demo Payslip coverage.

normalize_demo_payslips() (base/views.py) correctly re-anchors every
existing "Demo Payroll M-<n>"-tagged Payslip onto the current trailing 6
months, but it never creates new ones. Two of the three demo companies have
full Contract coverage yet only ~4 employees ever get paid across all 6
demo months, while the largest company pays a meaningfully larger share of
its own staff -- most contracted employees in the smaller companies never
appear on a payslip at all.

This creates real payslips, computed through the same calculation engine
the app's own scheduled payslip generation uses (payroll_calculation +
save_payslip), for a handful more contracted employees per company --
tagged the same "Demo Payroll M-<n>" convention so normalize_demo_payslips
keeps re-anchoring them on every future run.
"""

from __future__ import annotations

import json
import logging
from datetime import date

from django.apps import apps
from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)

DEMO_PAYROLL_GROUP_PREFIX = "Demo Payroll M-"
# base/views.py's normalize_demo_payslips() renames this prefix to
# "Demo Payroll - <Mon Year>" for a human-readable label, every load -- the
# "already paid" check below must recognize both forms, or a payslip that's
# already been through that rename becomes invisible to this check and a
# brand-new cohort gets backfilled on top of it every reload.
DEMO_PAYROLL_RENAMED_PREFIX = "Demo Payroll - "
TRAILING_MONTHS = 6
TARGET_PAID_PER_COMPANY = 12


@transaction.atomic
def backfill_payroll_coverage(today: date | None = None) -> int:
    """Ensure at least TARGET_PAID_PER_COMPANY employees per company have a
    demo payslip for each of the trailing 6 months, reusing the real
    payroll calculation engine so the generated data is genuinely valid."""
    if not apps.is_installed("payroll"):
        return 0

    today = today or date.today()

    from employee.models import Employee, EmployeeWorkInformation
    from payroll.methods.methods import calculate_employer_contribution, save_payslip
    from payroll.models.models import Contract, Payslip
    from payroll.views.component_views import payroll_calculation

    contracted_employee_ids = set(
        Contract._base_manager.filter(contract_status="active").values_list(
            "employee_id", flat=True
        )
    )
    company_by_employee = dict(
        EmployeeWorkInformation._base_manager.values_list("employee_id", "company_id")
    )

    already_paid_by_company: dict[int, set[int]] = {}
    paid_employee_ids = (
        Payslip._base_manager.filter(
            Q(group_name__startswith=DEMO_PAYROLL_GROUP_PREFIX)
            | Q(group_name__startswith=DEMO_PAYROLL_RENAMED_PREFIX)
        )
        .values_list("employee_id", flat=True)
        .distinct()
    )
    for employee_id in paid_employee_ids:
        company_id = company_by_employee.get(employee_id)
        already_paid_by_company.setdefault(company_id, set()).add(employee_id)

    candidates_by_company: dict[int, list[int]] = {}
    for employee_id in sorted(contracted_employee_ids):
        company_id = company_by_employee.get(employee_id)
        if company_id is not None:
            candidates_by_company.setdefault(company_id, []).append(employee_id)

    created = 0
    for company_id, candidate_ids in candidates_by_company.items():
        already_paid = already_paid_by_company.get(company_id, set())
        need = TARGET_PAID_PER_COMPANY - len(already_paid)
        if need <= 0:
            continue
        new_targets = [e for e in candidate_ids if e not in already_paid][:need]

        for employee_id in new_targets:
            employee = Employee._base_manager.get(pk=employee_id)
            for offset in range(TRAILING_MONTHS):
                # Same month-boundary math as normalize_demo_payslips, so
                # both functions agree on what "M-<offset>" means.
                year, month = today.year, today.month - offset
                while month < 1:
                    month += 12
                    year -= 1
                period_start = date(year, month, 1)
                period_end = date(year, month, 28)

                if Payslip._base_manager.filter(
                    employee_id=employee_id,
                    start_date=period_start,
                    end_date=period_end,
                ).exists():
                    continue

                payslip_data = payroll_calculation(employee, period_start, period_end)
                if not payslip_data:
                    continue

                data = {
                    "employee": employee,
                    "start_date": payslip_data["start_date"],
                    "end_date": payslip_data["end_date"],
                    "status": "paid",
                    "contract_wage": payslip_data["contract_wage"],
                    "basic_pay": payslip_data["basic_pay"],
                    "gross_pay": payslip_data["gross_pay"],
                    "deduction": payslip_data["total_deductions"],
                    "net_pay": payslip_data["net_pay"],
                    "pay_data": json.loads(payslip_data["json_data"]),
                    "group_name": f"{DEMO_PAYROLL_GROUP_PREFIX}{offset}",
                }
                calculate_employer_contribution(data)
                data["installments"] = payslip_data.get("installments", [])
                save_payslip(**data)
                created += 1

    logger.info(
        "Payroll backfill: created %s payslip(s) to rebalance per-company coverage",
        created,
    )
    return created
