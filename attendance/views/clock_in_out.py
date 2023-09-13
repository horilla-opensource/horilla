"""
clock_in_out.py

This module is used register endpoints to the check-in check-out functionalities
"""
from datetime import date, datetime, timedelta
from django.db.models import Q
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from base.models import EmployeeShiftDay
from horilla.decorators import login_required
from attendance.models import Attendance, AttendanceActivity, AttendanceLateComeEarlyOut
from attendance.views.views import (
    activity_datetime,
    attendance_validate,
    employee_exists,
    format_time,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)


def late_come_create(attendance):
    """
    used to create late come report
    args:
        attendance : attendance object
    """

    late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "late_come"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def late_come(attendance, start_time, end_time):
    """
    this method is used to mark the late check-in  attendance after the shift starts
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        end_time : attendance day shift end time

    """

    now_sec = strtime_seconds(datetime.now().strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    if start_time > end_time and start_time != end_time:
        # night shift
        if now_sec < mid_day_sec:
            # Here  attendance or attendance activity for new day night shift
            late_come_create(attendance)
        elif now_sec > start_time:
            # Here  attendance or attendance activity for previous day night shift
            late_come_create(attendance)
    elif start_time < now_sec:
        late_come_create(attendance)
    return True


def clock_in_attendance_and_activity(
    employee,
    date_today,
    attendance_date,
    day,
    now,
    shift,
    minimum_hour,
    start_time,
    end_time,
):
    """
    This method is used to create attendance activity or attendance when an employee clocks-in
    args:
        employee        : employee instance
        date_today      : date
        attendance_date : the date that attendance for
        day             : shift day
        now             : current time
        shift           : shift object
        minimum_hour    : minimum hour in shift schedule
        start_time      : start time in shift schedule
        end_time        : end time in shift schedule
    """

    # attendance activity create
    AttendanceActivity(
        employee_id=employee,
        attendance_date=attendance_date,
        clock_in_date=date_today,
        shift_day=day,
        clock_in=now,
    ).save()

    # create attendance if not exist
    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=attendance_date
    )
    if not attendance.exists():
        attendance = Attendance()
        attendance.employee_id = employee
        attendance.shift_id = shift
        attendance.work_type_id = attendance.employee_id.employee_work_info.work_type_id
        attendance.attendance_date = attendance_date
        attendance.attendance_day = day
        attendance.attendance_clock_in = now
        attendance.attendance_clock_in_date = date_today
        attendance.minimum_hour = minimum_hour
        attendance.save()
        # check here late come or not
        late_come(attendance=attendance, start_time=start_time, end_time=end_time)
    else:
        attendance = attendance[0]
        attendance.attendance_clock_out = None
        attendance.attendance_clock_out_date = None
        attendance.save()
        # delete if the attendance marked the early out
        early_out_instance = attendance.late_come_early_out.filter(type="early_out")
        if early_out_instance.exists():
            early_out_instance[0].delete()
    return attendance


@login_required
def clock_in(request):
    """
    This method is used to mark the attendance once per a day and multiple attendance activities.
    """
    employee, work_info = employee_exists(request)
    if employee and work_info is not None:
        shift = work_info.shift_id
        date_today = date.today()
        attendance_date = date_today
        day = date_today.strftime("%A").lower()
        day = EmployeeShiftDay.objects.get(day=day)
        now = datetime.now().strftime("%H:%M")
        now_sec = strtime_seconds(now)
        mid_day_sec = strtime_seconds("12:00")
        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
            day=day, shift=shift
        )
        if start_time_sec > end_time_sec:
            # night shift
            # ------------------
            # Night shift in Horilla consider a 24 hours from noon to next day noon,
            # the shift day taken today if the attendance clocked in after 12 O clock.

            if mid_day_sec > now_sec:
                # Here you need to create attendance for yesterday

                date_yesterday = date_today - timedelta(days=1)
                day_yesterday = date_yesterday.strftime("%A").lower()
                day_yesterday = EmployeeShiftDay.objects.get(day=day_yesterday)
                minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                    day=day_yesterday, shift=shift
                )
                attendance_date = date_yesterday
                day = day_yesterday
        clock_in_attendance_and_activity(
            employee=employee,
            date_today=date_today,
            attendance_date=attendance_date,
            day=day,
            now=now,
            shift=shift,
            minimum_hour=minimum_hour,
            start_time=start_time_sec,
            end_time=end_time_sec,
        )
        return HttpResponse(
            """
              <button class="oh-btn oh-btn--warning-outline "
              hx-get="/attendance/clock-out"
                  hx-target='#attendance-activity-container'
                  hx-swap='innerHTML'><ion-icon class="oh-navbar__clock-icon mr-2
                  text-warning"
                    name="exit-outline"></ion-icon>
               <span class="hr-check-in-out-text">{check_out}</span>
              </button>
            """.format(
                check_out=_("Check-Out")
            )
        )
    return HttpResponse(
        _("You Don't have work information filled or your employee detail neither entered ")
    )


def clock_out_attendance_and_activity(employee, date_today, now):
    """
    Clock out the attendance and activity
    args:
        employee    : employee instance
        date_today  : today date
        now         : now
    """

    attendance_activities = AttendanceActivity.objects.filter(
        employee_id=employee
    ).order_by("attendance_date", "id")
    if attendance_activities.exists():
        attendance_activity = attendance_activities.last()
        attendance_activity.clock_out = now
        attendance_activity.clock_out_date = date_today
        attendance_activity.save()
    attendance_activities = attendance_activities.filter(~Q(clock_out=None)).filter(
        attendance_date=attendance_activity.attendance_date
    )
    # Here calculate the total durations between the attendance activities

    duration = 0
    for attendance_activity in attendance_activities:
        in_datetime, out_datetime = activity_datetime(attendance_activity)
        difference = out_datetime - in_datetime
        days_second = difference.days * 24 * 3600
        seconds = difference.seconds
        total_seconds = days_second + seconds
        duration = duration + total_seconds
    duration = format_time(duration)
    # update clock out of attendance
    attendance = Attendance.objects.filter(employee_id=employee).order_by(
        "-attendance_date", "-id"
    )[0]
    attendance.attendance_clock_out = now
    attendance.attendance_clock_out_date = date_today
    attendance.attendance_worked_hour = duration
    attendance.save()
    # Overtime calculation
    attendance.attendance_overtime = overtime_calculation(attendance)

    # Validate the attendance as per the condition
    attendance.attendance_validated = attendance_validate(attendance)
    attendance.save()

    return


def early_out_create(attendance):
    """
    Used to create early out report
    args:
        attendance : attendance obj
    """

    late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "early_out"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def early_out(attendance, start_time, end_time):
    """
    This method is used to mark the early check-out attendance before the shift ends
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        start_end : attendance day shift end time
    """

    now_sec = strtime_seconds(datetime.now().strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    if start_time > end_time:
        # Early out condition for night shift
        if now_sec < mid_day_sec:
            if now_sec < end_time:
                # Early out condition for general shift
                early_out_create(attendance)
        else:
            early_out_create(attendance)
        return
    if end_time > now_sec:
        early_out_create(attendance)
    return


@login_required
def clock_out(request):
    """
    This method is used to set the out date and time for attendance and attendance activity
    """
    employee, work_info = employee_exists(request)
    shift = work_info.shift_id
    date_today = date.today()
    day = date_today.strftime("%A").lower()
    day = EmployeeShiftDay.objects.get(day=day)
    attendance = (
        Attendance.objects.filter(employee_id=employee)
        .order_by("id", "attendance_date")
        .last()
    )
    if attendance is not None:
        day = attendance.attendance_day
    now = datetime.now().strftime("%H:%M")
    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
        day=day, shift=shift
    )
    early_out_instance = attendance.late_come_early_out.filter(type="early_out")
    if not early_out_instance.exists():
        early_out(
            attendance=attendance, start_time=start_time_sec, end_time=end_time_sec
        )

    clock_out_attendance_and_activity(employee=employee, date_today=date_today, now=now)
    return HttpResponse(
        """
              <button class="oh-btn oh-btn--success-outline " 
              hx-get="/attendance/clock-in" 
              hx-target='#attendance-activity-container' 
              hx-swap='innerHTML'>
              <ion-icon class="oh-navbar__clock-icon mr-2 text-success" 
              name="enter-outline"></ion-icon>
               <span class="hr-check-in-out-text">{check_in}</span>
              </button>
            """.format(
            check_in=_("Check-In")
        )
    )
