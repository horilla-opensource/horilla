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

    working_days_details = months_between_range(basic_pay, last_working_date, notice_end_date)
    allowance_data_set = {
        "employee": employee,
        "start_date": last_working_date,
        "end_date": notice_end_date,
        "basic_pay": basic_pay,
        "day_dict": working_days_details,
    }
    allowance_data = calculate_allowance(**allowance_data_set)

    total_includable_allowances = sum(
        allowance["amount"]
        for allowance in allowance_data["allowances"]
        if allowance["include_in_lop"]
    )

    per_day_amount = ((basic_pay or 0) + (total_includable_allowances or 0)) / 30

    amount_for_fine = per_day_amount * payable_days

    off_emp = OffboardingEmployee.objects.filter(employee_id=employee).first()

    if amount_for_fine > 0:
        try:
            with transaction.atomic():
                deduction_task, _ = OffboardingTask.objects.get_or_create(
                    title="Salary deduction due to early resignation",
                    stage_id=None,
                    defaults={"is_fine": True},
                )
                if not deduction_task.is_fine:
                    deduction_task.is_fine = True
                    deduction_task.save(update_fields=["is_fine"])

                if off_emp:
                    description = f"Salary deduction of {amount_for_fine:.2f} due to early resignation."

                    existing_emp_task = EmployeeTask.objects.filter(
                        employee_id=off_emp,
                        task_id__is_fine=True,
                    ).first()

                    if existing_emp_task:
                        EmployeeTask.objects.filter(pk=existing_emp_task.pk).update(
                            description=description
                        )
                    else:
                        EmployeeTask.objects.bulk_create(
                            [
                                EmployeeTask(
                                    employee_id=off_emp,
                                    task_id=deduction_task,
                                    status="todo",
                                    description=description,
                                )
                            ],
                            ignore_conflicts=True,
                        )
        except Exception as e:
            logger.error("Error creating deduction task: %s", e)
    else:
        if off_emp:
            EmployeeTask.objects.filter(
                employee_id=off_emp,
                task_id__is_fine=True,
            ).delete()

    return amount_for_fine


def assign_task_to_stage_employees(sender, instance, created, **kwargs):
    """
    Helper to automatically assign a new OffboardingTask
    to existing OffboardingEmployees in that task's stage.
    """
    if created:
        if instance.is_fine:
            return

        from django.db.models import Q
        # If stage_id is null, it typically applies to all stages
        if instance.stage_id:
            employees = OffboardingEmployee.objects.filter(stage_id=instance.stage_id)
        else:
            employees = OffboardingEmployee.objects.all()

        # Prepare EmployeeTask instances for bulk creation to avoid
        # issuing one query (and one save/notification) per employee.
        employee_tasks = [
            EmployeeTask(
                employee_id=employee,
                task_id=instance,
                status="todo",
            )
            for employee in employees
        ]

        if employee_tasks:
            EmployeeTask.objects.bulk_create(
                employee_tasks,
                ignore_conflicts=True,
            )
