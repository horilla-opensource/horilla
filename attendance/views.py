"""
views.py

This module contains the view functions for handling HTTP requests and rendering
responses in your application.

Each view function corresponds to a specific URL route and performs the necessary
actions to handle the request, process data, and generate a response.

This module is part of the recruitment project and is intended to
provide the main entry points for interacting with the application's functionality.
"""

import contextlib
import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from attendance.filters import (
    AttendanceActivityFilter,
    AttendanceActivityReGroup,
    AttendanceFilters,
    AttendanceOverTimeFilter,
    AttendanceOvertimeReGroup,
    AttendanceReGroup,
    LateComeEarlyOutFilter,
    LateComeEarlyOutReGroup,
)
from attendance.forms import (
    AttendanceForm,
    AttendanceOverTimeForm,
    AttendanceUpdateForm,
    AttendanceValidationConditionForm,
)
from attendance.methods.utils import (
    activity_datetime,
    employee_exists,
    format_time,
    is_reportingmanger,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceValidationCondition,
)
from base.methods import choosesubordinates, filtersubordinates, sortby
from base.models import Department, EmployeeShiftDay, EmployeeShiftSchedule
from employee.models import Employee
from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from notifications.signals import notify

# Create your views here.


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


def attendance_validate(attendance):
    """
    This method is is used to check condition for at work in AttendanceValidationCondition
    model instance it return true if at work is smaller than condition
    args:
        attendance : attendance object
    """

    conditions = AttendanceValidationCondition.objects.all()
    # Set the default condition for 'at work' to 9:00 AM
    condition_for_at_work = strtime_seconds("09:00")
    if conditions.exists():
        condition_for_at_work = strtime_seconds(conditions[0].validation_at_work)
    at_work = strtime_seconds(attendance.attendance_worked_hour)
    return condition_for_at_work >= at_work


@login_required
@manager_can_enter("attendance.add_attendance")
def attendance_create(request):
    """
    This method is used to render attendance create form and save if it is valid
    """
    form = AttendanceForm()
    form = choosesubordinates(request, form, "attendance.add_attendance")
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        form = choosesubordinates(request, form, "attendance.add_attendance")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance added."))
            response = render(
                request, "attendance/attendance/form.html", {"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "attendance/attendance/form.html", {"form": form})


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, 50)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@manager_can_enter("attendance.view_attendance")
def attendance_view(request):
    """
    This method is used to view attendances.
    """
    previous_data = request.environ["QUERY_STRING"]
    form = AttendanceForm()
    condition = AttendanceValidationCondition.objects.first()
    minot = strtime_seconds("00:30")
    if condition is not None:
        minot = strtime_seconds(condition.minimum_overtime_to_approve)
    validate_attendances = Attendance.objects.filter(attendance_validated=False)
    attendances = Attendance.objects.filter(attendance_validated=True)
    ot_attendances = Attendance.objects.filter(
        attendance_overtime_approve=False,
        overtime_second__gte=minot,
        attendance_validated=True,
    )
    filter_obj = AttendanceFilters(queryset=Attendance.objects.all())
    attendances = filtersubordinates(request, attendances, "attendance.view_attendance")
    validate_attendances = filtersubordinates(
        request, validate_attendances, "attendance.view_attendance"
    )
    ot_attendances = filtersubordinates(
        request, ot_attendances, "attendance.view_attendance"
    )

    return render(
        request,
        "attendance/attendance/attendance_view.html",
        {
            "form": form,
            "validate_attendances": paginator_qry(
                validate_attendances, request.GET.get("vpage")
            ),
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "overtime_attendances": paginator_qry(
                ot_attendances, request.GET.get("opage")
            ),
            "f": filter_obj,
            "pd": previous_data,
            "gp_fields": AttendanceReGroup.fields,
        },
    )


@login_required
@manager_can_enter("attendance.view_attendance")
def attendance_search(request):
    """
    This method is used to search attendance by employee
    """
    previous_data = request.environ["QUERY_STRING"]
    field = request.GET.get("field")
    minot = strtime_seconds("00:30")
    condition = AttendanceValidationCondition.objects.first()
    if condition is not None:
        minot = strtime_seconds(condition.minimum_overtime_to_approve)

    validate_attendances = Attendance.objects.filter(attendance_validated=False)
    attendances = Attendance.objects.filter(attendance_validated=True)
    ot_attendances = Attendance.objects.filter(
        attendance_overtime_approve=False,
        overtime_second__gte=minot,
        attendance_validated=True,
    )

    validate_attendances = AttendanceFilters(request.GET, validate_attendances).qs
    attendances = AttendanceFilters(request.GET, attendances).qs
    ot_attendances = AttendanceFilters(request.GET, ot_attendances).qs

    template = "attendance/attendance/tab_content.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        attendances = attendances.order_by(field_copy)
        validate_attendances = validate_attendances.order_by(field_copy)
        ot_attendances = ot_attendances.order_by(field_copy)
        template = "attendance/attendance/group_by.html"

    attendances = filtersubordinates(request, attendances, "attendance.view_attendance")
    validate_attendances = filtersubordinates(
        request, validate_attendances, "attendance.view_attendance"
    )
    ot_attendances = filtersubordinates(
        request, ot_attendances, "attendance.view_attendance"
    )

    attendances = sortby(request, attendances, "sortby")
    validate_attendances = sortby(request, validate_attendances, "sortby")
    ot_attendances = sortby(request, ot_attendances, "sortby")

    return render(
        request,
        template,
        {
            "validate_attendances": paginator_qry(
                validate_attendances, request.GET.get("vpage")
            ),
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "overtime_attendances": paginator_qry(
                ot_attendances, request.GET.get("opage")
            ),
            "pd": previous_data,
            "field": field,
        },
    )


@login_required
@manager_can_enter("attendance.change_attendance")
def attendance_update(request, obj_id):
    """
    This method render form to update attendance and save if the form is valid
    args:
        obj_id : attendance id
    """
    attendance = Attendance.objects.get(id=obj_id)
    form = AttendanceUpdateForm(
        instance=attendance,
    )
    form = choosesubordinates(request, form, "attendance.change_attendance")
    if request.method == "POST":
        form = AttendanceUpdateForm(request.POST, instance=attendance)
        form = choosesubordinates(request, form, "attendance.change_attendance")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance Updated."))
            response = render(
                request, "attendance/attendance/update_form.html", {"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "attendance/attendance/update_form.html",
        {
            "form": form,
        },
    )


@login_required
@permission_required("attendance.delete_attendance")
@require_http_methods(["POST"])
def attendance_delete(request, obj_id):
    """
    This method is used to delete attendance.
    args:
        obj_id : attendance id
    """
    attendance = Attendance.objects.get(id=obj_id)
    month = attendance.attendance_date
    month = month.strftime("%B").lower()
    overtime = attendance.employee_id.employee_overtime.filter(month=month).last()
    if overtime is not None:
        if attendance.attendance_overtime_approve:
            # Subtract overtime of this attendance
            total_overtime = strtime_seconds(overtime.overtime)
            attendance_overtime_seconds = strtime_seconds(
                attendance.attendance_overtime
            )
            if total_overtime > attendance_overtime_seconds:
                total_overtime = total_overtime - attendance_overtime_seconds
            else:
                total_overtime = attendance_overtime_seconds - total_overtime
            overtime.overtime = format_time(total_overtime)
            overtime.save()
        try:
            attendance.delete()
            messages.success(request, _("Attendance deleted."))
        except Exception as error:
            messages.error(request, error)
            messages.error(request, _("You cannot delete this attendance"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@require_http_methods(["POST"])
@permission_required("attendance.delete_attendance")
def attendance_bulk_delete(request):
    """
    This method is used to delete bulk of attendances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for attendance_id in ids:
        try:
            attendance = Attendance.objects.get(id=attendance_id)
            month = attendance.attendance_date
            month = month.strftime("%B").lower()
            overtime = attendance.employee_id.employee_overtime.filter(
                month=month
            ).last()
            if overtime is not None:
                if attendance.attendance_overtime_approve:
                    # Subtract overtime of this attendance
                    total_overtime = strtime_seconds(overtime.overtime)
                    attendance_overtime_seconds = strtime_seconds(
                        attendance.attendance_overtime
                    )
                    if total_overtime > attendance_overtime_seconds:
                        total_overtime = total_overtime - attendance_overtime_seconds
                    else:
                        total_overtime = attendance_overtime_seconds - total_overtime
                    overtime.overtime = format_time(total_overtime)
                    overtime.save()
                try:
                    attendance.delete()
                    messages.success(request, _("Attendance Deleted"))
                except:
                    messages.error(
                        request,
                        _(
                            "You cannot delete this %(attendance)s"
                            % {"attendance": attendance}
                        ),
                    )
        except:
            pass

    return JsonResponse({"message": "Success"})


@login_required
def view_my_attendance(request):
    """
    This method is used to view self attendances of employee
    """
    user = request.user
    try:
        employee = user.employee_get
    except:
        return redirect("/employee/employee-profile")
    employee = user.employee_get
    employee_attendances = employee.employee_attendances.all()
    filter = AttendanceFilters()
    return render(
        request,
        "attendance/own_attendance/view_own_attendances.html",
        {
            "attendances": paginator_qry(employee_attendances, request.GET.get("page")),
            "f": filter,
        },
    )


@login_required
@hx_request_required
def filter_own_attendance(request):
    """
    This method is used to filter own attendances
    """
    attendances = Attendance.objects.filter(employee_id=request.user.employee_get)
    attendances = AttendanceFilters(request.GET, queryset=attendances).qs
    return render(
        request,
        "attendance/own_attendance/attendances.html",
        {"attendances": paginator_qry(attendances, request.GET.get("page"))},
    )


@login_required
def own_attendance_sort(request):
    """
    This method is used to sort out attendances
    """
    attendances = Attendance.objects.filter(employee_id=request.user.employee_get)
    previous_data = request.environ["QUERY_STRING"]
    attendances = sortby(request, attendances, "orderby")
    return render(
        request,
        "attendance/own_attendance/attendances.html",
        {
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "pd": previous_data,
        },
    )


@login_required
@manager_can_enter("attendance.add_attendanceovertime")
def attendance_overtime_create(request):
    """
    This method is used to render overtime creating form and save if the form is valid
    """
    form = AttendanceOverTimeForm()
    form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
    if request.method == "POST":
        form = AttendanceOverTimeForm(request.POST)
        form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance account added."))
            response = render(
                request, "attendance/attendance_account/form.html", {"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "attendance/attendance_account/form.html", {"form": form})


@login_required
@manager_can_enter("attendance.view_attendanceovertime")
def attendance_overtime_view(request):
    """
    This method is used to view attendance account or overtime account.
    """
    previous_data = request.environ["QUERY_STRING"]
    accounts = AttendanceOverTime.objects.all()
    accounts = filtersubordinates(
        request, accounts, "attendance.view_attendanceovertime"
    )
    form = AttendanceOverTimeForm()
    form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
    filter_obj = AttendanceOverTimeFilter()
    return render(
        request,
        "attendance/attendance_account/attendance_overtime_view.html",
        {
            "accounts": paginator_qry(accounts, request.GET.get("page")),
            "form": form,
            "pd": previous_data,
            "f": filter_obj,
            "gp_fields": AttendanceOvertimeReGroup.fields,
        },
    )


@login_required
@manager_can_enter("attendance.view_attendanceovertime")
def attendance_overtime_search(request):
    """
    This method is used to search attendance overtime account by employee.
    """
    field = request.GET.get("field")
    previous_data = request.environ["QUERY_STRING"]

    accounts = AttendanceOverTimeFilter(request.GET).qs
    form = AttendanceOverTimeForm()
    template = "attendance/attendance_account/overtime_list.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        accounts = accounts.order_by(field_copy)
        template = "attendance/attendance_account/group_by.html"
    accounts = sortby(request, accounts, "sortby")
    accounts = filtersubordinates(
        request, accounts, "attendance.view_attendanceovertime"
    )
    return render(
        request,
        template,
        {
            "accounts": paginator_qry(accounts, request.GET.get("page")),
            "form": form,
            "pd": previous_data,
            "field": field,
        },
    )


@login_required
@manager_can_enter("attendance.change_attendanceovertime")
@hx_request_required
def attendance_overtime_update(request, obj_id):
    """
    This method is used to update attendance overtime and save if the forms is valid
    args:
        obj_id : attendance overtime id
    """
    overtime = AttendanceOverTime.objects.get(id=obj_id)
    form = AttendanceOverTimeForm(instance=overtime)
    form = choosesubordinates(request, form, "attendance.change_attendanceovertime")
    if request.method == "POST":
        form = AttendanceOverTimeForm(request.POST, instance=overtime)
        form = choosesubordinates(request, form, "attendance.change_attendanceovertime")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance account updated successfully."))
            response = render(
                request,
                "attendance/attendance_account/update_form.html",
                {"form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request, "attendance/attendance_account/update_form.html", {"form": form}
    )


@login_required
@permission_required("attendance.delete_AttendanceOverTime")
@require_http_methods(["POST"])
def attendance_overtime_delete(request, obj_id):
    """
    This method is used to delete attendance overtime
    args:
        obj_id : attendance overtime id
    """
    try:
        AttendanceOverTime.objects.get(id=obj_id).delete()
        messages.success(request, _("OT account deleted."))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _("You cannot delete this attendance OT"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("attendance.view_attendanceactivity")
def attendance_activity_view(request):
    """
    This method will render a template to view all attendance activities
    """
    attendance_activities = AttendanceActivity.objects.all()
    previous_data = request.environ["QUERY_STRING"]
    filter_obj = AttendanceActivityFilter()
    return render(
        request,
        "attendance/attendance_activity/attendance_activity_view.html",
        {
            "data": paginator_qry(attendance_activities, request.GET.get("page")),
            "pd": previous_data,
            "f": filter_obj,
            "gp_fields": AttendanceActivityReGroup.fields,
        },
    )


@login_required
@permission_required("attendance.view_attendanceactivity")
def attendance_activity_search(request):
    """
    This method is used to search attendance activity
    """
    previous_data = request.environ["QUERY_STRING"]
    field = request.GET.get("field")
    attendance_activities = AttendanceActivityFilter(
        request.GET,
    ).qs
    template = "attendance/attendance_activity/activity_list.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        attendance_activities = attendance_activities.order_by(field_copy)
        template = "attendance/attendance_activity/group_by.html"
    attendance_activities = filtersubordinates(
        request, attendance_activities, "attendance.view_attendanceactivity"
    )

    attendance_activities = sortby(request, attendance_activities, "orderby")
    return render(
        request,
        template,
        {
            "data": paginator_qry(attendance_activities, request.GET.get("page")),
            "pd": previous_data,
            "field": field,
        },
    )


@login_required
@permission_required("attendance.delete_attendanceactivity")
@require_http_methods(["POST", "DELTE"])
def attendance_activity_delete(request, obj_id):
    """
    This method is used to delete attendance activity
    args:
        obj_id : attendance activity id
    """
    try:
        AttendanceActivity.objects.get(id=obj_id).delete()
        messages.success(request, _("Attendance activity deleted"))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _("You cannot delete this activity"))
    return redirect("/attendance/attendance-activity-view")


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
        "You Don't have work information filled or your employee detail neither entered "
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


@login_required
@manager_can_enter("attendance.view_attendancelatecomeearlyout")
def late_come_early_out_view(request):
    """
    This method render template to view all late come early out entries
    """
    reports = AttendanceLateComeEarlyOut.objects.all()
    reports = filtersubordinates(
        request, reports, "attendance.view_attendancelatecomeearlyout"
    )
    filter_obj = LateComeEarlyOutFilter()
    return render(
        request,
        "attendance/late_come_early_out/reports.html",
        {
            "data": paginator_qry(reports, request.GET.get("page")),
            "f": filter_obj,
            "gp_fields": LateComeEarlyOutReGroup.fields,
        },
    )


@login_required
@manager_can_enter("attendance.view_attendancelatecomeearlyout")
def late_come_early_out_search(request):
    """
    This method is used to search late come early out by employee.
    Also include filter and pagination.
    """
    field = request.GET.get("field")
    previous_data = request.environ["QUERY_STRING"]

    reports = LateComeEarlyOutFilter(
        request.GET,
    ).qs
    template = "attendance/late_come_early_out/report_list.html"
    if field != "" and field is not None:
        template = "attendance/late_come_early_out/group_by.html"
        field_copy = field.replace(".", "__")
        reports = reports.order_by(field_copy)
    reports = filtersubordinates(
        request, reports, "attendance.view_attendancelatecomeearlyout"
    )
    reports = sortby(request, reports, "sortby")

    return render(
        request,
        template,
        {
            "data": paginator_qry(reports, request.GET.get("page")),
            "pd": previous_data,
            "field": field,
        },
    )


@login_required
@permission_required("attendance.delete_attendancelatecomeearlyout")
@require_http_methods(["POST"])
def late_come_early_out_delete(request, obj_id):
    """
    This method is used to delete the late come early out instance
    args:
        obj_id : late come early out instance id
    """
    try:
        AttendanceLateComeEarlyOut.objects.get(id=obj_id).delete()
        messages.success(request, _("Late-in early-out deleted"))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _("You cannot delete this Late-in early-out"))

    return redirect("/attendance/late-come-early-out-view")


@login_required
@permission_required("attendance.add_attendancevalidationcondition")
def validation_condition_create(request):
    """
    This method render a form to create attendance validation conditions,
    and create if the form is valid.
    """
    form = AttendanceValidationConditionForm()
    condition = AttendanceValidationCondition.objects.first()
    if request.method == "POST":
        form = AttendanceValidationConditionForm(request.POST)
        if form.is_valid():
            form.save()
    return render(
        request,
        "attendance/break_point/condition.html",
        {"form": form, "condition": condition},
    )


@login_required
@permission_required("attendance.change_attendancevalidationcondition")
def validation_condition_update(request, obj_id):
    """
    This method is used to update validation condition
    Args:
        obj_id : validation condition instance id
    """
    condition = AttendanceValidationCondition.objects.get(id=obj_id)
    form = AttendanceValidationConditionForm(instance=condition)
    if request.method == "POST":
        form = AttendanceValidationConditionForm(request.POST, instance=condition)
        if form.is_valid():
            form.save()
    return render(
        request,
        "attendance/break_point/condition.html",
        {"form": form, "condition": condition},
    )


@login_required
@permission_required("attendance.change_attendancevalidationcondition")
@require_http_methods(["POST"])
def validation_condition_delete(request, obj_id):
    """
    This method is used to delete created validation condition
    args:
        obj_id  : validation condition id
    """
    try:
        AttendanceValidationCondition.objects.get(id=obj_id).delete()
        messages.success(request, _("validation condition deleted."))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _("You cannot delete this validation condition."))
    return redirect("/attendance/validation-condition-view")


@login_required
@require_http_methods(["POST"])
@manager_can_enter("attendance.change_attendance")
def validate_bulk_attendance(request):
    """
    This method is used to validate bulk of attendances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for attendance_id in ids:
        attendance = Attendance.objects.get(id=attendance_id)
        attendance.attendance_validated = True
        attendance.save()
        messages.success(request, _("Attendance validated."))
        notify.send(
            request.user.employee_get,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your attendance for the date {attendance.attendance_date} is validated",
            verb_ar=f"تم التحقق من حضورك في تاريخ {attendance.attendance_date}",
            verb_de=f"Ihre Anwesenheit für das Datum {attendance.attendance_date} wurde bestätigt",
            verb_es=f"Se ha validado su asistencia para la fecha {attendance.attendance_date}",
            verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée",
            redirect=reverse("view-my-attendance"),
            icon="checkmark",
        )
    return JsonResponse({"message": f"{attendance.employee_id} success"})


@login_required
def validate_this_attendance(request, obj_id):
    """
    This method is used to validate attendance
    args:
        id  : attendance id
    """
    attendance = Attendance.objects.get(id=obj_id)
    if is_reportingmanger(request, attendance) or request.user.has_perm(
        "attendance.change_attendance"
    ):
        attendance = Attendance.objects.get(id=obj_id)
        attendance.attendance_validated = True
        attendance.save()
        messages.success(request, _("Attendance validated."))
        notify.send(
            request.user.employee_get,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your attendance for the date {attendance.attendance_date} is validated",
            verb_ar=f"تم تحقيق حضورك في تاريخ {attendance.attendance_date}",
            verb_de=f"Deine Anwesenheit für das Datum {attendance.attendance_date} ist bestätigt.",
            verb_es=f"Se valida tu asistencia para la fecha {attendance.attendance_date}.",
            verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée.",
            redirect=reverse("view-my-attendance"),
            icon="checkmark",
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You Dont Have Permission")


@login_required
def revalidate_this_attendance(request, obj_id):
    """
    This method is used to not validate the attendance.
    args:
        id  : attendance id
    """

    attendance = Attendance.objects.get(id=obj_id)
    if is_reportingmanger(request, attendance) or request.user.has_perm(
        "attendance.change_attendance"
    ):
        attendance.attendance_validated = False
        attendance.save()
        with contextlib.suppress(Exception):
            notify.send(
                request.user.employee_get,
                recipient=(
                    attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                ),
                verb=f"{attendance.employee_id} requested revalidation for \
                    {attendance.attendance_date} attendance",
                verb_ar=f"{attendance.employee_id} طلب إعادة التحقق من حضور تاريخ {attendance.attendance_date}",
                verb_de=f"{attendance.employee_id} beantragte eine Neubewertung der Teilnahme am {attendance.attendance_date}",
                verb_es=f"{attendance.employee_id} solicitó la validación nuevamente para la asistencia del {attendance.attendance_date}",
                verb_fr=f"{attendance.employee_id} a demandé une revalidation pour la présence du {attendance.attendance_date}",
                redirect=reverse("view-my-attendance"),
                icon="refresh",
            )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return HttpResponse("You Cannot Request for others attendance")


@login_required
@manager_can_enter("attendance.change_attendance")
def approve_overtime(request, obj_id):
    """
    This method is used to approve attendance overtime
    args:
        obj_id  : attendance id
    """
    attendance = Attendance.objects.get(id=obj_id)
    attendance.attendance_overtime_approve = True
    attendance.save()
    with contextlib.suppress(Exception):
        notify.send(
            request.user.employee_get,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your {attendance.attendance_date}'s attendance overtime approved.",
            verb_ar=f"تمت الموافقة على إضافة ساعات العمل الإضافية لتاريخ {attendance.attendance_date}.",
            verb_de=f"Die Überstunden für den {attendance.attendance_date} wurden genehmigt.",
            verb_es=f"Se ha aprobado el tiempo extra de asistencia para el {attendance.attendance_date}.",
            verb_fr=f"Les heures supplémentaires pour la date {attendance.attendance_date} ont été approuvées.",
            redirect=reverse("attendance-overtime-view"),
            icon="checkmark",
        )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@manager_can_enter("attendance.change_attendance")
def approve_bulk_overtime(request):
    """
    This method is used to approve bulk of attendance
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for attendance_id in ids:
        attendance = Attendance.objects.get(id=attendance_id)
        attendance.attendance_overtime_approve = True
        attendance.save()
        messages.success(request, _("Overtime approved"))
        notify.send(
            request.user.employee_get,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Overtime approved for {attendance.attendance_date}'s attendance",
            verb_ar=f"تمت الموافقة على العمل الإضافي لحضور تاريخ {attendance.attendance_date}",
            verb_de=f"Überstunden für die Anwesenheit am {attendance.attendance_date} genehmigt",
            verb_es=f"Horas extra aprobadas para la asistencia del {attendance.attendance_date}",
            verb_fr=f"Heures supplémentaires approuvées pour la présence du {attendance.attendance_date}",
            redirect=reverse("attendance-overtime-view"),
            icon="checkmark",
        )

    return JsonResponse({"message": "Success"})


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
