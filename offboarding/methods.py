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

logger = logging.getLogger(__name__)


def compute_resignation_balance(employee, last_working_date, notice_end_date):
    working_days = get_working_days(last_working_date, notice_end_date)
    payable_days = working_days.get("total_working_days", 0)

    contract = Contract.objects.filter(
        employee_id=employee, contract_status="termination_in_progress"
    ).first()
    if contract is None:
        return None

    basic_pay = contract.wage
    print("basic_pay:", basic_pay)

    working_days_details = months_between_range(basic_pay, last_working_date, notice_end_date)
    kwargs = {
        "employee": employee,
        "start_date": last_working_date,
        "end_date": notice_end_date,
        "basic_pay": basic_pay,
        "day_dict": working_days_details,
    }
    allowance_data = calculate_allowance(**kwargs)

    total_includable_allowances = sum(
        allowance["amount"]
        for allowance in allowance_data["allowances"]
        if allowance["include_in_lop"]
    )

    per_day_amount = (basic_pay + total_includable_allowances) / 30

    amount_for_fine = per_day_amount * payable_days

    if amount_for_fine > 0:
        try:
            with transaction.atomic():
                deduction_task, _ = OffboardingTask.objects.get_or_create(
                    title=f"Salary deduction of {amount_for_fine:.2f} due to early resignation.",
                    defaults={"stage_id": None},
                    is_fine=True
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
        except Exception as e:
                logger.error("Error creating deduction task: %s", e)
    return amount_for_fine

