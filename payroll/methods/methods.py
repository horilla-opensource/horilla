"""
methods.py

Payroll related module to write custom calculation methods
"""

import calendar
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.paginator import Paginator
from django.db.models import F, Q

# from attendance.models import Attendance
from base.methods import (
    get_company_leave_dates,
    get_date_range,
    get_holiday_dates,
    get_pagination,
    get_working_days,
)
from base.models import CompanyLeaves, Holidays
from horilla.methods import get_horilla_model_class
from payroll.models.models import Contract, Deduction, Payslip


def get_total_days(start_date, end_date):
    """
    Calculates the total number of days in a given period.

    Args:
        start_date (date): The start date of the period.

        end_date (date): The end date of the period.
    Returns:
        int: The total number of days in the period, including the end date.

    Example:
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 10)
        days_on_period = get_total_days(start_date, end_date)
    """
    delta = end_date - start_date
    total_days = delta.days + 1  # Add 1 to include the end date itself
    return total_days


def get_leaves(employee, start_date, end_date):
    """
    This method is used to return all the leaves taken by the employee
    between the period.

    Args:
        employee (obj): Employee model instance
        start_date (obj): the start date from the data needed
        end_date (obj): the end date till the date needed
    """
    if apps.is_installed("leave"):
        approved_leaves = employee.leaverequest_set.filter(status="approved")
    else:
        approved_leaves = None
    paid_leave = 0
    unpaid_leave = 0
    paid_half = 0
    unpaid_half = 0
    paid_leave_dates = []
    unpaid_leave_dates = []
    company_leave_dates = get_working_days(start_date, end_date)["company_leave_dates"]

    if approved_leaves and approved_leaves.exists():
        for instance in approved_leaves:
            if instance.leave_type_id.payment == "paid":
                # if the taken leave is paid
                # for the start date
                all_the_paid_leave_taken_dates = instance.requested_dates()
                paid_leave_dates = paid_leave_dates + [
                    date
                    for date in all_the_paid_leave_taken_dates
                    if start_date <= date <= end_date
                ]
            else:
                # if the taken leave is unpaid
                # for the start date
                all_unpaid_leave_taken_dates = instance.requested_dates()
                unpaid_leave_dates = unpaid_leave_dates + [
                    date
                    for date in all_unpaid_leave_taken_dates
                    if start_date <= date <= end_date
                ]

    half_day_data = find_half_day_leaves()

    unpaid_half = half_day_data["half_unpaid_leaves"]
    paid_half = half_day_data["half_paid_leaves"]

    paid_leave_dates = list(set(paid_leave_dates) - set(company_leave_dates))
    unpaid_leave_dates = list(set(unpaid_leave_dates) - set(company_leave_dates))
    paid_leave = len(paid_leave_dates) - paid_half
    unpaid_leave = len(unpaid_leave_dates) - unpaid_half

    return {
        "paid_leave": paid_leave,
        "unpaid_leaves": unpaid_leave,
        "total_leaves": paid_leave + unpaid_leave,
        # List of paid leave date between range
        "paid_leave_dates": paid_leave_dates,
        # List of un paid date between range
        "unpaid_leave_dates": unpaid_leave_dates,
        "leave_dates": unpaid_leave_dates + paid_leave_dates,
    }


if apps.is_installed("attendance"):

    def get_attendance(employee, start_date, end_date):
        """
        This method is used to render attendance details between the range

        Args:
            employee (obj): Employee user instance
            start_date (obj): start date of the period
            end_date (obj): end date of the period
        """
        Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
        attendances_on_period = Attendance.objects.filter(
            employee_id=employee,
            attendance_date__range=(start_date, end_date),
            attendance_validated=True,
        )
        present_on = [
            attendance.attendance_date for attendance in attendances_on_period
        ]
        working_days_between_range = get_working_days(start_date, end_date)[
            "working_days_on"
        ]
        leave_dates = get_leaves(employee, start_date, end_date)["leave_dates"]
        conflict_dates = list(
            set(working_days_between_range)
            - set(attendances_on_period)
            - set(leave_dates)
        )
        conflict_dates = conflict_dates + [
            date
            for date in present_on
            if date in get_holiday_dates(start_date, end_date)
            or date
            in list(
                set(
                    get_company_leave_dates(start_date.year)
                    + get_company_leave_dates(end_date.year)
                )
            )
        ]

        return {
            "attendances_on_period": attendances_on_period,
            "present_on": present_on,
            "conflict_dates": conflict_dates,
        }


def hourly_computation(employee, wage, start_date, end_date):
    """
    Hourly salary computation for period.

    Args:
        employee (obj): Employee instance
        wage (float): wage of the employee
        start_date (obj): start of the pay period
        end_date (obj): end date of the period
    """
    if not apps.is_installed("attendance"):
        return {
            "basic_pay": 0,
            "loss_of_pay": 0,
        }
    attendance_data = get_attendance(employee, start_date, end_date)
    attendances_on_period = attendance_data["attendances_on_period"]
    total_worked_hour_in_second = 0
    for attendance in attendances_on_period:
        total_worked_hour_in_second = total_worked_hour_in_second + (
            attendance.at_work_second - attendance.overtime_second
        )

    # to find wage per second
    # wage_per_second = wage_per_hour / total_seconds_in_hour
    wage_in_second = wage / 3600
    basic_pay = float(f"{(wage_in_second * total_worked_hour_in_second):.2f}")

    return {
        "basic_pay": basic_pay,
        "loss_of_pay": 0,
        "paid_days": len(attendances_on_period),
        "unpaid_days": 0,
    }


def find_half_day_leaves():
    """
    This method is used to return the half day leave details

    Args:
        employee (obj): Employee model instance
        start_date (obj): start date of the period
        end_date (obj): end date of the period
    """
    paid_queryset = []
    unpaid_queryset = []

    paid_leaves = list(filter(None, list(set(paid_queryset))))
    unpaid_leaves = list(filter(None, list(set(unpaid_queryset))))

    paid_half = len(paid_leaves) * 0.5
    unpaid_half = len(unpaid_leaves) * 0.5
    queryset = paid_leaves + unpaid_leaves
    total_leaves = len(queryset) * 0.50
    return {
        "half_day_query_set": queryset,
        "half_day_leaves": total_leaves,
        "half_paid_leaves": paid_half,
        "half_unpaid_leaves": unpaid_half,
    }


def daily_computation(employee, wage, start_date, end_date):
    """
    Hourly salary computation for period.

    Args:
        employee (obj): Employee instance
        wage (float): wage of the employee
        start_date (obj): start of the pay period
        end_date (obj): end date of the period
    """
    working_day_data = get_working_days(start_date, end_date)
    total_working_days = working_day_data["total_working_days"]

    leave_data = get_leaves(employee, start_date, end_date)

    contract = employee.contract_set.filter(contract_status="active").first()
    basic_pay = wage * total_working_days
    loss_of_pay = 0

    date_range = get_date_range(start_date, end_date)
    half_day_leaves_between_period_on_start_date = (
        employee.leaverequest_set.filter(
            leave_type_id__payment="unpaid",
            start_date__in=date_range,
            status="approved",
        )
        .exclude(start_date_breakdown="full_day")
        .count()
    )

    half_day_leaves_between_period_on_end_date = (
        employee.leaverequest_set.filter(
            leave_type_id__payment="unpaid", end_date__in=date_range, status="approved"
        )
        .exclude(end_date_breakdown="full_day")
        .exclude(start_date=F("end_date"))
        .count()
    )
    unpaid_half_leaves = (
        half_day_leaves_between_period_on_start_date
        + half_day_leaves_between_period_on_end_date
    ) * 0.5

    contract = employee.contract_set.filter(
        is_active=True, contract_status="active"
    ).first()

    unpaid_leaves = leave_data["unpaid_leaves"] - unpaid_half_leaves
    if contract.calculate_daily_leave_amount:
        loss_of_pay = (unpaid_leaves) * wage
    else:
        fixed_penalty = contract.deduction_for_one_leave_amount
        loss_of_pay = (unpaid_leaves) * fixed_penalty
    if contract.deduct_leave_from_basic_pay:
        basic_pay = basic_pay - loss_of_pay

    return {
        "basic_pay": basic_pay,
        "loss_of_pay": loss_of_pay,
        "paid_days": total_working_days,
        "unpaid_days": unpaid_leaves,
    }


def get_daily_salary(wage, wage_date) -> dict:
    """
    This method is used to calculate daily salary for the date
    """
    last_day = calendar.monthrange(wage_date.year, wage_date.month)[1]
    end_date = date(wage_date.year, wage_date.month, last_day)
    start_date = date(wage_date.year, wage_date.month, 1)
    working_days = get_working_days(start_date, end_date)["total_working_days"]
    day_wage = (
        wage / working_days if working_days else 0.0
    )  # if working_days != 0 else 0 #769

    return {
        "day_wage": day_wage,
    }


def months_between_range(wage, start_date, end_date):
    """
    This method is used to find the months between range
    """
    months_data = []

    for current_date in (
        start_date + relativedelta(months=i)
        for i in range(
            (end_date.year - start_date.year) * 12
            + end_date.month
            - start_date.month
            + 1
        )
    ):
        month = current_date.month
        year = current_date.year

        days_in_month = (
            current_date + relativedelta(day=1, months=1) - relativedelta(days=1)
        ).day

        # Calculate the end date for the current month
        current_end_date = current_date + relativedelta(day=days_in_month)
        current_end_date = min(current_end_date, end_date)
        working_days_on_month = get_working_days(
            current_date.replace(day=1), current_date.replace(day=days_in_month)
        )["total_working_days"]

        month_start_date = (
            date(year=year, month=month, day=1)
            if start_date < date(year=year, month=month, day=1)
            else start_date
        )
        total_working_days_on_period = get_working_days(
            month_start_date, current_end_date
        )["total_working_days"]

        month_info = {
            "month": month,
            "year": year,
            "days": days_in_month,
            "start_date": month_start_date.strftime("%Y-%m-%d"),
            "end_date": current_end_date.strftime("%Y-%m-%d"),
            # month period
            "working_days_on_period": total_working_days_on_period,
            "working_days_on_month": working_days_on_month,
            "per_day_amount": (
                wage / working_days_on_month if working_days_on_month else 0.0
            ),
            # if working_days_on_month != 0 else 0 #769,
        }

        months_data.append(month_info)
        # Set the start date for the next month as the first day of the next month
        current_date = (current_date + relativedelta(day=1, months=1)).replace(day=1)

    return months_data


def compute_yearly_taxable_amount(
    monthly_taxable_amount=None,
    default_yearly_taxable_amount=None,
    *args,
    **kwargs,
):
    """
    Compute yearly taxable amount custom logic
    eg:
        default_yearly_taxable_amount = monthly_taxable_amount * 12
    """
    return default_yearly_taxable_amount


def convert_year_tax_to_period(
    federal_tax_for_period=None,
    yearly_tax=None,
    total_days=None,
    start_date=None,
    end_date=None,
    *args,
    **kwargs,
):
    """
    Method to convert yearly taxable to monthly
    """
    return federal_tax_for_period


def compute_net_pay(
    net_pay=None,
    gross_pay=None,
    total_pretax_deduction=None,
    total_post_tax_deduction=None,
    total_tax_deductions=None,
    federal_tax=None,
    loss_of_pay_amount=None,
    *args,
    **kwargs,
):
    """
    Compute net pay | Additional logic
    """

    return net_pay


def monthly_computation(employee, wage, start_date, end_date, *args, **kwargs):
    """
    Hourly salary computation for period.

    Args:
        employee (obj): Employee instance
        wage (float): wage of the employee
        start_date (obj): start of the pay period
        end_date (obj): end date of the period
    """
    basic_pay = 0
    month_data = months_between_range(wage, start_date, end_date)

    leave_data = get_leaves(employee, start_date, end_date)

    for data in month_data:
        basic_pay = basic_pay + (
            data["working_days_on_period"] * data["per_day_amount"]
        )

    contract = employee.contract_set.filter(contract_status="active").first()
    loss_of_pay = 0
    date_range = get_date_range(start_date, end_date)
    if apps.is_installed("leave"):
        start_date_leaves = (
            employee.leaverequest_set.filter(
                leave_type_id__payment="unpaid",
                start_date__in=date_range,
                status="approved",
            )
            .exclude(start_date_breakdown="full_day")
            .count()
        )
        end_date_leaves = (
            employee.leaverequest_set.filter(
                leave_type_id__payment="unpaid",
                end_date__in=date_range,
                status="approved",
            )
            .exclude(end_date_breakdown="full_day")
            .exclude(start_date=F("end_date"))
            .count()
        )
    else:
        start_date_leaves = 0
        end_date_leaves = 0

    half_day_leaves_between_period_on_start_date = start_date_leaves

    half_day_leaves_between_period_on_end_date = end_date_leaves

    unpaid_half_leaves = (
        half_day_leaves_between_period_on_start_date
        + half_day_leaves_between_period_on_end_date
    ) * 0.5

    contract = employee.contract_set.filter(
        is_active=True, contract_status="active"
    ).first()
    unpaid_leaves = abs(leave_data["unpaid_leaves"] - unpaid_half_leaves)
    paid_days = month_data[0]["working_days_on_period"] - unpaid_leaves
    daily_computed_salary = get_daily_salary(wage=wage, wage_date=start_date)[
        "day_wage"
    ]
    if contract.calculate_daily_leave_amount:
        loss_of_pay = (unpaid_leaves) * daily_computed_salary
    else:
        fixed_penalty = contract.deduction_for_one_leave_amount
        loss_of_pay = (unpaid_leaves) * fixed_penalty

    if contract.deduct_leave_from_basic_pay:
        basic_pay = basic_pay - loss_of_pay
    return {
        "basic_pay": basic_pay,
        "loss_of_pay": loss_of_pay,
        "month_data": month_data,
        "unpaid_days": unpaid_leaves,
        "paid_days": paid_days,
        "contract": contract,
    }


def compute_salary_on_period(employee, start_date, end_date, wage=None):
    """
    This method is used to compute salary on the start to end date period

    Args:
        employee (obj): Employee instance
        start_date (obj): start date of the period
        end_date (obj): end date of the period
    """
    contract = Contract.objects.filter(
        employee_id=employee, contract_status="active"
    ).first()
    if contract is None:
        return contract

    wage = contract.wage if wage is None else wage
    wage_type = contract.wage_type
    data = None
    if wage_type == "hourly":
        data = hourly_computation(employee, wage, start_date, end_date)
        month_data = months_between_range(wage, start_date, end_date)
        data["month_data"] = month_data
    elif wage_type == "daily":
        data = daily_computation(employee, wage, start_date, end_date)
        month_data = months_between_range(wage, start_date, end_date)
        data["month_data"] = month_data

    else:
        data = monthly_computation(employee, wage, start_date, end_date)
    data["contract_wage"] = wage
    data["contract"] = contract
    return data


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


def calculate_employer_contribution(data):
    """
    This method is used to calculate the employer contribution
    """
    pay_head_data = data["pay_data"]
    deductions_to_process = [
        pay_head_data.get("pretax_deductions"),
        pay_head_data.get("post_tax_deductions"),
        pay_head_data.get("tax_deductions"),
        pay_head_data.get("net_deductions"),
    ]

    for deductions in deductions_to_process:
        if deductions:
            for deduction in deductions:
                if (
                    deduction.get("deduction_id")
                    and deduction.get("employer_contribution_rate", 0) > 0
                ):
                    object = Deduction.objects.filter(
                        id=deduction.get("deduction_id")
                    ).first()
                    if object:
                        amount = pay_head_data.get(object.based_on)
                        employer_contribution_amount = (
                            amount * object.employer_rate
                        ) / 100
                        deduction["based_on"] = object.based_on
                        deduction["employer_contribution_amount"] = (
                            employer_contribution_amount
                        )
    return data


def save_payslip(**kwargs):
    """
    This method is used to save the generated payslip
    """
    filtered_instance = Payslip.objects.filter(
        employee_id=kwargs["employee"],
        start_date=kwargs["start_date"],
        end_date=kwargs["end_date"],
    ).first()
    instance = filtered_instance if filtered_instance is not None else Payslip()
    instance.employee_id = kwargs["employee"]
    instance.group_name = kwargs.get("group_name")
    instance.start_date = kwargs["start_date"]
    instance.end_date = kwargs["end_date"]
    instance.status = kwargs["status"]
    instance.basic_pay = round(kwargs["basic_pay"], 2)
    instance.contract_wage = round(kwargs["contract_wage"], 2)
    instance.gross_pay = round(kwargs["gross_pay"], 2)
    instance.deduction = round(kwargs["deduction"], 2)
    instance.net_pay = round(kwargs["net_pay"], 2)
    instance.pay_head_data = kwargs["pay_data"]
    instance.save()
    instance.installment_ids.set(kwargs["installments"])
    return instance
