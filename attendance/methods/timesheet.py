from datetime import date, timedelta

from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from notifications.signals import notify
from notifications.models import Notification

from project.models import TimeSheet
from attendance.models import Attendance
from attendance.methods.utils import strtime_seconds
from employee.models import Employee


def _check_timesheet(employee: Employee, day: date):
    """Return timesheet comparison info for a given day.

    Returns a dictionary with keys ``missing`` and ``mismatch`` along with
    ``worked`` and ``logged`` seconds. If there is no attendance for the day
    ``None`` is returned.
    """

    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=day
    ).first()
    if not attendance or not attendance.attendance_worked_hour:
        return None

    worked = strtime_seconds(attendance.attendance_worked_hour or "00:00")
    sheets = TimeSheet.objects.filter(employee_id=employee, date=day)
    logged = sum(strtime_seconds(ts.time_spent or "00:00") for ts in sheets)

    info = {
        "missing": not sheets.exists(),
        "mismatch": logged < worked,
        "worked": worked,
        "logged": logged,
    }
    return info


def _send_notification(sender, recipient, message: str, redirect: str):
    """Send a notification if it doesn't already exist for this verb/recipient."""

    if not Notification.objects.filter(recipient=recipient, verb=str(message)).exists():
        notify.send(
            sender,
            recipient=recipient,
            verb=str(message),
            verb_ar=str(message),
            verb_de=str(message),
            verb_es=str(message),
            verb_fr=str(message),
            redirect=redirect,
            icon="alert",
        )


def validate_previous_day_timesheet(employee: Employee, today: date):
    """Validate yesterday's timesheet for an employee and send notifications."""

    day = today - timedelta(days=1)
    info = _check_timesheet(employee, day)
    if not info:
        return

    message = None
    if info["missing"]:
        message = _(
            "You haven't filled your timesheet for yesterday. Please complete it now to ensure accurate record-keeping."
        )
    elif info["mismatch"]:
        message = _(
            "Your logged hours are less than your check-in/check-out duration for yesterday. Please update your timesheet."
        )
    if not message:
        return

    user = employee.employee_user_id
    redirect_url = reverse("view-time-sheet")
    # Use Employee as actor so templates can show employee name
    _send_notification(employee, user, message, redirect_url)

    manager = employee.get_reporting_manager()
    if manager:
        manager_msg = _(
            "Employee {name} has not submitted their timesheet for yesterday. Please follow up."
        ).format(name=str(employee))
        _send_notification(employee, manager.employee_user_id, manager_msg, redirect_url)


def get_employee_timesheet_reminders(employee: Employee):
    """Return reminder messages for the logged-in employee and ensure notifications exist."""

    today = date.today()
    day = today - timedelta(days=1)
    info = _check_timesheet(employee, day)
    reminders = []
    if info:
        redirect_url = reverse("view-time-sheet")
        if info["missing"]:
            msg = _(
                "You haven't filled your timesheet for yesterday. Please complete it now to ensure accurate record-keeping."
            )
            reminders.append({"message": msg})
            _send_notification(employee, employee.employee_user_id, msg, redirect_url)
        elif info["mismatch"]:
            msg = _(
                "Your logged hours are less than your check-in/check-out duration for yesterday. Please update your timesheet."
            )
            reminders.append({"message": msg})
            _send_notification(employee, employee.employee_user_id, msg, redirect_url)
    return reminders


def get_manager_timesheet_reminders(manager: Employee):
    """Return reminders for a manager about subordinates and ensure notifications exist."""

    today = date.today()
    day = today - timedelta(days=1)
    reminders = []
    subordinates = Employee.objects.filter(
        employee_work_info__reporting_manager_id=manager, is_active=True
    )
    for emp in subordinates:
        info = _check_timesheet(emp, day)
        if info and (info["missing"] or info["mismatch"]):
            msg = _(
                "Employee {name} has not submitted their timesheet for yesterday. Please follow up."
            ).format(name=str(emp))
            reminders.append({"message": msg})
            _send_notification(emp, manager.employee_user_id, msg, reverse("view-time-sheet"))
    return reminders

