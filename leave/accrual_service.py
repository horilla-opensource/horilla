"""
Leave accrual service methods for Royal Falcon Security leave policy.
Handles all calculations related to monthly accrual, service duration, and auditing.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q
from employee.models import Employee
from leave.models import (
    AvailableLeave,
    LeaveType,
    UnpaidLeave,
    UnauthorizedExtension,
    EmployeeServiceAdjustment,
    LeaveAccrualAuditLog,
    EmployeeCategory,
    LeaveAccrualConfiguration,
)


def get_employee_category(employee):
    """
    Determine employee category based on badge_id prefix.
    Falls back to Normal Employee if not found.
    """
    if not employee.badge_id:
        # Default to Normal Employee if no badge_id
        try:
            category = EmployeeCategory.objects.filter(
                badge_id_prefix="DEFAULT"
            ).first()
            if category:
                return category
        except:
            pass
        # Create or get default category
        category, _ = EmployeeCategory.objects.get_or_create(
            badge_id_prefix="DEFAULT",
            defaults={
                "name": "Normal Employee",
                "max_carryforward_days": 60,
            },
        )
        return category

    # Extract prefix from badge_id (e.g., "A-", "S-", "SD-")
    badge_prefix = employee.badge_id.split("-")[0] + "-" if "-" in employee.badge_id else employee.badge_id

    category = EmployeeCategory.objects.filter(badge_id_prefix=badge_prefix).first()

    if not category:
        # Default to Normal Employee
        category, _ = EmployeeCategory.objects.get_or_create(
            badge_id_prefix="DEFAULT",
            defaults={
                "name": "Normal Employee",
                "max_carryforward_days": 60,
            },
        )

    return category


def calculate_adjusted_service_days(employee, reference_date=None):
    """
    Calculate service days excluding unpaid leave and unauthorized extensions.
    Used to determine if employee is eligible for monthly accrual.

    Args:
        employee: Employee instance
        reference_date: Date to calculate service days up to (default: today)

    Returns:
        Number of days of actual service (excluding unpaid/unauthorized)
    """
    if reference_date is None:
        reference_date = date.today()

    if not employee.original_joining_date:
        # Fallback to date_joining if original_joining_date not set
        start_date = employee.employee_work_info.date_joining if employee.employee_work_info else None
        if not start_date:
            return 0
    else:
        start_date = employee.original_joining_date

    # Start with total service days
    service_days = (reference_date - start_date).days

    # Subtract unpaid leave days
    unpaid_leaves = UnpaidLeave.objects.filter(
        employee_id=employee,
        status__in=["active", "returned"],
        start_date__lte=reference_date,
    )
    for ul in unpaid_leaves:
        end = min(ul.end_date, reference_date)
        if ul.start_date <= reference_date:
            days_to_subtract = (end - ul.start_date).days + 1
            service_days -= days_to_subtract

    # Subtract unauthorized extension days
    unauthorized = UnauthorizedExtension.objects.filter(
        employee_id=employee,
        status__in=["pending_review", "approved"],
        actual_return_date__lte=reference_date,
    )
    for ue in unauthorized:
        if ue.unauthorized_days:
            service_days -= int(ue.unauthorized_days)

    return max(service_days, 0)


def is_anniversary_month(employee, check_date=None):
    """
    Check if current month is the anniversary month for the employee.
    Anniversary is based on joining date month (not necessarily full year).

    Args:
        employee: Employee instance
        check_date: Date to check (default: today)

    Returns:
        True if check_date's month matches employee's joining month
    """
    if check_date is None:
        check_date = date.today()

    if not employee.original_joining_date:
        if employee.employee_work_info and employee.employee_work_info.date_joining:
            joining_date = employee.employee_work_info.date_joining
        else:
            return False
    else:
        joining_date = employee.original_joining_date

    return check_date.month == joining_date.month and check_date.day >= joining_date.day


def is_service_eligible_for_accrual(employee, check_date=None):
    """
    Check if employee has completed at least 30 days of service and is in anniversary month.
    Also ensures accrual isn't paused during this date.

    Args:
        employee: Employee instance
        check_date: Date to check (default: today)

    Returns:
        True if employee is eligible for accrual
    """
    if check_date is None:
        check_date = date.today()

    # Check if employee is active
    if not employee.is_active:
        return False

    # Calculate adjusted service days
    service_days = calculate_adjusted_service_days(employee, check_date)
    if service_days < 30:
        return False

    # Check if in anniversary month
    if not is_anniversary_month(employee, check_date):
        return False

    return True


def create_accrual_audit_log(employee, accrual_type, old_balance, new_balance, reason, effective_date=None, leave_type=None, created_by=None):
    """
    Create an immutable audit log entry for leave balance change.

    Args:
        employee: Employee instance
        accrual_type: Type of accrual (monthly_accrual, annual_reset, etc.)
        old_balance: Balance before change
        new_balance: Balance after change
        reason: Human-readable reason for change
        effective_date: Date when accrual took effect (default: today)
        leave_type: LeaveType affected (optional)
        created_by: Employee who triggered the change (optional)

    Returns:
        Created LeaveAccrualAuditLog instance
    """
    if effective_date is None:
        effective_date = date.today()

    accrual_days = new_balance - old_balance

    audit_log = LeaveAccrualAuditLog.objects.create(
        employee_id=employee,
        accrual_type=accrual_type,
        old_balance=float(old_balance),
        new_balance=float(new_balance),
        accrual_days=float(accrual_days),
        reason=reason,
        effective_date=effective_date,
        related_leave_type_id=leave_type,
        created_by=created_by,
    )

    return audit_log


def pause_accrual_for_unpaid_leave(unpaid_leave):
    """
    Pause accrual for employee during unpaid leave period.
    Updates AvailableLeave and creates EmployeeServiceAdjustment record.

    Args:
        unpaid_leave: UnpaidLeave instance
    """
    employee = unpaid_leave.employee_id

    # Update all AvailableLeave records to pause accrual
    available_leaves = AvailableLeave.objects.filter(employee_id=employee)
    for available_leave in available_leaves:
        available_leave.accrual_paused_until = unpaid_leave.end_date
        available_leave.save()

    # Create service adjustment record
    adjustment_days = (unpaid_leave.end_date - unpaid_leave.start_date).days + 1
    EmployeeServiceAdjustment.objects.create(
        employee_id=employee,
        adjustment_type="unpaid_leave_pause",
        start_date=unpaid_leave.start_date,
        end_date=unpaid_leave.end_date,
        days_excluded=adjustment_days,
        related_unpaid_leave_id=unpaid_leave,
        notes=f"Unpaid leave from {unpaid_leave.start_date} to {unpaid_leave.end_date}",
    )

    # Create audit logs for accrual pause
    create_accrual_audit_log(
        employee=employee,
        accrual_type="accrual_pause_start",
        old_balance=0,
        new_balance=0,
        reason=f"Accrual paused due to unpaid leave from {unpaid_leave.start_date} to {unpaid_leave.end_date}",
        effective_date=unpaid_leave.start_date,
        created_by=unpaid_leave.created_by,
    )


def resume_accrual_after_unpaid_leave(unpaid_leave):
    """
    Resume accrual for employee after unpaid leave ends.

    Args:
        unpaid_leave: UnpaidLeave instance (status should be 'returned')
    """
    employee = unpaid_leave.employee_id

    # Clear accrual pause
    available_leaves = AvailableLeave.objects.filter(employee_id=employee)
    for available_leave in available_leaves:
        available_leave.accrual_paused_until = None
        available_leave.save()

    # Create audit log for accrual resume
    create_accrual_audit_log(
        employee=employee,
        accrual_type="accrual_pause_end",
        old_balance=0,
        new_balance=0,
        reason=f"Accrual resumed after unpaid leave ended on {unpaid_leave.end_date}",
        effective_date=unpaid_leave.end_date,
        created_by=unpaid_leave.created_by,
    )


def create_unauthorized_extension_record(leave_request, actual_return_date, created_by=None):
    """
    Create unauthorized extension record when employee doesn't return on time.

    Args:
        leave_request: LeaveRequest instance (the approved paid leave)
        actual_return_date: Date when employee actually returned
        created_by: Employee/HR who created this record

    Returns:
        Created UnauthorizedExtension instance
    """
    approved_return_date = leave_request.end_date + timedelta(days=1)
    unauthorized_days = (actual_return_date - approved_return_date).days

    unauthorized_ext = UnauthorizedExtension.objects.create(
        employee_id=leave_request.employee_id,
        leave_request_id=leave_request,
        approved_return_date=approved_return_date,
        actual_return_date=actual_return_date,
        unauthorized_days=unauthorized_days,
        status="pending_review",
        created_by=created_by,
    )

    # Create service adjustment record
    EmployeeServiceAdjustment.objects.create(
        employee_id=leave_request.employee_id,
        adjustment_type="unauthorized_extension",
        start_date=approved_return_date,
        end_date=actual_return_date,
        days_excluded=unauthorized_days,
        related_unauthorized_extension_id=unauthorized_ext,
        notes=f"Unauthorized absence from {approved_return_date} to {actual_return_date} ({unauthorized_days} days)",
    )

    # Create audit log
    create_accrual_audit_log(
        employee=leave_request.employee_id,
        accrual_type="accrual_pause_start",
        old_balance=0,
        new_balance=0,
        reason=f"Accrual paused for {unauthorized_days} days of unauthorized absence from {approved_return_date} to {actual_return_date}",
        effective_date=approved_return_date,
        created_by=created_by,
    )

    return unauthorized_ext


def get_accrual_config(company=None):
    """
    Get leave accrual configuration for company.
    Creates default if not exists.

    Args:
        company: Company instance (optional)

    Returns:
        LeaveAccrualConfiguration instance
    """
    if not company:
        # Get first company with config, or create default
        config = LeaveAccrualConfiguration.objects.first()
        if config:
            return config
        # Create default
        from base.models import Company
        company = Company.objects.first()
        if not company:
            return None

    config, _ = LeaveAccrualConfiguration.objects.get_or_create(
        company_id=company,
        defaults={
            "monthly_accrual_days": Decimal("2.5"),
            "annual_reset_month": 12,
            "annual_reset_day": 31,
            "active": True,
        },
    )
    return config
