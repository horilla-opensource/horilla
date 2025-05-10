"""
This module contains various functions for calculating payroll-related information for employees.
It includes functions for calculating gross pay, taxable gross pay, allowances, tax deductions,
pre-tax deductions, and post-tax deductions.

"""

import contextlib
import operator

from django.apps import apps

# from attendance.models import Attendance
from horilla.methods import get_horilla_model_class
from payroll.methods.deductions import update_compensation_deduction
from payroll.methods.limits import compute_limit
from payroll.models import models
from payroll.models.models import (
    Allowance,
    Contract,
    Deduction,
    LoanAccount,
    MultipleCondition,
)


def return_none(a, b):
    return None


operator_mapping = {
    "equal": operator.eq,
    "notequal": operator.ne,
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
    "icontains": operator.contains,
    "range": return_none,
}
filter_mapping = {
    "work_type_id": {
        "filter": lambda employee, allowance, start_date, end_date: {
            "employee_id": employee,
            "work_type_id__id": allowance.work_type_id.id,
            "attendance_date__range": (start_date, end_date),
            "attendance_validated": True,
        }
    },
    "shift_id": {
        "filter": lambda employee, allowance, start_date, end_date: {
            "employee_id": employee,
            "shift_id__id": allowance.shift_id.id,
            "attendance_date__range": (start_date, end_date),
            "attendance_validated": True,
        }
    },
    "overtime": {
        "filter": lambda employee, allowance, start_date, end_date: {
            "employee_id": employee,
            "attendance_date__range": (start_date, end_date),
            "attendance_overtime_approve": True,
            "attendance_validated": True,
        }
    },
    "attendance": {
        "filter": lambda employee, allowance, start_date, end_date: {
            "employee_id": employee,
            "attendance_date__range": (start_date, end_date),
            "attendance_validated": True,
        }
    },
}


tets = {
    "net_pay": 35140.905000000006,
    "employee": 1,
    "allowances": [
        {
            "allowance_id": 5,
            "title": "Low Basic Pay Assistance",
            "is_taxable": True,
            "amount": 0,
        },
        {
            "allowance_id": 13,
            "title": "Bonus point Redeem for Adam Luis ",
            "is_taxable": True,
            "amount": 75.0,
        },
        {
            "allowance_id": 17,
            "title": "Motorcycle",
            "is_taxable": True,
            "amount": 5000.0,
        },
        {
            "allowance_id": 2,
            "title": "Meal Allowance",
            "is_taxable": False,
            "amount": 800.0,
        },
    ],
    "gross_pay": 39284.09090909091,
    "contract_wage": 35000.0,
    "basic_pay": 33409.09090909091,
    "paid_days": 21.0,
    "unpaid_days": 1.0,
    "taxable_gross_pay": {"taxable_gross_pay": 35848.47727272727},
    "basic_pay_deductions": [],
    "gross_pay_deductions": [],
    "pretax_deductions": [
        {
            "deduction_id": 1,
            "title": "Social Security (FICA)",
            "is_pretax": True,
            "amount": 2435.6136363636365,
            "employer_contribution_rate": 6.2,
        },
        {
            "deduction_id": 62,
            "title": "Late Come penalty",
            "is_pretax": True,
            "amount": 200.0,
            "employer_contribution_rate": 0.0,
        },
    ],
    "post_tax_deductions": [
        {
            "deduction_id": 2,
            "title": "Medicare tax",
            "is_pretax": False,
            "amount": 484.43181818181824,
            "employer_contribution_rate": 1.45,
        },
        {
            "deduction_id": 55,
            "title": "ESI",
            "is_pretax": False,
            "amount": 0,
            "employer_contribution_rate": 3.25,
        },
        {
            "deduction_id": 73,
            "title": "Test",
            "is_pretax": False,
            "amount": 0.0,
            "employer_contribution_rate": 0.0,
        },
    ],
    "tax_deductions": [
        {
            "deduction_id": 75,
            "title": "test tax netpay",
            "is_tax": True,
            "amount": 668.1818181818182,
            "employer_contribution_rate": 3.0,
        }
    ],
    "net_deductions": [
        {
            "deduction_id": 74,
            "title": "Test Netpay",
            "is_pretax": False,
            "amount": 354.9586363636364,
            "employer_contribution_rate": 2.0,
        }
    ],
    "total_deductions": 3788.227272727273,
    "loss_of_pay": 1590.909090909091,
    "federal_tax": 0,
    "start_date": "2024-02-01",
    "end_date": "2024-02-29",
    "range": "Feb 01 2024 - Feb 29 2024",
}


def dynamic_attr(obj, attribute_path):
    """
    Retrieves the value of a nested attribute from a related object dynamically.

    Args:
        obj: The base object from which to start accessing attributes.
        attribute_path (str): The path of the nested attribute to retrieve, using
        double underscores ('__') to indicate relationship traversal.

    Returns:
        The value of the nested attribute if it exists, or None if it doesn't exist.
    """
    attributes = attribute_path.split("__")

    for attr in attributes:
        with contextlib.suppress(Exception):
            if isinstance(obj.first(), Contract):
                obj = obj.filter(is_active=True).first()

        obj = getattr(obj, attr, None)
        if obj is None:
            break
    return obj


def calculate_gross_pay(*_args, **kwargs):
    """
    Calculate the gross pay for an employee within a given date range.

    Args:
        employee: The employee object for whom to calculate the gross pay.
        start_date: The start date of the period for which to calculate the gross pay.
        end_date: The end date of the period for which to calculate the gross pay.

    Returns:
        A dictionary containing the gross pay as the "gross_pay" key.

    """
    basic_pay = kwargs["basic_pay"]
    total_allowance = kwargs["total_allowance"]
    # basic_pay = compute_salary_on_period(employee, start_date, end_date)["basic_pay"]
    gross_pay = total_allowance + basic_pay

    employee, start_date, end_date = (
        kwargs[key] for key in ("employee", "start_date", "end_date")
    )

    updated_gross_pay_data = update_compensation_deduction(
        employee, gross_pay, "gross_pay", start_date, end_date
    )
    return {
        "gross_pay": updated_gross_pay_data["compensation_amount"],
        "basic_pay": basic_pay,
        "deductions": updated_gross_pay_data["deductions"],
    }


def calculate_taxable_gross_pay(*_args, **kwargs):
    """
    Calculate the taxable gross pay for an employee within a given date range.

    Args:
        employee: The employee object for whom to calculate the taxable gross pay.
        start_date: The start date of the period for which to calculate the taxable gross pay.
        end_date: The end date of the period for which to calculate the taxable gross pay.

    Returns:
        A dictionary containing the taxable gross pay as the "taxable_gross_pay" key.

    """
    allowances = kwargs["allowances"]
    gross_pay = calculate_gross_pay(**kwargs)
    gross_pay = gross_pay["gross_pay"]
    pre_tax_deductions = calculate_pre_tax_deduction(**kwargs)
    non_taxable_allowance_total = sum(
        allowance["amount"]
        for allowance in allowances["allowances"]
        if not allowance["is_taxable"]
    )
    pretax_deduction_total = sum(
        deduction["amount"]
        for deduction in pre_tax_deductions["pretax_deductions"]
        if deduction["is_pretax"]
    )
    taxable_gross_pay = gross_pay - non_taxable_allowance_total - pretax_deduction_total
    return {
        "taxable_gross_pay": taxable_gross_pay,
    }


def calculate_allowance(**kwargs):
    """
    Calculate the allowances for an employee within the specified payroll period.

    Args:
        employee (Employee): The employee object for which to calculate the allowances.
        start_date (datetime.date): The start date of the payroll period.
        end_date (datetime.date): The end date of the payroll period.

    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    basic_pay = kwargs["basic_pay"]
    day_dict = kwargs["day_dict"]
    specific_allowances = Allowance.objects.filter(specific_employees=employee)
    conditional_allowances = Allowance.objects.filter(is_condition_based=True).exclude(
        exclude_employees=employee
    )
    active_employees = Allowance.objects.filter(include_active_employees=True).exclude(
        exclude_employees=employee
    )

    allowances = specific_allowances | conditional_allowances | active_employees

    allowances = (
        allowances.exclude(one_time_date__lt=start_date)
        .exclude(one_time_date__gt=end_date)
        .distinct()
    )

    employee_allowances = []
    tax_allowances = []
    no_tax_allowances = []
    tax_allowances_amt = []
    no_tax_allowances_amt = []
    # Append allowances based on condition, or unconditionally to employee
    for allowance in allowances:
        if allowance.is_condition_based:
            conditions = list(
                allowance.other_conditions.values_list("field", "condition", "value")
            )
            condition_field = allowance.field
            condition_operator = allowance.condition
            condition_value = allowance.value.lower().replace(" ", "_")
            conditions.append((condition_field, condition_operator, condition_value))
            applicable = True
            for condition in conditions:
                val = dynamic_attr(employee, condition[0])
                if val is not None:
                    operator_func = operator_mapping.get(condition[1])
                    condition_value = type(val)(condition[2])
                    if operator_func(val, condition_value):
                        applicable = applicable * True
                        continue
                    else:
                        applicable = False
                        break
                else:
                    applicable = False
                    break
            if applicable:
                employee_allowances.append(allowance)
        else:
            if allowance.based_on in filter_mapping:
                filter_params = filter_mapping[allowance.based_on]["filter"](
                    employee, allowance, start_date, end_date
                )
                if apps.is_installed("attendance"):
                    Attendance = get_horilla_model_class(
                        app_label="attendance", model="attendance"
                    )
                    if Attendance.objects.filter(**filter_params):
                        employee_allowances.append(allowance)
            else:
                employee_allowances.append(allowance)
    # Filter and append taxable allowance and not taxable allowance
    for allowance in employee_allowances:
        if allowance.is_taxable:
            tax_allowances.append(allowance)
        else:
            no_tax_allowances.append(allowance)
    # Find and append the amount of tax_allowances
    for allowance in tax_allowances:
        if allowance.is_fixed:
            amount = allowance.amount
            kwargs["amount"] = amount
            kwargs["component"] = allowance

            amount = if_condition_on(**kwargs)
            tax_allowances_amt.append(amount)
        else:
            calculation_function = calculation_mapping.get(allowance.based_on)
            amount = calculation_function(
                **{
                    "employee": employee,
                    "start_date": start_date,
                    "end_date": end_date,
                    "component": allowance,
                    "allowances": None,
                    "total_allowance": None,
                    "basic_pay": basic_pay,
                    "day_dict": day_dict,
                },
            )
            kwargs["amount"] = amount
            kwargs["component"] = allowance
            amount = if_condition_on(**kwargs)
            tax_allowances_amt.append(amount)
    # Find and append the amount of not tax_allowances
    for allowance in no_tax_allowances:
        if allowance.is_fixed:
            amount = allowance.amount
            kwargs["amount"] = amount
            kwargs["component"] = allowance
            amount = if_condition_on(**kwargs)
            no_tax_allowances_amt.append(amount)

        else:
            calculation_function = calculation_mapping.get(allowance.based_on)
            amount = calculation_function(
                **{
                    "employee": employee,
                    "start_date": start_date,
                    "end_date": end_date,
                    "component": allowance,
                    "day_dict": day_dict,
                    "basic_pay": basic_pay,
                }
            )
            kwargs["amount"] = amount
            kwargs["component"] = allowance
            amount = if_condition_on(**kwargs)
            no_tax_allowances_amt.append(amount)
    serialized_allowances = []

    # Serialize taxable allowances
    for allowance, amount in zip(tax_allowances, tax_allowances_amt):
        serialized_allowance = {
            "allowance_id": allowance.id,
            "title": allowance.title,
            "is_taxable": allowance.is_taxable,
            "amount": amount,
        }
        serialized_allowances.append(serialized_allowance)

    # Serialize no-taxable allowances
    for allowance, amount in zip(no_tax_allowances, no_tax_allowances_amt):
        serialized_allowance = {
            "allowance_id": allowance.id,
            "title": allowance.title,
            "is_taxable": allowance.is_taxable,
            "amount": amount,
        }
        serialized_allowances.append(serialized_allowance)
    return {"allowances": serialized_allowances}


def calculate_tax_deduction(*_args, **kwargs):
    """
    Calculates the tax deductions for the specified employee within the given date range.

    Args:
        employee (Employee): The employee for whom the tax deductions are being calculated.
        start_date (date): The start date of the tax deduction period.
        end_date (date): The end date of the tax deduction period.
        allowances (dict): Dictionary containing the calculated allowances.
        total_allowance (float): The total amount of allowances.
        basic_pay (float): The basic pay amount.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        dict: A dictionary containing the serialized tax deductions.
    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    specific_deductions = models.Deduction.objects.filter(
        specific_employees=employee, is_pretax=False, is_tax=True
    )
    active_employee_deduction = models.Deduction.objects.filter(
        include_active_employees=True, is_pretax=False, is_tax=True
    ).exclude(exclude_employees=employee)
    deductions = specific_deductions | active_employee_deduction
    deductions = (
        deductions.exclude(one_time_date__lt=start_date)
        .exclude(one_time_date__gt=end_date)
        .exclude(update_compensation__isnull=False)
    )
    deductions_amt = []
    serialized_deductions = []
    for deduction in deductions:
        calculation_function = calculation_mapping.get(deduction.based_on)
        amount = calculation_function(
            **{
                "employee": employee,
                "start_date": start_date,
                "end_date": end_date,
                "component": deduction,
                "allowances": kwargs["allowances"],
                "total_allowance": kwargs["total_allowance"],
                "basic_pay": kwargs["basic_pay"],
                "day_dict": kwargs["day_dict"],
            }
        )
        kwargs["amount"] = amount
        kwargs["component"] = deduction
        amount = if_condition_on(**kwargs)
        deductions_amt.append(amount)
    for deduction, amount in zip(deductions, deductions_amt):
        serialized_deduction = {
            "deduction_id": deduction.id,
            "title": deduction.title,
            "is_tax": deduction.is_tax,
            "amount": amount,
            "employer_contribution_rate": deduction.employer_rate,
        }
        serialized_deductions.append(serialized_deduction)
    return {"tax_deductions": serialized_deductions}


def calculate_pre_tax_deduction(*_args, **kwargs):
    """
    This function retrieves pre-tax deductions applicable to the employee and calculates
    their amounts

    Args:
        employee: The employee object for whom to calculate the pre-tax deductions.
        start_date: The start date of the period for which to calculate the pre-tax deductions.
        end_date: The end date of the period for which to calculate the pre-tax deductions.

    Returns:
        A dictionary containing the pre-tax deductions as the "pretax_deductions" key.

    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]

    specific_deductions = models.Deduction.objects.filter(
        specific_employees=employee, is_pretax=True, is_tax=False
    )
    conditional_deduction = models.Deduction.objects.filter(
        is_condition_based=True, is_pretax=True, is_tax=False
    ).exclude(exclude_employees=employee)
    active_employee_deduction = models.Deduction.objects.filter(
        include_active_employees=True, is_pretax=True, is_tax=False
    ).exclude(exclude_employees=employee)

    deductions = specific_deductions | conditional_deduction | active_employee_deduction
    deductions = (
        deductions.exclude(one_time_date__lt=start_date)
        .exclude(one_time_date__gt=end_date)
        .exclude(update_compensation__isnull=False)
    )
    # Installment deductions
    installments = deductions.filter(is_installment=True)

    pre_tax_deductions = []
    pre_tax_deductions_amt = []
    serialized_deductions = []

    for deduction in deductions:
        if deduction.is_condition_based:
            conditions = list(
                deduction.other_conditions.values_list("field", "condition", "value")
            )
            condition_field = deduction.field
            condition_operator = deduction.condition
            condition_value = deduction.value.lower().replace(" ", "_")
            conditions.append((condition_field, condition_operator, condition_value))
            operator_func = operator_mapping.get(condition_operator)
            applicable = True
            for condition in conditions:
                val = dynamic_attr(employee, condition[0])
                if val is not None:
                    operator_func = operator_mapping.get(condition[1])
                    condition_value = type(val)(condition[2])
                    if operator_func(val, condition_value):
                        applicable = applicable * True
                        continue
                    else:
                        applicable = False
                        break
                else:
                    applicable = False
                    break
            if applicable:
                pre_tax_deductions.append(deduction)
        else:
            pre_tax_deductions.append(deduction)

    for deduction in pre_tax_deductions:
        if deduction.is_fixed:
            kwargs["amount"] = deduction.amount
            kwargs["component"] = deduction
            pre_tax_deductions_amt.append(if_condition_on(**kwargs))
        else:
            calculation_function = calculation_mapping.get(deduction.based_on)
            amount = calculation_function(
                **{
                    "employee": employee,
                    "start_date": start_date,
                    "end_date": end_date,
                    "component": deduction,
                    "allowances": kwargs["allowances"],
                    "total_allowance": kwargs["total_allowance"],
                    "basic_pay": kwargs["basic_pay"],
                    "day_dict": kwargs["day_dict"],
                }
            )
            kwargs["amount"] = amount
            kwargs["component"] = deduction
            pre_tax_deductions_amt.append(if_condition_on(**kwargs))
    for deduction, amount in zip(pre_tax_deductions, pre_tax_deductions_amt):
        serialized_deduction = {
            "deduction_id": deduction.id,
            "title": deduction.title,
            "is_pretax": deduction.is_pretax,
            "amount": amount,
            "employer_contribution_rate": deduction.employer_rate,
        }
        serialized_deductions.append(serialized_deduction)
    return {"pretax_deductions": serialized_deductions, "installments": installments}


def calculate_post_tax_deduction(*_args, **kwargs):
    """
    This function retrieves post-tax deductions applicable to the employee and calculates
    their amounts

    Args:
        employee: The employee object for whom to calculate the pre-tax deductions.
        start_date: The start date of the period for which to calculate the pre-tax deductions.
        end_date: The end date of the period for which to calculate the pre-tax deductions.

    Returns:
        A dictionary containing the pre-tax deductions as the "post_tax_deductions" key.

    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    allowances = kwargs["allowances"]
    total_allowance = kwargs["total_allowance"]
    basic_pay = kwargs["basic_pay"]
    day_dict = kwargs["day_dict"]
    specific_deductions = models.Deduction.objects.filter(
        specific_employees=employee, is_pretax=False, is_tax=False
    )
    conditional_deduction = models.Deduction.objects.filter(
        is_condition_based=True, is_pretax=False, is_tax=False
    ).exclude(exclude_employees=employee)
    active_employee_deduction = models.Deduction.objects.filter(
        include_active_employees=True, is_pretax=False, is_tax=False
    ).exclude(exclude_employees=employee)
    deductions = specific_deductions | conditional_deduction | active_employee_deduction
    deductions = (
        deductions.exclude(one_time_date__lt=start_date)
        .exclude(one_time_date__gt=end_date)
        .exclude(update_compensation__isnull=False)
    )
    # Installment deductions
    installments = deductions.filter(is_installment=True)

    post_tax_deductions = []
    post_tax_deductions_amt = []
    serialized_deductions = []
    serialized_net_pay_deductions = []

    for deduction in deductions:
        if deduction.is_condition_based:
            condition_field = deduction.field
            condition_operator = deduction.condition
            condition_value = deduction.value.lower().replace(" ", "_")
            employee_value = dynamic_attr(employee, condition_field)
            operator_func = operator_mapping.get(condition_operator)
            if employee_value is not None:
                condition_value = type(employee_value)(condition_value)
                if operator_func(employee_value, condition_value):
                    post_tax_deductions.append(deduction)
        else:
            post_tax_deductions.append(deduction)
    for deduction in post_tax_deductions:
        if deduction.is_fixed:
            amount = deduction.amount
            kwargs["amount"] = amount
            kwargs["component"] = deduction
            amount = if_condition_on(**kwargs)
            post_tax_deductions_amt.append(amount)
        else:
            if deduction.based_on != "net_pay":
                calculation_function = calculation_mapping.get(deduction.based_on)
                amount = calculation_function(
                    **{
                        "employee": employee,
                        "start_date": start_date,
                        "end_date": end_date,
                        "component": deduction,
                        "allowances": allowances,
                        "total_allowance": total_allowance,
                        "basic_pay": basic_pay,
                        "day_dict": day_dict,
                    }
                )
                kwargs["amount"] = amount
                kwargs["component"] = deduction
                amount = if_condition_on(**kwargs)
                post_tax_deductions_amt.append(amount)

    for deduction, amount in zip(post_tax_deductions, post_tax_deductions_amt):
        serialized_deduction = {
            "deduction_id": deduction.id,
            "title": deduction.title,
            "is_pretax": deduction.is_pretax,
            "amount": amount,
            "employer_contribution_rate": deduction.employer_rate,
        }
        serialized_deductions.append(serialized_deduction)
    for deduction in post_tax_deductions:
        if deduction.based_on == "net_pay":
            serialized_net_pay_deduction = {"deduction": deduction}
            serialized_net_pay_deductions.append(serialized_net_pay_deduction)
    return {
        "post_tax_deductions": serialized_deductions,
        "net_pay_deduction": serialized_net_pay_deductions,
        "installments": installments,
    }


def calculate_net_pay_deduction(net_pay, net_pay_deductions, **kwargs):
    """
    Calculates the deductions based on the net pay amount.

    Args:
        net_pay (float): The net pay amount.
        net_pay_deductions (list): List of net pay deductions.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        dict: A dictionary containing the serialized deductions and deduction amount.
    """
    day_dict = kwargs["day_dict"]
    serialized_net_pay_deductions = []
    deductions = [item["deduction"] for item in net_pay_deductions]
    deduction_amt = []
    for deduction in deductions:
        amount = calculate_based_on_net_pay(deduction, net_pay, day_dict)
        kwargs["amount"] = amount
        kwargs["component"] = deduction
        amount = if_condition_on(**kwargs)
        deduction_amt.append(amount)
    net_deduction = 0
    for deduction, amount in zip(deductions, deduction_amt):
        serialized_deduction = {
            "deduction_id": deduction.id,
            "title": deduction.title,
            "is_pretax": deduction.is_pretax,
            "amount": amount,
            "employer_contribution_rate": deduction.employer_rate,
        }
        net_deduction = amount + net_deduction
        serialized_net_pay_deductions.append(serialized_deduction)
    return {
        "net_pay_deductions": serialized_net_pay_deductions,
        "net_deduction": net_deduction,
    }


def if_condition_on(*_args, **kwargs):
    """
    This method is used to check the allowance or deduction through the the conditions

    Args:
        employee (obj): Employee instance
        amount (float): calculated amount of the component
        component (obj): Allowance or Deduction instance
        start_date (obj): Start date of the period
        end_date (obj): End date of the period

    Returns:
        _type_: _description_
    """
    component = kwargs["component"]
    basic_pay = kwargs["basic_pay"]
    amount = kwargs["amount"]
    gross_pay = 0
    amount = float(amount)
    if not isinstance(component, Allowance):
        gross_pay = calculate_gross_pay(
            **kwargs,
        )["gross_pay"]
    condition_value = basic_pay if component.if_choice == "basic_pay" else gross_pay
    if component.if_condition == "range":
        if not component.start_range <= condition_value <= component.end_range:
            amount = 0
    else:
        operator_func = operator_mapping.get(component.if_condition)
        if not operator_func(condition_value, component.if_amount):
            amount = 0
    return amount


def calculate_based_on_basic_pay(*_args, **kwargs):
    """
    Calculate the amount of an allowance or deduction based on the employee's
    basic pay with rate provided in the allowance or deduction object

    Args:
        employee (Employee): The employee object for whom to calculate the amount.
        start_date (datetime.date): The start date of the period for which to calculate the amount.
        end_date (datetime.date): The end date of the period for which to calculate the amount.
        component (Component): The allowance or deduction object that defines the rate or percentage
        to apply.

    Returns:
        The calculated allowance or deduction amount based on the employee's basic pay.

    """
    component = kwargs["component"]
    basic_pay = kwargs["basic_pay"]
    day_dict = kwargs["day_dict"]
    rate = component.rate
    amount = basic_pay * rate / 100
    amount = compute_limit(component, amount, day_dict)

    return amount


def calculate_based_on_gross_pay(*_args, **kwargs):
    """
    Calculate the amount of an allowance or deduction based on the employee's gross pay with rate
    provided in the allowance or deduction object

    Args:
        employee (Employee): The employee object for whom to calculate the amount.
        start_date (datetime.date): The start date of the period for which to calculate the amount.
        end_date (datetime.date): The end date of the period for which to calculate the amount.
        component (Component): The allowance or deduction object that defines the rate or percentage
        to apply.

    Returns:+-
        The calculated allowance or deduction amount based on the employee's gross pay.

    """

    component = kwargs["component"]
    day_dict = kwargs["day_dict"]
    gross_pay = calculate_gross_pay(**kwargs)
    rate = component.rate
    amount = gross_pay["gross_pay"] * rate / 100
    amount = compute_limit(component, amount, day_dict)
    return amount


def calculate_based_on_taxable_gross_pay(*_args, **kwargs):
    """
    Calculate the amount of an allowance or deduction based on the employee's taxable gross pay with
    rate provided in the allowance or deduction object

    Args:
        employee (Employee): The employee object for whom to calculate the amount.
        start_date (datetime.date): The start date of the period for which to calculate the amount.
        end_date (datetime.date): The end date of the period for which to calculate the amount.
        component (Component): The allowance or deduction object that defines the rate or percentage
        to apply.

    Returns:
        The calculated component amount based on the employee's taxable gross pay.

    """
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]
    taxable_gross_pay = calculate_taxable_gross_pay(**kwargs)
    taxable_gross_pay = taxable_gross_pay["taxable_gross_pay"]
    rate = component.rate
    amount = taxable_gross_pay * rate / 100
    amount = compute_limit(component, amount, day_dict)
    return amount


def calculate_based_on_net_pay(component, net_pay, day_dict):
    """
    Calculates the amount of an allowance or deduction based on the net pay of an employee.

    Args:
        component (Allowance or Deduction): The allowance or deduction object.
        net_pay (float): The net pay of the employee.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the component based on the net pay.
    """
    rate = float(component.rate)
    amount = net_pay * rate / 100
    amount = compute_limit(component, amount, day_dict)
    return amount


def calculate_based_on_attendance(*_args, **kwargs):
    """
    Calculates the amount of an allowance or deduction based on the attendance of an employee.

    Args:
        employee (Employee): The employee for whom the attendance is being calculated.
        start_date (date): The start date of the attendance period.
        end_date (date): The end date of the attendance period.
        component (Allowance or Deduction): The allowance or deduction object.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the component based on the attendance.
    """

    if not apps.is_installed("attendance"):
        return 0

    Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]

    count = Attendance.objects.filter(
        employee_id=employee,
        attendance_date__range=(start_date, end_date),
        attendance_validated=True,
    ).count()
    amount = count * component.per_attendance_fixed_amount
    amount = compute_limit(component, amount, day_dict)
    return amount


def calculate_based_on_shift(*_args, **kwargs):
    """
    Calculates the amount of an allowance or deduction based on the employee's shift attendance.

    Args:
        employee (Employee): The employee for whom the shift attendance is being calculated.
        start_date (date): The start date of the attendance period.
        end_date (date): The end date of the attendance period.
        component (Allowance or Deduction): The allowance or deduction object.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the component based on the shift attendance.
    """
    if not apps.is_installed("attendance"):
        return 0

    Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]

    shift_id = component.shift_id.id
    count = Attendance.objects.filter(
        employee_id=employee,
        shift_id=shift_id,
        attendance_date__range=(start_date, end_date),
        attendance_validated=True,
    ).count()
    amount = count * component.shift_per_attendance_amount

    amount = compute_limit(component, amount, day_dict)
    return amount


def calculate_based_on_overtime(*_args, **kwargs):
    """
    Calculates the amount of an allowance or deduction based on employee's overtime hours.

    Args:
        employee (Employee): The employee for whom the overtime is being calculated.
        start_date (date): The start date of the overtime period.
        end_date (date): The end date of the overtime period.
        component (Allowance or Deduction): The allowance or deduction object.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the allowance or deduction based on the overtime hours.
    """
    if not apps.is_installed("attendance"):
        return 0

    Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]

    attendances = Attendance.objects.filter(
        employee_id=employee,
        attendance_date__range=(start_date, end_date),
        attendance_overtime_approve=True,
    )
    overtime = sum(attendance.overtime_second for attendance in attendances)
    amount_per_hour = component.amount_per_one_hr
    amount_per_second = amount_per_hour / (60 * 60)
    amount = overtime * amount_per_second
    amount = round(amount, 2)

    amount = compute_limit(component, amount, day_dict)

    return amount


def calculate_based_on_work_type(*_args, **kwargs):
    """
    Calculates the amount of an allowance or deduction based on the employee's
    attendance with a specific work type.

    Args:
        employee (Employee): The employee for whom the attendance is being considered.
        start_date (date): The start date of the attendance period.
        end_date (date): The end date of the attendance period.
        component (Allowance or Deduction): The allowance or deduction object.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the allowance or deduction based on the
               attendance with the specified work type.
    """
    if not apps.is_installed("attendance"):
        return 0

    Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]

    work_type_id = component.work_type_id.id
    count = Attendance.objects.filter(
        employee_id=employee,
        work_type_id=work_type_id,
        attendance_date__range=(start_date, end_date),
        attendance_validated=True,
    ).count()
    amount = count * component.work_type_per_attendance_amount

    amount = compute_limit(component, amount, day_dict)

    return amount


def calculate_based_on_children(*_args, **kwargs):
    """
    Calculates the amount of an allowance or deduction based on the attendance of an employee.

    Args:
        employee (Employee): The employee for whom the attendance is being calculated.
        start_date (date): The start date of the attendance period.
        end_date (date): The end date of the attendance period.
        component (Allowance or Deduction): The allowance or deduction object.
        day_dict (dict): Dictionary containing working day details.

    Returns:
        float: The calculated amount of the component based on the attendance.
    """
    employee = kwargs["employee"]
    component = kwargs["component"]
    day_dict = kwargs["day_dict"]
    count = employee.children
    amount = count * component.per_children_fixed_amount
    amount = compute_limit(component, amount, day_dict)
    return amount


calculation_mapping = {
    "basic_pay": calculate_based_on_basic_pay,
    "gross_pay": calculate_based_on_gross_pay,
    "taxable_gross_pay": calculate_based_on_taxable_gross_pay,
    "net_pay": calculate_based_on_net_pay,
    "attendance": calculate_based_on_attendance,
    "shift_id": calculate_based_on_shift,
    "overtime": calculate_based_on_overtime,
    "work_type_id": calculate_based_on_work_type,
    "children": calculate_based_on_children,
}
