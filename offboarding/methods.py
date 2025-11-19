from django.db import transaction

from base.methods import (
    get_company_leave_dates,
    get_date_range,
    get_holiday_dates,
    get_pagination,
    get_working_days,
)
from offboarding.models import OffboardingEmployee, OffboardingTask, EmployeeTask
from payroll.methods.methods import get_attendance, get_leaves, months_between_range
from payroll.methods.payslip_calc import calculate_allowance
from payroll.models.models import Contract, Deduction, Payslip
import logging

from payroll.views.component_views import payroll_calculation

logger = logging.getLogger(__name__)


def compute_resignation_balance(employee,  last_working_date , notice_end_date):

    days_between = notice_end_date - last_working_date
    print("last working date" , last_working_date)
    print("notice end date" , notice_end_date)
    print("days_between", days_between.days)

    attendance = get_attendance(employee , last_working_date , notice_end_date)
    print("attendance", attendance)

    holiday_dates = get_holiday_dates(last_working_date, notice_end_date)
    print("holiday_dates", holiday_dates)

    leave_data = get_leaves(employee, last_working_date, notice_end_date)
    print("leave_data", leave_data)

    contract = Contract.objects.filter(
        employee_id=employee, contract_status="termination_in_progress"
    ).first()
    if contract is None:
        return contract

    basic_pay = contract.wage
    print("basic_pay", basic_pay)

    working_days_details = months_between_range(basic_pay, last_working_date, notice_end_date)
    print("Working days details", working_days_details)

    kwargs = {
        "employee": employee,
        "start_date": last_working_date,
        "end_date": notice_end_date,
        "basic_pay": basic_pay,
        "day_dict": working_days_details,
    }
    allowance_data = calculate_allowance(**kwargs)

    total_includable_allowances = sum(
        allowance["amount"] for allowance in allowance_data["allowances"] if allowance["include_in_lop"]
    )
    print("total_includable_allowances", total_includable_allowances)


    per_day_amount = (basic_pay + total_includable_allowances) / 30
    amount_for_fine = per_day_amount * days_between.days
    print("per_day_amount", per_day_amount)
    print("amount_for_fine", amount_for_fine)

    if amount_for_fine > 0:
        try:
            with transaction.atomic():
                deduction_task, _ = OffboardingTask.objects.get_or_create(
                    title=f"Salary deduction of {amount_for_fine:.2f} due to early resignation.",
                    defaults={"stage_id": None},
                )

                off_emp = OffboardingEmployee.objects.filter(employee_id=employee).first()
                if off_emp:
                    emp_task, created = EmployeeTask.objects.get_or_create(
                        employee_id=off_emp,
                        task_id=deduction_task,
                        defaults={
                            "status": "todo",
                            "description": f"Salary deduction of {amount_for_fine:.2f} due to early resignation.",
                        },
                    )
                    if created:
                        print(f"Offboarding task created for {employee}: {emp_task.description}")
                    else:
                        print(f"Task already exists for {employee}")
        except Exception as e:
            print(f" Error creating offboarding task: {e}")

    return amount_for_fine


