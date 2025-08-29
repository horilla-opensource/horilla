from datetime import date, timedelta

from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from notifications.signals import notify
from notifications.models import Notification

from project.models import TimeSheet
from attendance.models import Attendance
from attendance.methods.utils import strtime_seconds, format_time
from employee.models import Employee


def _check_timesheet(employee: Employee, day: date):
    """Return timesheet comparison info for a given day.

    Always returns a dictionary with keys:
      - ``missing``: True if no timesheet entries exist for the day
      - ``mismatch``: True if logged < worked (when attendance exists)
      - ``worked``: Worked seconds from attendance if available (else 0)
      - ``logged``: Total logged seconds from timesheets (0 if none)
    """

    sheets = TimeSheet.objects.filter(employee_id=employee, date=day)
    logged = sum(strtime_seconds(ts.time_spent or "00:00") for ts in sheets)

    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=day
    ).first()
    worked = 0
    if attendance and attendance.attendance_worked_hour:
        worked = strtime_seconds(attendance.attendance_worked_hour or "00:00")

    worked_hours = worked // 3600
    logged_hours = logged // 3600

    info = {
        "missing": not sheets.exists(),
        # Compare by hours only; minutes difference within same hour is OK
        "mismatch": worked > 0 and (logged_hours != worked_hours),
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
    day_name = day.strftime("%A")
    day_str = day.strftime("%d %b %Y")
    if info["missing"]:
        message = _(
            "You haven't filled your timesheet for {day_name}, {date}. Please complete it now to ensure accurate record-keeping."
        ).format(day_name=day_name, date=day_str)
    elif info["mismatch"]:
        message = _(
            "Your logged hours are less than your check-in/check-out duration for {day_name}, {date}. Please update your timesheet."
        ).format(day_name=day_name, date=day_str)
    if not message:
        return

    user = employee.employee_user_id
    redirect_url = reverse("view-time-sheet")
    # Use Employee as actor so templates can show employee name
    _send_notification(employee, user, message, redirect_url)

    manager = employee.get_reporting_manager()
    if manager:
        manager_msg = _(
            "Employee {name} has not submitted their timesheet for {day_name}, {date}. Please follow up."
        ).format(name=str(employee), day_name=day_name, date=day_str)
        _send_notification(employee, manager.employee_user_id, manager_msg, redirect_url)


def get_employee_timesheet_reminders(employee: Employee):
    """Return reminder messages for the logged-in employee and ensure notifications exist.

    Each reminder item may include worked/logged in HH:MM for display.
    """

    today = date.today()
    day = today - timedelta(days=1)
    info = _check_timesheet(employee, day)
    reminders = []
    if info:
        redirect_url = reverse("view-time-sheet")
        day_name = day.strftime("%A")
        day_str = day.strftime("%d %b %Y")
        if info["missing"]:
            msg = _(
                "You haven't filled your timesheet for {day_name}, {date}. Please complete it now to ensure accurate record-keeping."
            ).format(day_name=day_name, date=day_str)
            reminders.append({
                "message": msg,
                "missing": True,
            })
            _send_notification(employee, employee.employee_user_id, msg, redirect_url)
        elif info["mismatch"]:
            msg = _(
                "Your logged hours are less than your check-in/check-out duration for {day_name}, {date}. Please update your timesheet."
            ).format(day_name=day_name, date=day_str)
            reminders.append({
                "message": msg,
                "mismatch": True,
                "worked_hm": format_time(info["worked"]),
                "logged_hm": format_time(info["logged"]),
            })
            _send_notification(employee, employee.employee_user_id, msg, redirect_url)
    return reminders


def get_manager_timesheet_reminders(manager: Employee):
    """Return reminders for a manager about subordinates and ensure notifications exist.

    Each item contains message plus details: missing/mismatch and HH:MM values.
    """

    today = date.today()
    day = today - timedelta(days=1)
    reminders = []
    subordinates = Employee.objects.filter(
        employee_work_info__reporting_manager_id=manager, is_active=True
    )
    for emp in subordinates:
        info = _check_timesheet(emp, day)
        if info and (info["missing"] or info["mismatch"]):
            redirect_url = reverse("view-time-sheet")
            day_name = day.strftime("%A")
            day_str = day.strftime("%d %b %Y")
            if info["missing"]:
                msg = _(
                    "Employee {name} has not submitted the timesheet for {day_name}, {date}. Please follow up."
                ).format(name=str(emp), day_name=day_name, date=day_str)
                reminders.append({
                    "employee_name": str(emp),
                    "message": msg,
                    "missing": True,
                })
                _send_notification(emp, manager.employee_user_id, msg, redirect_url)
            elif info["mismatch"]:
                worked_hm = format_time(info["worked"])
                logged_hm = format_time(info["logged"])
                msg = _(
                    "Employee {name} has a timesheet discrepancy for {day_name}, {date}. Please follow up."
                ).format(name=str(emp), day_name=day_name, date=day_str)
                reminders.append({
                    "employee_name": str(emp),
                    "message": msg,
                    "mismatch": True,
                    "worked_hm": worked_hm,
                    "logged_hm": logged_hm,
                })
                _send_notification(emp, manager.employee_user_id, msg, redirect_url)
    return reminders
