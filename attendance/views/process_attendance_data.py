"""
process_attendance_data.py

This module contains a function for processing attendance data 
from Excel files and saving it to a database.
"""
from datetime import datetime
import pandas as pd
from employee.models import Employee
from attendance.models import Attendance
from base.models import EmployeeShift, WorkType


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
    for attendance_data in attendance_dicts:
        save = True
        try:
            today = datetime.today().date()
            badge_id = attendance_data["Badge ID"]
            shift_id = attendance_data["Shift"]
            work_type_id = attendance_data["Work type"]
            employee = Employee.objects.filter(badge_id=badge_id).first()
            shift = EmployeeShift.objects.filter(employee_shift=shift_id).first()
            work_type = WorkType.objects.filter(work_type=work_type_id).first()
            attendance_date = None
            check_in_date = None
            check_out_date = None

            try:
                attendance_date = pd.to_datetime(
                    attendance_data["Attendance date"]
                ).date()
                existing_attendance = Attendance.objects.filter(
                    employee_id__badge_id=badge_id,
                    attendance_date=attendance_data["Attendance date"],
                ).first()
                if existing_attendance:
                    attendance_data[
                        "Error6"
                    ] = "Attendance for this date already exists"
                    save = False
            except Exception as exception:
                attendance_data[
                    "Error14"
                ] = "The date format for attendance date is not valid"
                save = False

            try:
                check_in_date = pd.to_datetime(attendance_data["Check-in date"]).date()
            except Exception as exception:
                attendance_data[
                    "Error15"
                ] = "The date format for Check-in date is not valid"
                save = False

            try:
                check_out_date = pd.to_datetime(
                    attendance_data["Check-out date"]
                ).date()
            except Exception as exception:
                attendance_data[
                    "Error16"
                ] = "The date format for Check-out date is not valid"
                save = False

            try:
                check_in = pd.to_datetime(
                    attendance_data["Check-in"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Error10"] = f"{exception} of check-in time"
                save = False

            try:
                check_out = pd.to_datetime(
                    attendance_data["Check-out"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Error11"] = f"{exception} of check-out time"
                save = False

            try:
                worked_hour = pd.to_datetime(
                    attendance_data["Worked hour"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Error12"] = f"{exception} of worked hours"
                save = False

            try:
                minimum_hour = pd.to_datetime(
                    attendance_data["Minimum hour"], format="%H:%M:%S"
                ).time()
            except Exception as exception:
                attendance_data["Error13"] = f"{exception} of minimum hours"
                save = False

            if employee is None:
                attendance_data["Error1"] = f"Invalid Badge ID given {badge_id}"
                save = False

            if shift is None:
                attendance_data["Error2"] = f"Invalid shift '{shift_id}'"
                save = False

            if work_type is None:
                attendance_data["Error3"] = f"Invalid work type '{work_type_id}'"
                save = False

            if check_in_date is not None and attendance_date is not None:
                if check_in_date < attendance_date:
                    attendance_data[
                        "Error4"
                    ] = "Attendance check-in date cannot be smaller than attendance date"
                    save = False

            if check_in_date is not None and check_out_date is not None:
                if check_out_date < check_in_date:
                    attendance_data[
                        "Error5"
                    ] = "Attendance check-out date never smaller than attendance check-in date"
                    save = False

            if attendance_date is not None:
                if attendance_date >= today:
                    attendance_data["Error7"] = "Attendance date in future"
                    save = False

            if check_in_date is not None:
                if check_in_date >= today:
                    attendance_data["Error8"] = "Attendance check in date in future"
                    save = False

            if check_out_date is not None:
                if check_out_date >= today:
                    attendance_data["Error9"] = "Attendance check out date in future"
                    save = False

            if save:
                attendance = Attendance(
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
                attendance.save()
            else:
                error_list.append(attendance_data)

        except Exception as exception:
            attendance_data["Error17"] = f"{str(exception)}"
            error_list.append(attendance_data)

    return error_list
