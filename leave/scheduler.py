import calendar
import datetime as dt
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def update_anniversary_reset_dates():
    """
    Updates reset dates for anniversary-based leave types when anniversary dates change
    """
    from leave.models import AvailableLeave
    from employee.models import EmployeeWorkInformation
    
    today_date = today.date()
    
    # Get all employees with anniversary-based leaves
    available_leaves = AvailableLeave.objects.filter(
        leave_type_id__reset_based='anniversary',
        employee_id__employee_work_info__isnull=False
    ).select_related('employee_id__employee_work_info')
    
    for available_leave in available_leaves:
        work_info = available_leave.employee_id.employee_work_info
        if work_info and work_info.anniversary_date:
            # Calculate next anniversary date
            next_anniversary = work_info.anniversary_date.replace(year=today_date.year)
            if next_anniversary < today_date:
                next_anniversary = next_anniversary.replace(year=today_date.year + 1)
            
            # Update reset date if it's different
            if available_leave.reset_date != next_anniversary:
                available_leave.reset_date = next_anniversary
                available_leave.save()


def leave_reset():
    from leave.models import LeaveType, AvailableLeave
    from employee.models import EmployeeWorkInformation

    today_date = today.date()
    
    # Handle anniversary-based resets
    anniversary_leaves = AvailableLeave.objects.filter(
        leave_type_id__reset_based='anniversary',
        reset_date__lte=today_date
    )
    
    for available_leave in anniversary_leaves:
        # Reset available days
        available_leave.available_days = available_leave.leave_type_id.total_days
        
        # Calculate next reset date
        work_info = available_leave.employee_id.employee_work_info
        if work_info and work_info.anniversary_date:
            next_year = today_date.year + 1
            available_leave.reset_date = work_info.anniversary_date.replace(year=next_year)
            available_leave.save()

    leave_types = LeaveType.objects.filter(reset=True)
    # Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        # Skip if carryforward is not enabled
        if not leave_type.carryforward:
            continue
            
        expire_date = leave_type.set_expired_date(today_date)
        if expire_date:
            leave_type.carryforward_expire_date = expire_date
            leave_type.save()

        # Looping through all available leaves
        available_leaves = leave_type.employee_available_leave.all()

        for available_leave in available_leaves:
            reset_date = None
            expired_date = available_leave.expired_date

            if leave_type.reset_based == "anniversary":
                work_info = available_leave.employee_id.employee_work_info
                if work_info and work_info.anniversary_date:
                    anniversary_date = work_info.anniversary_date
                    next_anniversary = anniversary_date.replace(year=today_date.year)
                    # Check if the next anniversary is today
                    if next_anniversary == today_date:
                        reset_date = next_anniversary

            if reset_date == today_date:
                available_leave.update_carryforward()
                available_leave.reset_date = reset_date
                available_leave.save()
 
            if expired_date and expired_date <= today_date:
                new_expired_date = available_leave.set_expired_date(
                    available_leave=available_leave, assigned_date=today_date
                )
                available_leave.expired_date = new_expired_date
                available_leave.save()


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(leave_reset, "interval", seconds=20)
    # Add the new job to run every hour
    scheduler.add_job(update_anniversary_reset_dates, "interval", hours=1)

    scheduler.start()
