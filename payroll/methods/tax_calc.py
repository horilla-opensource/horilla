"""
Module: payroll.tax_calc

This module contains a function for calculating the taxable amount for an employee 
based on their contract details and income information.
"""
import datetime
from payroll.methods.payslip_calc import (
    calculate_taxable_gross_pay,
    calculate_gross_pay,
)
from payroll.models.models import Contract
from payroll.models.tax_models import TaxBracket


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
    contract = Contract.objects.filter(employee_id=employee,contract_status='active').first()
    filing = contract.filing_status
    federal_tax_for_period = 0
    if filing is not None:
        based = filing.based_on
        num_days = (end_date - start_date).days + 1
        calculation_functions = {
            "taxable_gross_pay": calculate_taxable_gross_pay,
            "gross_pay": calculate_gross_pay,
        }
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
        yearly_income = round(yearly_income, 2)
        tax_brackets = TaxBracket.objects.filter(filing_status_id=filing).order_by(
            "min_income"
        )
        federal_tax = 0
        remaining_income = yearly_income
        if tax_brackets.exists():
            if tax_brackets.first().min_income <= yearly_income:
                for tax_bracket in tax_brackets:
                    min_income = tax_bracket.min_income
                    max_income = tax_bracket.max_income
                    tax_rate = tax_bracket.tax_rate
                    if remaining_income <= 0:
                        break
                    taxable_amount = min(remaining_income, max_income - min_income)
                    tax_amount = taxable_amount * tax_rate / 100
                    federal_tax += tax_amount
                    remaining_income -= taxable_amount
            daily_federal_tax = federal_tax / total_days
            federal_tax_for_period = daily_federal_tax * num_days
        else:
            federal_tax_for_period = 0
    return federal_tax_for_period
