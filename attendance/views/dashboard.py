"""
dashboard.py

This module is used to register endpoints for dashboard-related requests
"""

from datetime import datetime
from django.db.models import Q
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from base.methods import filtersubordinates
from base.models import Department, EmployeeShiftSchedule
from employee.models import Employee
from horilla.decorators import login_required
from attendance.models import Attendance, AttendanceLateComeEarlyOut






def find_on_time(request, today, week_day, department=None):
    """
    This method is used to find count for on time attendances
    """
    on_time = 0
    attendances = Attendance.objects.filter(attendance_date=today)
    attendances = filtersubordinates(request, attendances, "attendance.view_attendance")
    if department is not None:
        attendances = attendances.filter(
            employee_id__employee_work_info__department_id=department
        )
    excepted_attendances = 0
    for attendance in attendances:
        shift = attendance.shift_id
        schedules_today = shift.employeeshiftschedule_set.filter(day__day=week_day)
        if schedules_today.first() is not None:
            excepted_attendances = excepted_attendances + 1
            late_come_obj = attendance.late_come_early_out.filter(
                type="late_come"
            ).first()
            if late_come_obj is None:
                on_time = on_time + 1
    return on_time


def find_late_come(today, department=None):
    """
    This method is used to find count of late comers
    """
    late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
        type="late_come", attendance_id__attendance_date=today
    )
    if department is not None:
        late_come_obj = late_come_obj.filter(
            employee_id__employee_work_info__department_id=department
        )
    return len(late_come_obj)


def find_expected_attendances(week_day):
    """
    This method is used to find count of expected attendances for the week day
    """
    schedules_today = EmployeeShiftSchedule.objects.filter(day__day=week_day)
    expected_attendances = 0
    for schedule in schedules_today:
        shift = schedule.shift_id
        expected_attendances = expected_attendances + len(
            shift.employeeworkinformation_set.all()
        )
    return expected_attendances


@login_required
def dashboard(request):
    """
    This method is used to render individual dashboard for attendance module
    """
    employees = Employee.objects.filter(
        is_active=True,
    ).filter(~Q(employee_work_info__shift_id=None))
    total_employees = len(employees)

    today = datetime.today()
    week_day = today.strftime("%A").lower()

    on_time = find_on_time(request, today=today, week_day=week_day)
    late_come_obj = find_late_come(today=today)

    marked_attendances = late_come_obj + on_time

    expected_attendances = find_expected_attendances(week_day=week_day)
    on_time_ratio = 0
    late_come_ratio = 0
    marked_attendances_ratio = 0
    if expected_attendances != 0:
        on_time_ratio = f"{(on_time / expected_attendances) * 100:.1f}"
        late_come_ratio = f"{(late_come_obj / expected_attendances) * 100:.1f}"
        marked_attendances_ratio = (
            f"{(marked_attendances / expected_attendances) * 100:.1f}"
        )
    early_outs = AttendanceLateComeEarlyOut.objects.filter(
        type="early_out", attendance_id__attendance_date=today
    )

    return render(
        request,
        "attendance/dashboard/dashboard.html",
        {
            "total_employees": total_employees,
            "on_time": on_time,
            "on_time_ratio": on_time_ratio,
            "late_come": late_come_obj,
            "late_come_ratio": late_come_ratio,
            "expected_attendances": expected_attendances,
            "marked_attendances": marked_attendances,
            "marked_attendances_ratio": marked_attendances_ratio,
            "on_break": early_outs,
        },
    )


def find_early_out(today, department=None):
    """
    This method is used to find early out attendances and it returns query set
    """
    if department is not None:
        early_out_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="early_out",
            employee_id__employee_work_info__department_id=department,
            attendance_id__attendance_date=today,
        )
    else:
        early_out_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="early_out", attendance_id__attendance_date=today
        )
    return early_out_obj


def generate_data_set(request, dept):
    """
    This method is used to generate all the dashboard data
    """
    today = datetime.today()
    week_day = today.strftime("%A").lower()
    # below method will find all the on-time attendance corresponding to the
    # employee shift and shift schedule.
    on_time = find_on_time(request, today=today, week_day=week_day, department=dept)

    # below method will find all the late-come attendance corresponding to the
    # employee shift and schedule.
    late_come_obj = find_late_come(today=today, department=dept)

    # below method will find all the early-out attendance corresponding to the
    # employee shift and shift schedule
    early_out_obj = find_early_out(department=dept, today=today)

    data = {
        "label": dept.department,
        "data": [on_time, late_come_obj, len(early_out_obj)],
    }
    return data


@login_required
def dashboard_attendance(request):
    """
    This method is used to render json response of dashboard data

    Returns:
        JsonResponse: returns data set as json
    """
    labels = [
        _("On Time"),
        _("Late Come"),
        _("On Break"),
    ]
    data_set = []
    departments = Department.objects.all()
    for dept in departments:
        data_set.append(generate_data_set(request, dept))
    return JsonResponse({"dataSet": data_set, "labels": labels})
