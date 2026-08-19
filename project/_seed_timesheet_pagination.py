"""
One-shot seeder: add timesheet rows so Project > Timesheet pagination
(group-by employee + within-group pages) can be tested.

Run:
    python manage.py shell < project/_seed_timesheet_pagination.py
or:
    python project/_seed_timesheet_pagination.py  (with DJANGO_SETTINGS_MODULE)
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.db.models import Count

from employee.models import Employee, EmployeeWorkInformation
from project.models import Project, Task, TimeSheet

COMPANY_ID = 1
# Group-by uses 10 groups/page; nested group lists use 10 rows/page.
TARGET_EMPLOYEE_GROUPS = 35
ROWS_PER_EMPLOYEE = 12
DESCRIPTIONS = [
    "Demo timesheet for pagination testing",
    "Follow-up work on assigned task",
    "Code review and documentation update",
    "Sprint planning notes",
    "Bug triage and fixes",
    "Client sync and status update",
    "QA verification pass",
    "Deploy preparation",
    "Refactor module helpers",
    "Write unit coverage",
    "Pair programming session",
    "Backlog grooming",
]


def main():
    project = (
        Project.objects.filter(company_id=COMPANY_ID, is_active=True)
        .order_by("-id")
        .first()
    )
    if not project:
        raise SystemExit("No active project found for company_id=%s" % COMPANY_ID)

    task = Task.objects.filter(project=project).order_by("-id").first()
    if not task:
        task = Task.objects.create(
            title="Pagination Demo Task",
            project=project,
            status="in_progress",
            description="Auto-created for timesheet pagination demo",
        )

    # Prefer company employees; fall back to any active employees.
    company_emps = list(
        Employee.objects.filter(
            is_active=True, employee_work_info__company_id=COMPANY_ID
        ).order_by("id")
    )
    if len(company_emps) < TARGET_EMPLOYEE_GROUPS:
        extra = list(
            Employee.objects.filter(is_active=True)
            .exclude(id__in=[e.id for e in company_emps])
            .order_by("id")[: TARGET_EMPLOYEE_GROUPS - len(company_emps)]
        )
        for emp in extra:
            wi, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=emp)
            if wi.company_id_id != COMPANY_ID:
                wi.company_id_id = COMPANY_ID
                wi.save(update_fields=["company_id"])
            company_emps.append(emp)

    # Create lightweight demo employees if still short.
    created_emps = 0
    while len(company_emps) < TARGET_EMPLOYEE_GROUPS:
        n = len(company_emps) + 1
        badge = f"PAG{n:03d}"
        email = f"pagination.demo{n}@horilla.local"
        if Employee.objects.filter(email=email).exists():
            emp = Employee.objects.get(email=email)
        else:
            emp = Employee.objects.create(
                employee_first_name=f"Pagination",
                employee_last_name=f"Demo{n:02d}",
                email=email,
                phone=f"9000000{n:03d}"[-10:],
                badge_id=badge,
                is_active=True,
            )
            EmployeeWorkInformation.objects.create(
                employee_id=emp, company_id_id=COMPANY_ID
            )
            created_emps += 1
        company_emps.append(emp)

    employees = company_emps[:TARGET_EMPLOYEE_GROUPS]
    if task:
        # Task M2M names may vary; ignore if absent.
        for attr in ("task_members", "members"):
            if hasattr(task, attr):
                getattr(task, attr).add(*employees)
                break

    today = date.today()
    created_rows = 0
    for emp in employees:
        existing = TimeSheet.objects.filter(employee_id=emp).count()
        need = max(0, ROWS_PER_EMPLOYEE - existing)
        for i in range(need):
            TimeSheet.objects.create(
                project_id=project,
                task_id=task,
                employee_id=emp,
                date=today - timedelta(days=(i % 28) + 1),
                time_spent=f"{(i % 6):02d}:{(i * 15) % 60:02d}",
                status="in_Progress" if i % 2 == 0 else "completed",
                description=DESCRIPTIONS[i % len(DESCRIPTIONS)],
            )
            created_rows += 1

    groups = (
        TimeSheet.objects.filter(project_id__company_id=COMPANY_ID)
        .values("employee_id")
        .distinct()
        .count()
    )
    total = TimeSheet.objects.filter(project_id__company_id=COMPANY_ID).count()
    print(
        f"Done. created_employees={created_emps}, created_timesheets={created_rows}, "
        f"company_timesheets={total}, employee_groups={groups}, "
        f"project={project.id} ({project.title}), task={task.id}"
    )
    print(
        "Refresh /project/view-time-sheet/ with Group by Employee — "
        "expect multiple group pages (10/page) and nested pages inside groups."
    )


if __name__ == "__main__":
    main()
