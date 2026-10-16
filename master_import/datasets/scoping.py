"""Picking the right record when a name is shared by several companies."""

from employee.models import Employee


def pick(model, column, name, company, **extra):
    """The record called ``name`` that belongs to ``company``.

    Preference: one owned by the company, then one owned by no company at all
    (everyone's), then any. None when nothing has that name.
    """
    records = list(
        model.objects.entire()
        .filter(**{column: name}, **extra)
        .prefetch_related("company_id")
    )
    if not records:
        return None
    if company is not None:
        for record in records:
            if company in record.company_id.all():
                return record
    for record in records:
        if not record.company_id.all():
            return record
    return records[0]


def managers_by_name():
    """{full name: [employees]}: the same name can belong to people in several companies."""
    table = {}
    employees = Employee.objects.entire().select_related(
        "employee_work_info__company_id"
    )
    for employee in employees:
        name = f"{employee.employee_first_name} {employee.employee_last_name}"
        table.setdefault(name, []).append(employee)
    return table


def pick_manager(name, company, table):
    """The employee of that name in ``company``, else the first of that name."""
    found = table.get(name, [])
    if not found:
        return None
    if company is not None:
        for employee in found:
            info = getattr(employee, "employee_work_info", None)
            if info is not None and info.company_id_id == company.pk:
                return employee
    return found[0]
