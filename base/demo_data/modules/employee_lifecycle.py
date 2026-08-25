"""Give demo employee joining/exit dates real spread across a trailing 6 months.

`EmployeeWorkInformation.date_joining` ships with zero rows in the current
year at all, and `contract_end_date` is almost always null -- so the hires
and exits sides of the turnover chart, plus the joining/headcount trends,
render empty regardless of the `_shift_fixture_dates` anchor shift (that
shift relocates dates, it doesn't manufacture new ones). This moves a small,
deterministic set of existing employees' dates into the window instead.

Named demo personas used for role-assignment scenarios (base/demo_roles.py
DEMO_ROLE_ASSIGNMENTS) are excluded so this never breaks that demo. Employees
the static offboarding fixture already marks as departed are excluded too,
so this never "re-hires" someone the offboarding pipeline shows as archived.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

TRAILING_DAYS = 180
NEW_HIRE_COUNT = 12
EXIT_COUNT = 7

# Keep in sync with base/demo_roles.py DEMO_ROLE_ASSIGNMENTS -- these
# employees are load-bearing for the Roles & Permissions demo and must stay
# untouched (still active, still with their original join date).
_PROTECTED_EMAILS = {
    "alexander.smith@horilla.com",
    "michael.brown@horilla.com",
    "sarah.anderson@horilla.com",
    "emily.clark@horilla.com",
    "jessica.evans@horilla.com",
    "benjamin.parker@horilla.com",
    "lily.campbell@horilla.com",
    "matthew.harris@horilla.com",
    "david.king@horilla.com",
}


def _static_offboarding_employee_ids(load_dir: Path | None = None) -> set[int]:
    """Employee ids the *static* offboarding fixture already marks departed.

    Read directly from load_data/offboarding_data.json rather than querying
    OffboardingEmployee/ResignationLetter in the DB -- those tables also
    accumulate rows this same seeder creates on every run (offboarding_trend,
    offboarding_expansion), so live-querying them would make the exclusion
    set grow indefinitely and shift which employees land in hire_ids/
    exit_ids on every reload. The static fixture file never changes, so this
    set is always the same.
    """
    load_dir = load_dir or Path(settings.BASE_DIR) / "load_data"
    path = load_dir / "offboarding_data.json"
    if not path.exists():
        return set()
    with open(path) as f:
        rows = json.load(f)
    ids: set[int] = set()
    for row in rows:
        if row.get("model") in (
            "offboarding.offboardingemployee",
            "offboarding.resignationletter",
        ):
            emp_id = row.get("fields", {}).get("employee_id")
            if emp_id is not None:
                ids.add(emp_id)
    return ids


@transaction.atomic
def backfill_employee_lifecycle(
    today: date | None = None, load_dir: Path | None = None
) -> dict:
    """
    Move a deterministic set of employees' date_joining into the trailing
    6 months (new hires), and a separate set's contract_end_date + is_active
    (exits). Returns {"hires": n, "exits": n}.
    """
    if not apps.is_installed("employee"):
        return {"hires": 0, "exits": 0}

    today = today or date.today()
    window_start = today - timedelta(days=TRAILING_DAYS)

    from employee.models import Employee, EmployeeWorkInformation

    # Deliberately NOT filtered by is_active: a prior run may have already
    # marked the exit set inactive, and filtering on it here would shift
    # which employees land in each slice on every re-run, cascading more
    # employees into "exited" every time load_demo_data runs. Ordering by
    # id off the full (protected/superuser-excluded) pool keeps both slices
    # stable across repeated runs.
    safe_qs = Employee._base_manager.exclude(email__in=_PROTECTED_EMAILS).exclude(
        employee_user_id__is_superuser=True
    )
    # The static offboarding fixture already tells a complete departure
    # story for a fixed set of employees. Picking one of them as a "new
    # hire" here contradicts that story -- e.g. re-hiring someone the
    # fixture shows sitting in an Archived offboarding stage.
    if apps.is_installed("offboarding"):
        offboarding_employee_ids = _static_offboarding_employee_ids(load_dir)
        if offboarding_employee_ids:
            safe_qs = safe_qs.exclude(pk__in=offboarding_employee_ids)
    # The turnover/joining dashboards are company-scoped by session, and a
    # fresh demo login defaults to the first company. Picking candidates
    # from other companies first would spread hires/exits across companies
    # that default (single-company) chart view never sees, leaving it
    # looking mostly empty despite the data existing elsewhere. Prefer the
    # lowest-id company (the one every fixture creates first) so the chart
    # looks right without switching companies first.
    from base.models import Company

    default_company_id = (
        Company._base_manager.order_by("id").values_list("id", flat=True).first()
    )
    same_company_ids = set(
        EmployeeWorkInformation._base_manager.filter(
            company_id=default_company_id
        ).values_list("employee_id", flat=True)
    )
    all_ids = list(safe_qs.order_by("id").values_list("id", flat=True))
    safe_ids = [i for i in all_ids if i in same_company_ids] + [
        i for i in all_ids if i not in same_company_ids
    ]

    hire_ids = safe_ids[:NEW_HIRE_COUNT]
    exit_ids = safe_ids[NEW_HIRE_COUNT : NEW_HIRE_COUNT + EXIT_COUNT]

    # count-1, not count: anchors the last hire/exit at exactly today instead
    # of one step short of it -- with only a handful of points, that step is
    # big enough to leave the current month's bucket empty otherwise.
    for i, emp_id in enumerate(hire_ids):
        offset = int(i * TRAILING_DAYS / max(len(hire_ids) - 1, 1))
        new_join = window_start + timedelta(days=offset)
        EmployeeWorkInformation._base_manager.filter(employee_id=emp_id).update(
            date_joining=new_join
        )

    for i, emp_id in enumerate(exit_ids):
        offset = int(i * TRAILING_DAYS / max(len(exit_ids) - 1, 1))
        new_exit = window_start + timedelta(days=offset)
        EmployeeWorkInformation._base_manager.filter(employee_id=emp_id).update(
            contract_end_date=new_exit
        )
        Employee._base_manager.filter(pk=emp_id).update(is_active=False)

    logger.info(
        "Employee lifecycle backfill: %s new hire(s), %s exit(s) over the trailing %s days",
        len(hire_ids),
        len(exit_ids),
        TRAILING_DAYS,
    )
    return {
        "hires": len(hire_ids),
        "exits": len(exit_ids),
        "exit_employee_ids": exit_ids,
    }
