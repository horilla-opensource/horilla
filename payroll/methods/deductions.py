"""
deductions.py

This module is used to compute the deductions of employees
"""

from payroll.models.models import Deduction


def update_compensation_deduction(
    employee, compensation_amount, compensation_type, start_date, end_date
):
    """
    This method is used to update the basic or gross pay

    Args:
        compensation_amount (_type_): Gross pay or Basic pay or employee
    """
    deduction_heads = (
        Deduction.objects.filter(
            update_compensation=compensation_type, specific_employees=employee
        )
        .exclude(one_time_date__lt=start_date)
        .exclude(one_time_date__gt=end_date)
        # .exclude(exclude_employees=employee)
    )
    deductions = []
    temp = compensation_amount
    for deduction in deduction_heads:
        amount = deduction.amount if deduction.amount else 0
        employee_rate = deduction.rate
        if employee_rate:
            amount = compensation_amount * employee_rate / 100
        compensation_amount = compensation_amount - float(amount)
        employer_contribution_amount = 0
        if max(0, deduction.employer_rate):
            employer_contribution_amount = (amount * deduction.employer_rate) / 100
        deductions.append(
            {
                "deduction_id": deduction.id,
                "title": deduction.title,
                "amount": amount,
                "employer_contribution_rate": deduction.employer_rate,
                "employer_contribution_amount": employer_contribution_amount,
            }
        )

    difference_amount = temp - compensation_amount
    return {
        "compensation_amount": compensation_amount,
        "deductions": deductions,
        "difference_amount": difference_amount,
    }


def create_deductions(instance, amount, date):
    installment = Deduction()
    installment.title = f"{instance.title} - {date}"
    installment.include_active_employees = False
    installment.amount = amount
    installment.is_fixed = True
    installment.one_time_date = date
    installment.only_show_under_employee = True
    installment.is_installment = True
    installment.save()
    installment.include_active_employees = False
    installment.specific_employees.add(instance.employee_id)
    installment.save()

    return installment
