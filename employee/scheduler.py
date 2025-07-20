import datetime
import sys
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.core.mail import send_mail
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



def send_probation_end_notifications():

    from employee.models import Employee
    from django.utils import timezone
    from employee.models import EmployeeWorkInformation

    today = timezone.now().date()

    # Employees whose probation ends today
    # ending_today = Employee.objects.filter(
    #     probation_end_date=today,
    #     # probation_notification_sent=False,
    #     is_active=True
    # )

    ending_today = EmployeeWorkInformation.objects.filter(
        probation_end_date=today,
        employee_id__is_active=True
    )


    # upcoming_month = Employee.objects.filter(
    #     probation_end_date=today + timedelta(days=30),
    #     # probation_notification_sent=False,
    #     is_active=True
    # )
    # upcoming_two_week = Employee.objects.filter(
    #     probation_end_date=today + timedelta(days=14),
    #     probation_notification_sent=False,
    #     is_active=True
    # )
    # upcoming_one_week = Employee.objects.filter(
    #     probation_end_date=today + timedelta(days=7),
    #     # probation_notification_sent=False,
    #     is_active=True
    # )

    # Send notifications for probation ending today
    for employee in ending_today:
        context = {
            'employee': employee,
            'probation_end_date': employee.probation_end_date,
            'days_remaining': 0
        }

        send_probation_email(employee, 'probation_notification.html', context)


def send_probation_email(employee, template_name, context):

    subject = f"Probation Period Notification: {employee.employee_id.get_full_name()}"

    # Render HTML email
    html_message = render_to_string(
        f"emails/{template_name}",
        context
    )

    # Determine recipients (employee, manager, HR)
    recipients = [employee.email]
    # if employee.reporting_manager_id.get_email():
    #     recipients.append(employee.employee_work_info.reporting_manager.work_email)

    # Add HR email from settings
    hr_email = getattr(settings, 'HR_EMAIL', 'hr@wireapps.co.uk')
    recipients.append(hr_email)

    # print(html_message)
    #
    # print(recipients)
    #
    # print(subject)

    # send_mail(
    #     subject=subject,
    #     message="",  # Empty message since we're using html_message
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=list(set(recipients)),  # Remove duplicates
    #     html_message=html_message,
    #     fail_silently=False
    # )


def send_contract_end_notification():
    from django.utils import timezone
    from employee.models import EmployeeWorkInformation

    today = timezone.now().date()

    ending_today = EmployeeWorkInformation.objects.filter(
        contract_end_date=today,
        employee_id__is_active=True
    )
    # new contract date > last contrat date
    # print("Contract",ending_today)


def send_birthday_in_this_month_notification():
    from django.utils import timezone
    from employee.models import Employee

    today = timezone.now().date()
    current_month = today.month

    birthday_list = Employee.objects.filter(
        dob__month=current_month,

    )
    # only once
    # print("Birhtday" , birthday_list)


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_experience, "interval", hours=4)
    scheduler.add_job(block_unblock_disciplinary, "interval", seconds=25)
    # scheduler.add_job(send_probation_end_notifications, "interval", days=1)
    # scheduler.add_job(send_contract_end_notification, "interval", seconds=30)
    # scheduler.add_job(send_birthday_in_this_month_notification, "interval", seconds=5)
    scheduler.start()

