import sys
import logging
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler

from horilla.signals import post_scheduler, pre_scheduler

logger = logging.getLogger(__name__)


def leave_monthly_accrual():
    """
    Process monthly leave accrual for all active employees.
    Credits 2.5 days to employees on their anniversary month.
    Only runs if employee has 30+ days of service and in anniversary month.
    """
    pre_scheduler.send(sender=leave_monthly_accrual)
    
    try:
        from leave.models import AvailableLeave, LeaveType
        from leave.accrual_service import (
            is_service_eligible_for_accrual,
            get_employee_category,
            create_accrual_audit_log,
            get_accrual_config,
        )
        from employee.models import Employee

        today = date.today()
        accrual_config = get_accrual_config()
        
        if not accrual_config or not accrual_config.active:
            return

        # Find annual leave types for accrual
        leave_types = LeaveType.objects.filter(name__icontains="annual").order_by("id")
        
        if not leave_types.exists():
            # Fallback: use any non-compensatory leave type
            leave_types = LeaveType.objects.filter(
                is_compensatory_leave=False
            ).order_by("id")[:1]

        active_employees = Employee.objects.filter(is_active=True)

        for employee in active_employees:
            # Check if employee is eligible for accrual
            if not is_service_eligible_for_accrual(employee, today):
                continue

            # Process accrual for each leave type
            for leave_type in leave_types:
                try:
                    available_leave, _ = AvailableLeave.objects.get_or_create(
                        employee_id=employee,
                        leave_type_id=leave_type,
                    )

                    # Check if already accrued this month
                    if not available_leave.is_accrual_eligible(today):
                        continue

                    # Proceed with accrual
                    old_balance = available_leave.available_days
                    available_leave.available_days += float(accrual_config.monthly_accrual_days)
                    available_leave.total_leave_days = round(
                        available_leave.available_days + available_leave.carryforward_days, 2
                    )
                    available_leave.last_accrual_date = today
                    available_leave.save()

                    # Create audit log
                    create_accrual_audit_log(
                        employee=employee,
                        accrual_type="monthly_accrual",
                        old_balance=old_balance,
                        new_balance=available_leave.available_days,
                        reason=f"Monthly accrual - {accrual_config.monthly_accrual_days} days credited on anniversary month ({today.strftime('%B %d')})",
                        effective_date=today,
                        leave_type=leave_type,
                        created_by=None,  # System-generated
                    )

                    logger.info(
                        f"Accrual: {employee.badge_id} credited {accrual_config.monthly_accrual_days} days for {leave_type.name}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing accrual for employee {employee.badge_id}: {str(e)}"
                    )
                    continue

    except Exception as e:
        logger.error(f"Error in leave_monthly_accrual: {str(e)}")

    post_scheduler.send(sender=leave_monthly_accrual)


def leave_annual_reset():
    """
    Process annual December 31 reset for leave carryforward limits.
    Enforces category-based max carryforward (30 days for Management, 60 for Normal).
    Creates audit logs for all reductions.
    """
    pre_scheduler.send(sender=leave_annual_reset)
    
    try:
        from leave.models import AvailableLeave
        from leave.accrual_service import (
            get_employee_category,
            create_accrual_audit_log,
            get_accrual_config,
        )

        today = date.today()
        accrual_config = get_accrual_config()

        # Check if today is the annual reset date
        if not (today.month == accrual_config.annual_reset_month and 
                today.day == accrual_config.annual_reset_day):
            return

        logger.info(f"Starting annual leave reset on {today}")

        available_leaves = AvailableLeave.objects.all()

        for available_leave in available_leaves:
            try:
                employee = available_leave.employee_id
                category = get_employee_category(employee)
                max_carryforward = category.max_carryforward_days

                current_balance = available_leave.total_leave_days

                # Check if balance exceeds limit
                if current_balance > max_carryforward:
                    excess = current_balance - max_carryforward

                    # Calculate how much to remove from each type
                    carryforward_reduction = min(available_leave.carryforward_days, excess)
                    if carryforward_reduction < excess:
                        available_leave.available_days -= (excess - carryforward_reduction)
                    
                    available_leave.carryforward_days -= carryforward_reduction
                    available_leave.total_leave_days = round(
                        available_leave.available_days + available_leave.carryforward_days, 2
                    )
                    available_leave.save()

                    # Create audit log
                    create_accrual_audit_log(
                        employee=employee,
                        accrual_type="annual_reset",
                        old_balance=current_balance,
                        new_balance=available_leave.total_leave_days,
                        reason=f"Annual Carryforward Limit Reset - {category.name} category max {max_carryforward} days",
                        effective_date=today,
                        leave_type=available_leave.leave_type_id,
                        created_by=None,  # System-generated
                    )

                    logger.info(
                        f"Annual reset: {employee.badge_id} - reduced from {current_balance} to {available_leave.total_leave_days} days"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing annual reset for available_leave {available_leave.id}: {str(e)}"
                )
                continue

    except Exception as e:
        logger.error(f"Error in leave_annual_reset: {str(e)}")

    post_scheduler.send(sender=leave_annual_reset)


def leave_reset():
    pre_scheduler.send(sender=leave_reset)
    from leave.models import LeaveType

    today = datetime.now()
    today_date = today.date()
    leave_types = LeaveType.objects.filter(reset=True)
    # Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        # Looping through all available leaves
        available_leaves = leave_type.employee_available_leave.all()

        for available_leave in available_leaves:
            reset_date = available_leave.reset_date
            expired_date = available_leave.expired_date
            if reset_date == today_date:
                available_leave.update_carryforward()
                # new_reset_date = available_leave.set_reset_date(assigned_date=today_date,available_leave = available_leave)
                new_reset_date = available_leave.set_reset_date(
                    assigned_date=today_date, available_leave=available_leave
                )
                available_leave.reset_date = new_reset_date
                available_leave.save()
            if expired_date and expired_date <= today_date:
                new_expired_date = available_leave.set_expired_date(
                    available_leave=available_leave, assigned_date=today_date
                )
                available_leave.expired_date = new_expired_date
                available_leave.save()

        if (
            leave_type.carryforward_expire_date
            and leave_type.carryforward_expire_date <= today_date
        ):
            leave_type.carryforward_expire_date = leave_type.set_expired_date(
                today_date
            )
            leave_type.save()
    post_scheduler.send(
        sender=leave_reset,
        **{
            "today": today,
            "today_date": today_date,
            "leave_types": leave_types,
        }
    )


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    # Original leave reset job (every 4 hours)
    scheduler.add_job(leave_reset, "interval", hours=4)
    
    # New Royal Falcon accrual jobs
    # Monthly accrual - run daily to check for anniversary months
    scheduler.add_job(leave_monthly_accrual, "interval", hours=24)
    
    # Annual reset - run daily (will only execute on Dec 31)
    scheduler.add_job(leave_annual_reset, "interval", hours=24)

    scheduler.start()
