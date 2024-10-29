"""
process_attendance_data.py

This module contains a function for processing attendance data
from Excel files and saving it to a database.
"""

from datetime import datetime

import pandas as pd

from attendance.models import Attendance
from base.models import EmployeeShift, WorkType
from employee.models import Employee


def format_time(time_obj):
    return time_obj.strftime("%H:%M") if time_obj else None


def process_attendance_data(attendance_dicts):
    """
    Process a list of attendance data dictionaries and save valid records to the database,
    while collecting error details for invalid records.

    Parameters:
        attendance_dicts (list of dict): A list of dictionaries containing attendance data.

    Returns:
        list: A list of dictionaries representing errors encountered during processing.
    """
    error_list = []
    attendance_list = []
    today = datetime.today().date()

    # Cache all necessary data in bulk to reduce DB hits
    badge_ids = [d["Badge ID"] for d in attendance_dicts]
    employees = {
        emp.badge_id: emp
        for emp in Employee.objects.filter(
            badge_id__in=[d["Badge ID"] for d in attendance_dicts], is_active=True
        )
    }
    shifts = {shift.employee_shift: shift for shift in EmployeeShift.objects.all()}
    work_types = {wt.work_type: wt for wt in WorkType.objects.all()}
    existing_attendance_records = {
        (att.employee_id.badge_id, att.attendance_date): att
        for att in Attendance.objects.filter(
            employee_id__badge_id__in=badge_ids
        ).select_related("employee_id")
    }

    for attendance_data in attendance_dicts:
        save = True
        try:
            badge_id = attendance_data["Badge ID"]
            shift_id = attendance_data["Shift"]
            work_type_id = attendance_data["Work type"]

            # Retrieve objects from cached dictionaries
            employee = employees.get(badge_id)
            shift = shifts.get(shift_id)
            work_type = work_types.get(work_type_id)

            attendance_date = None
            check_in_date = None
            check_out_date = None

            try:
                attendance_date = pd.to_datetime(
                    attendance_data["Attendance date"]
                ).date()
                if (badge_id, attendance_date) in existing_attendance_records:
                    attendance_data["Attendance Error"] = (
                        "This employee's attendance for this date already exists."
                    )
                    save = False
            except Exception as exception:
                attendance_data["Attendance Date Error"] = (
                    "The attendance date format is invalid. Please use the format YYYY-MM-DD"
                )
                save = False

            try:
                check_in_date = pd.to_datetime(attendance_data["Check-in date"]).date()
            except Exception as exception:
                attendance_data["Check-in Date Error"] = (
                    "The Check-in date format is invalid. Please use the format YYYY-MM-DD"
                )
                save = False

            try:
                check_out_date = pd.to_datetime(
                    attendance_data["Check-out date"]
                ).date()
            except Exception as exception:
                attendance_data["Check-out Date Error"] = (
                    "The Check-out date format is invalid. Please use the format YYYY-MM-DD"
                )
                save = False

            try:
                check_in = pd.to_datetime(
                    attendance_data["Check-in"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Check-in Error"] = f"{exception} of check-in time"
                save = False

            try:
                check_out = pd.to_datetime(
                    attendance_data["Check-out"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Check-out Error"] = f"{exception} of check-out time"
                save = False

            try:
                worked_hour = pd.to_datetime(
                    attendance_data["Worked hour"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Worked Hours Error"] = f"{exception} of worked hours"
                save = False

            try:
                minimum_hour = pd.to_datetime(
                    attendance_data["Minimum hour"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Minimum Hour Error"] = f"{exception} of minimum hours"
                save = False

            if employee is None or not employee.is_active:
                attendance_data["Badge ID Error"] = f"Invalid Badge ID given {badge_id}"
                save = False

            if shift is None:
                attendance_data["Shift Error"] = f"Invalid shift '{shift_id}'"
                save = False

            if work_type is None:
                attendance_data["Work Type Error"] = (
                    f"Invalid work type '{work_type_id}'"
                )
                save = False

            if check_in_date is not None and attendance_date is not None:
                if check_in_date < attendance_date:
                    attendance_data["Check-in Validation Error"] = (
                        "Attendance check-in date cannot be smaller than attendance date"
                    )
                    save = False

            if check_in_date is not None and check_out_date is not None:
                if check_out_date < check_in_date:
                    attendance_data["Check-out Validation Error"] = (
                        "Attendance check-out date never smaller than attendance check-in date"
                    )
                    save = False

            if attendance_date is not None:
                if attendance_date >= today:
                    attendance_data["Attendance Date Validation Error"] = (
                        "Attendance date in future"
                    )
                    save = False

            if check_in_date is not None:
                if check_in_date >= today:
                    attendance_data["Check-in Validation Error"] = (
                        "Attendance check in date in future"
                    )
                    save = False

            if check_out_date is not None:
                if check_out_date >= today:
                    attendance_data["Check-out Validation Error"] = (
                        "Attendance check out date in future"
                    )
                    save = False

            if save:
                attendance_list.append(
                    Attendance(
                        employee_id=employee,
                        shift_id=shift,
                        work_type_id=work_type,
                        attendance_date=attendance_date,
                        attendance_clock_in_date=check_in_date,
                        attendance_clock_in=format_time(check_in),
                        attendance_clock_out_date=check_out_date,
                        attendance_clock_out=format_time(check_out),
                        attendance_worked_hour=format_time(worked_hour),
                        minimum_hour=format_time(minimum_hour),
                    )
                )
                existing_attendance_records[(badge_id, attendance_date)] = (
                    employee,
                    attendance_date,
                )
            else:
                error_list.append(attendance_data)

        except Exception as exception:
            attendance_data["Other Errors"] = f"{str(exception)}"
            error_list.append(attendance_data)
    if attendance_list:
        Attendance.objects.bulk_create(attendance_list)
    return error_list
