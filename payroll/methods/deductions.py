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
        compensation_amount = compensation_amount - float(amount)
        deductions.append({"title": deduction.title, "amount": amount})

    difference_amount = temp - compensation_amount
    return {
        "compensation_amount": compensation_amount,
        "deductions": deductions,
        "difference_amount": difference_amount,
    }
