import datetime
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler


def update_experience():
    from employee.models import EmployeeWorkInformation

    """
    This scheduled task to trigger the experience calculator
    to update the employee work experience
    """
    queryset = EmployeeWorkInformation.objects.filter(employee_id__is_active=True)
    for instance in queryset:
        instance.experience_calculator()
    return


def block_unblock_disciplinary():
    """
    This scheduled task to trigger the Disciplinary action and take the suspens
    """
    from base.models import EmployeeShiftSchedule
    from employee.models import DisciplinaryAction
    from employee.policies import employee_account_block_unblock

    dis_action = DisciplinaryAction.objects.all()
    for dis in dis_action:

        if dis.action.block_option:
            if dis.action.action_type == "suspension":
                if dis.days:
                    day = dis.days
                    end_date = dis.start_date + timedelta(days=day)
                    if (
                        datetime.date.today() >= dis.start_date
                        or datetime.date.today() >= end_date
                    ):
                        if datetime.date.today() >= dis.start_date:
                            r = False
                        if datetime.date.today() >= end_date:
                            r = True

                        employees = dis.employee_id.all()
                        for emp in employees:
                            employee_account_block_unblock(emp_id=emp.id, result=r)

                if dis.hours:
                    hour_str = dis.hours + ":00"
                    if hour_str > "00:00:00":

                        # Checking the date of action date.
                        if datetime.date.today() >= dis.start_date:

                            employees = dis.employee_id.all()
                            for emp in employees:

                                # Taking the shift of employee for taking the work start time
                                shift = emp.employee_work_info.shift_id
                                shift_detail = EmployeeShiftSchedule.objects.filter(
                                    shift_id=shift
                                )
                                for shi in shift_detail:
                                    today = datetime.datetime.today()
                                    day_of_week = today.weekday()

                                    # List of weekday names
                                    weekday_names = [
                                        "monday",
                                        "tuesday",
                                        "wednesday",
                                        "thursday",
                                        "friday",
                                        "saturday",
                                        "sunday",
                                    ]
                                    if weekday_names[day_of_week] == shi.day.day:

                                        st_time = shi.start_time

                                        hour_time = datetime.datetime.strptime(
                                            hour_str, "%H:%M:%S"
                                        ).time()

                                        time1 = st_time
                                        time2 = hour_time

                                        # Convert them to datetime objects
                                        datetime1 = datetime.datetime.combine(
                                            datetime.date.today(), time1
                                        )
                                        datetime2 = datetime.datetime.combine(
                                            datetime.date.today(), time2
                                        )

                                        # Add the datetime objects
                                        result_datetime = (
                                            datetime1
                                            + datetime.timedelta(
                                                hours=datetime2.hour,
                                                minutes=datetime2.minute,
                                                seconds=datetime2.second,
                                            )
                                        )

                                        # Extract the time component from the result
                                        result_time = result_datetime.time()

                                        # Get the current time
                                        current_time = datetime.datetime.now().time()

                                        # Check if the current time matches st_time
                                        if current_time >= st_time:
                                            r = False
                                        if current_time >= result_time:
                                            r = True

                                    employee_account_block_unblock(
                                        emp_id=emp.id, result=r
                                    )

            if dis.action.action_type == "dismissal":
                if datetime.date.today() >= dis.start_date:
                    if datetime.date.today() >= dis.start_date:
                        r = False
                    employees = dis.employee_id.all()
                    for emp in employees:
                        employee_account_block_unblock(emp_id=emp.id, result=r)

    return


scheduler = BackgroundScheduler()
scheduler.add_job(update_experience, "interval", hours=4)
scheduler.add_job(block_unblock_disciplinary, "interval", seconds=10)
scheduler.start()
