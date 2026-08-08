"""Lightweight model factories for Horilla TestCase suites."""

from __future__ import annotations

from base.models import Company, Department, EmployeeShift, WorkType
from employee.models import Employee, EmployeeWorkInformation
from horilla_auth.models import HorillaUser


def make_company(name: str = "Test Corp", **overrides) -> Company:
    defaults = {
        "company": name,
        "hq": True,
        "address": "1 Test St",
        "country": "US",
        "state": "CA",
        "city": "LA",
        "zip": "90001",
    }
    defaults.update(overrides)
    return Company.objects.create(**defaults)


def make_user(
    username: str,
    *,
    password: str = "pass",
    email: str | None = None,
    is_superuser: bool = False,
) -> HorillaUser:
    email = email or f"{username}@test.horilla"
    if is_superuser:
        return HorillaUser.objects.create_superuser(
            username=username, email=email, password=password
        )
    return HorillaUser.objects.create_user(
        username=username, email=email, password=password
    )


def make_employee(
    *,
    company: Company,
    email: str,
    first_name: str = "Test",
    last_name: str = "Employee",
    phone: str = "9999999999",
    user: HorillaUser | None = None,
    shift: EmployeeShift | None = None,
    work_type: WorkType | None = None,
    department: Department | None = None,
) -> Employee:
    """
    Create an Employee and attach work-info to ``company``.

    Employee.save() auto-creates a HorillaUser when none is set; pass
    ``user=`` to link an existing account instead (avoids orphan-user deletes).
    EmployeeWorkInformation is updated afterward — same pattern as leave/
    attendance holiday fixtures.
    """
    emp = Employee(
        employee_first_name=first_name,
        employee_last_name=last_name,
        email=email,
        phone=phone,
    )
    if user is not None:
        emp.employee_user_id = user
    emp.save()
    updates = {"company_id": company}
    if shift is not None:
        updates["shift_id"] = shift
    if work_type is not None:
        updates["work_type_id"] = work_type
    if department is not None:
        updates["department_id"] = department
    updated = EmployeeWorkInformation.objects.filter(employee_id=emp).update(**updates)
    if updated == 0:
        EmployeeWorkInformation.objects.create(employee_id=emp, **updates)
    # Avoid stale reverse OneToOne cache from create().
    return Employee.objects.select_related("employee_work_info").get(pk=emp.pk)
