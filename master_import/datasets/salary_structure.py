"""Putting a salary structure on an employee's contract, found by its title."""

from payroll.models.models import Contract, SalaryStructure


def structure_table():
    """{title: [structures]}: titles can repeat across companies."""
    table = {}
    for structure in SalaryStructure.objects.entire().select_related("company_id"):
        table.setdefault(structure.title, []).append(structure)
    return table


def pick_structure(title, company_name, table):
    """(structure, error). No structure and no error means it is to be created. A title shared by several companies is settled by the person's own."""
    found = table.get(title, [])
    if not found:
        return None, ""  # none by that name: the import creates it
    if len(found) > 1:
        # a structure with no company belongs to everyone
        mine = [
            s
            for s in found
            if s.company_id_id is None
            or (s.company_id and s.company_id.company == company_name)
        ]
        found = mine
    if len(found) != 1:
        return (
            None,
            f"More than one salary structure is titled '{title}'; it cannot be told apart.",
        )
    return found[0], ""


def contract_of(employee):
    """The active contract, or the latest one when none is active."""
    contracts = Contract.objects.entire().filter(employee_id=employee)
    return (
        contracts.filter(contract_status="active")
        .order_by("-contract_start_date", "-id")
        .first()
        or contracts.order_by("-contract_start_date", "-id").first()
    )


def put_on_contract(employee, structure):
    """Returns True when the contract changed. set_salary_structure also adds the
    employee to the structure's components, the way the contract form does."""
    contract = contract_of(employee)
    if contract is None or contract.salary_structure_id_id == structure.pk:
        return False
    contract.set_salary_structure(structure)
    return True


def get_or_create_structure(title, company_name, cache):
    """The structure by that title for the company, made when there is none.

    Made empty, as Gross Up, owned by the company: its components are added
    afterwards on the structure's own page.
    """
    from base.models import Company

    key = (title, company_name)
    if key not in cache:
        table = structure_table()
        found, _why = pick_structure(title, company_name, table)
        if found is None:
            company = (
                Company.objects.filter(company=company_name).first()
                if company_name
                else None
            )
            found = SalaryStructure.objects.create(
                title=title, structure_mode="gross_up", company_id=company
            )
        cache[key] = found
    return cache[key]
