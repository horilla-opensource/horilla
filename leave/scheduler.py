import calendar
import datetime as dt
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def leave_reset():
    from leave.models import LeaveType

    today_date = today.date()
    leave_types = LeaveType.objects.filter(reset=True)
    # Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        # #Looping through all available leaves
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
            if expired_date == today_date:
                new_expired_date = available_leave.set_expired_date(
                    available_leave=available_leave, assigned_date=today_date
                )
                available_leave.expired_date = new_expired_date
                available_leave.save()


def recurring_holiday():
    from leave.models import Holiday

    recurring_holidays = Holiday.objects.filter(recurring=True)
    # Looping through all recurring holiday
    for recurring_holiday in recurring_holidays:
        start_date = recurring_holiday.start_date
        end_date = recurring_holiday.end_date
        new_start_date = dt.date(start_date.year + 1, start_date.month, start_date.day)
        new_end_date = dt.date(end_date.year + 1, end_date.month, end_date.day)
        # Checking that end date is not none
        if end_date is None:
            # checking if that start date is day before today
            if start_date == (today - timedelta(days=1)).date():
                recurring_holiday.start_date = new_start_date
        elif end_date == (today - timedelta(days=1)).date():
            recurring_holiday.start_date = new_start_date
            recurring_holiday.end_date = new_end_date
        recurring_holiday.save()


scheduler = BackgroundScheduler()
scheduler.add_job(leave_reset, "interval", hours=4)
scheduler.add_job(recurring_holiday, "interval", hours=4)

scheduler.start()
