import logging
import os
import time
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.signals import user_login_failed
from django.db.models import Max, Q
from django.db.models.signals import m2m_changed, post_migrate, post_save
from django.dispatch import receiver
from django.shortcuts import redirect

from base.models import Announcement, PenaltyAccounts
from horilla.methods import get_horilla_model_class


@receiver(post_save, sender=PenaltyAccounts)
def create_deduction_cutleave_from_penalty(sender, instance, created, **kwargs):
    """
    This is post save method, used to create deduction and cut available leave days
    """
    # only work when creating
    if created:
        penalty_amount = instance.penalty_amount
        if apps.is_installed("payroll") and penalty_amount:
            Deduction = get_horilla_model_class(app_label="payroll", model="deduction")
            penalty = Deduction()
            if instance.late_early_id:
                penalty.title = f"{instance.late_early_id.get_type_display()} penalty"
                penalty.one_time_date = (
                    instance.late_early_id.attendance_id.attendance_date
                )
            elif instance.leave_request_id:
                penalty.title = f"Leave penalty {instance.leave_request_id.end_date}"
                penalty.one_time_date = instance.leave_request_id.end_date
            else:
                penalty.title = f"Penalty on {datetime.today()}"
                penalty.one_time_date = datetime.today()
            penalty.include_active_employees = False
            penalty.is_fixed = True
            penalty.amount = instance.penalty_amount
            penalty.only_show_under_employee = True
            penalty.save()
            penalty.include_active_employees = False
            penalty.specific_employees.add(instance.employee_id)
            penalty.save()

        if (
            apps.is_installed("leave")
            and instance.leave_type_id
            and instance.minus_leaves
        ):
            available = instance.employee_id.available_leave.filter(
                leave_type_id=instance.leave_type_id
            ).first()
            unit = round(instance.minus_leaves * 2) / 2
            if not instance.deduct_from_carry_forward:
                available.available_days = max(0, (available.available_days - unit))
            else:
                available.carryforward_days = max(
                    0, (available.carryforward_days - unit)
                )

            available.save()


# @receiver(post_migrate)
def clean_work_records(sender, **kwargs):
    if sender.label not in ["attendance"]:
        return
    from attendance.models import WorkRecords

    latest_records = (
        WorkRecords.objects.exclude(work_record_type="DFT")
        .values("employee_id", "date")
        .annotate(latest_id=Max("id"))
    )

    # Delete all but the latest WorkRecord
    deleted_count = 0
    for record in latest_records:
        deleted_count += (
            WorkRecords.objects.filter(
                employee_id=record["employee_id"], date=record["date"]
            )
            .exclude(id=record["latest_id"])
            .delete()[0]
        )


@receiver(m2m_changed, sender=Announcement.employees.through)
def filtered_employees(sender, instance, action, **kwargs):
    """
    filtered employees
    """
    if action not in ["post_add", "post_remove", "post_clear"]:
        return  # Only run after M2M changes
    employee_ids = list(instance.employees.values_list("id", flat=True))
    department_ids = list(instance.department.values_list("id", flat=True))
    job_position_ids = list(instance.job_position.values_list("id", flat=True))

    employees = instance.model_employee.objects.filter(
        Q(id__in=employee_ids)
        | Q(employee_work_info__department_id__in=department_ids)
        | Q(employee_work_info__job_position_id__in=job_position_ids)
    )

    instance.filtered_employees.set(employees)


# Logger setup
logger = logging.getLogger("django.security")

# Create a global dictionary to track login attempts and ban time per session
failed_attempts = {}
ban_time = {}

FAIL2BAN_LOG_ENABLED = os.path.exists(
    "security.log"
)  # Checking that any file is created for the details of the wrong logins.
# The file will be created only if you set the LOGGING in your settings.py


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    """
    To ban the IP of user that enter wrong credentials for multiple times
    you should add this section in your settings.py file. And also it creates the security file for deatils of wrong logins.


    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': '/var/log/django/security.log', # File Path for view the log details.
                                                            # Give the same path to the section FAIL2BAN_LOG_ENABLED = os.path.exists('security.log') in signals.py in Base.
            },
        },
        'loggers': {
            'django.security': {
                'handlers': ['security_file'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
    }

    """

    # Checking that the file is created or not to initiate the ban functions.
    if not FAIL2BAN_LOG_ENABLED:
        return

    username = credentials.get("username", "unknown")
    ip = request.META.get("REMOTE_ADDR", "unknown")

    # Track the number of failed attempts for the user in the current session
    session_key = request.session.session_key
    if not session_key:
        request.session.create()

    # Initialize failed attempts for this session if not already
    if session_key not in failed_attempts:
        failed_attempts[session_key] = 0

    # Initialize ban time if not already set
    if session_key not in ban_time:
        ban_time[session_key] = 0

    failed_attempts[session_key] += 1

    # Log the failed attempt
    logger.warning(f"Invalid login attempt for user '{username}' from {ip}")

    # Set maximum allowed attempts
    max_attempts = 3
    attempts_left = max_attempts - failed_attempts[session_key]

    # If the user is banned, show banned message and GIF
    if ban_time.get(session_key, 0) > time.time():
        banned_until = time.strftime("%H:%M", time.localtime(ban_time[session_key]))
        messages.info(
            request, f"You are banned until {banned_until}. Please try again later."
        )
        return redirect("/")

    # If failed attempts are above the limit, ban the user for 5 minutes
    if failed_attempts[session_key] >= max_attempts:
        # Ban user for 5 minutes (300 seconds)
        ban_time[session_key] = time.time() + 300
        messages.info(
            request,
            "You have exceeded the maximum attempts. You are banned for 5 minutes.",
        )
        return redirect("/")  # Redirect or show a banned page

    # Display message showing remaining attempts
    if attempts_left > 0:
        message = (
            f"You have {attempts_left} attempts left before being temporarily banned."
        )
    else:
        message = (
            "You have exceeded the maximum attempts. You will be banned for 5 minutes."
        )

    # Add a message to the session to show to the user
    messages.info(request, message)
    return redirect("login")
