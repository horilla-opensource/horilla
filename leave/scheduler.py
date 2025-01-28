import calendar
import datetime as dt
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def leave_reset():
    from leave.models import LeaveType
    from employee.models import EmployeeWorkInformation

    today_date = today.date()
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
                    if next_anniversary < today_date:
                        next_anniversary = next_anniversary.replace(year=today_date.year + 1)
                    reset_date = next_anniversary

            if reset_date == today_date:
                available_leave.update_carryforward()
                available_leave.reset_date = reset_date  # Update reset_date if needed
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

    scheduler.start()
