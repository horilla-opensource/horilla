"""
Module: payroll.tax_calc

This module contains a function for calculating the taxable amount for an employee
based on their contract details and income information.
"""

import datetime
import logging

from payroll.methods.methods import (
    compute_yearly_taxable_amount,
    convert_year_tax_to_period,
)
from payroll.methods.payslip_calc import (
    calculate_gross_pay,
    calculate_taxable_gross_pay,
)
from payroll.models.models import Contract
from payroll.models.tax_models import TaxBracket

logger = logging.getLogger(__name__)


def calculate_taxable_amount(**kwargs):
    """Calculate the taxable amount for a given employee within a specific period.

    Args:
        employee (int): The ID of the employee.
        start_date (datetime.date): The start date of the period.
        end_date (datetime.date): The end date of the period.
        allowances (int): The number of allowances claimed by the employee.
        total_allowance (float): The total allowance amount.
        basic_pay (float): The basic pay amount.
        day_dict (dict): A dictionary containing specific day-related information.

    Returns:
        float: The federal tax amount for the specified period.
    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    basic_pay = kwargs["basic_pay"]
    contract = Contract.objects.filter(
        employee_id=employee, contract_status="active"
    ).first()
    filing = contract.filing_status
    if not filing:
        return 0
    federal_tax_for_period = 0
    tax_brackets = TaxBracket.objects.filter(filing_status_id=filing).order_by(
        "min_income"
    )
    num_days = (end_date - start_date).days + 1
    calculation_functions = {
        "taxable_gross_pay": calculate_taxable_gross_pay,
        "gross_pay": calculate_gross_pay,
    }
    based = filing.based_on
    if based in calculation_functions:
        calculation_function = calculation_functions[based]
        income = calculation_function(**kwargs)
        income = float(income[based])
    else:
        income = float(basic_pay)

    year = end_date.year
    check_start_date = datetime.date(year, 1, 1)
    check_end_date = datetime.date(year, 12, 31)
    total_days = (check_end_date - check_start_date).days + 1
    yearly_income = income / num_days * total_days
    yearly_income = compute_yearly_taxable_amount(income, yearly_income)
    yearly_income = round(yearly_income, 2)
    federal_tax = 0
    if filing is not None and not filing.use_py:
        brackets = [
            {
                "rate": item["tax_rate"],
                "min": item["min_income"],
                "max": min(item["max_income"], yearly_income),
            }
            for item in tax_brackets.values("tax_rate", "min_income", "max_income")
        ]
        filterd_brackets = []
        for bracket in brackets:
            if bracket["max"] > bracket["min"]:
                bracket["diff"] = bracket["max"] - bracket["min"]
                bracket["calculated_rate"] = (bracket["rate"] / 100) * bracket["diff"]
                filterd_brackets.append(bracket)
                continue
            break
        federal_tax = sum(bracket["calculated_rate"] for bracket in filterd_brackets)

    elif filing.use_py:
        code = filing.python_code
        code = code.replace("print(", "pass_print(")
        pass_print = """
def pass_print(*args, **kwargs):
    return None
"""
        code = pass_print + code
        code = code.replace("  formated_result(", "#  formated_result(")
        local_vars = {}
        exec(code, {}, local_vars)
        try:
            federal_tax = local_vars["calculate_federal_tax"](yearly_income)
        except Exception as e:
            logger.error(e)

    federal_tax_for_period = 0
    if federal_tax and (tax_brackets.exists() or filing.use_py):
        daily_federal_tax = federal_tax / total_days
        federal_tax_for_period = daily_federal_tax * num_days

    federal_tax_for_period = convert_year_tax_to_period(
        federal_tax_for_period=federal_tax_for_period,
        yearly_tax=federal_tax,
        total_days=total_days,
        start_date=start_date,
        end_date=end_date,
    )
    return federal_tax_for_period
