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
from datetime import datetime
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from horilla.decorators import (
    permission_required,
    login_required,
    hx_request_required,
    manager_can_enter,
)
from base.methods import filtersubordinates, choosesubordinates
from notifications.signals import notify
from attendance.filters import (
    AttendanceFilters,
    AttendanceOverTimeFilter,
    LateComeEarlyOutFilter,
    AttendanceActivityFilter,
)
from attendance.forms import (
    AttendanceForm,
    AttendanceOverTimeForm,
    AttendanceValidationConditionForm,
    AttendanceUpdateForm,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceOverTime,
    AttendanceLateComeEarlyOut,
    AttendanceValidationCondition,
)
from attendance.filters import (
    AttendanceReGroup,
    AttendanceOvertimeReGroup,
    LateComeEarlyOutReGroup,
    AttendanceActivityReGroup,
)


# Create your views here.


def intersection_list(list1, list2):
    """
    This method is used to intersect two list
    """
    return [value for value in list1 if value in list2]


def format_time(seconds):
    """
    this method is used to formate seconds to H:M and return it
    args:
        seconds : seconds
    """

    hour = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int((seconds % 3600) % 60)
    return f"{hour:02d}:{minutes:02d}"


def strtime_seconds(time):
    """
    this method is used reconvert time in H:M formate string back to seconds and return it
    args:
        time : time in H:M format
    """

    ftr = [3600, 60, 1]
    return sum(a * b for a, b in zip(ftr, map(int, time.split(":"))))


def is_reportingmanger(request, instance):
    """
    if the instance have employee id field then you can use this method to know the
    request user employee is the reporting manager of the instance
    args :
        request : request
        instance : an object or instance of any model contain employee_id foreign key field
    """

    manager = request.user.employee_get
    try:
        employee_workinfo_manager = (
            instance.employee_id.employee_work_info.reporting_manager_id
        )
    except Exception:
        return HttpResponse("This Employee Dont Have any work information")
    return manager == employee_workinfo_manager


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
    previous_data = request.GET.urlencode()
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
    previous_data = request.GET.urlencode()
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
    previous_data = request.GET.urlencode()
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


def employee_exists(request):
    """
    This method return the employee instance and work info if not exists return None instead
    """
    employee, employee_work_info = None, None
    try:
        employee = request.user.employee_get
        employee_work_info = employee.employee_work_info
    finally:
        return (employee, employee_work_info)


def shift_schedule_today(day, shift):
    """
    This function is used to find shift schedules for the day,
    it will returns min hour,start time seconds  end time seconds
    args:
        shift   : shift instance
        day     : shift day object
    """
    schedule_today = day.day_schedule.filter(shift_id=shift)
    start_time_sec, end_time_sec, minimum_hour = 0, 0, "00:00"
    if schedule_today.exists():
        schedule_today = schedule_today[0]
        minimum_hour = schedule_today.minimum_working_hour
        start_time_sec = strtime_seconds(schedule_today.start_time.strftime("%H:%M"))
        end_time_sec = strtime_seconds(schedule_today.end_time.strftime("%H:%M"))
    return (minimum_hour, start_time_sec, end_time_sec)


def overtime_calculation(attendance):
    """
    This method is used to calculate overtime of the attendance, it will
    return difference between attendance worked hour and minimum hour if
    and only worked hour greater than minimum hour, else return 00:00
    args:
        attendance : attendance instance
    """

    minimum_hour = attendance.minimum_hour
    at_work = attendance.attendance_worked_hour
    at_work_sec = strtime_seconds(at_work)
    minimum_hour_sec = strtime_seconds(minimum_hour)
    if at_work_sec > minimum_hour_sec:
        return format_time((at_work_sec - minimum_hour_sec))
    return "00:00"


def activity_datetime(attendance_activity):
    """
    This method is used to convert clock-in and clock-out of activity as datetime object
    args:
        attendance_activity : attendance activity instance
    """

    # in
    in_year = attendance_activity.clock_in_date.year
    in_month = attendance_activity.clock_in_date.month
    in_day = attendance_activity.clock_in_date.day
    in_hour = attendance_activity.clock_in.hour
    in_minute = attendance_activity.clock_in.minute
    # out
    out_year = attendance_activity.clock_out_date.year
    out_month = attendance_activity.clock_out_date.month
    out_day = attendance_activity.clock_out_date.day
    out_hour = attendance_activity.clock_out.hour
    out_minute = attendance_activity.clock_out.minute
    return datetime(in_year, in_month, in_day, in_hour, in_minute), datetime(
        out_year, out_month, out_day, out_hour, out_minute
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
            redirect="/attendance/view-my-attendance",
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
            redirect="/attendance/view-my-attendance",
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
                redirect="/attendance/view-my-attendance",
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
            redirect="/attendance/attendance-overtime-view",
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
            redirect="/attendance/attendance-overtime-view",
            icon="checkmark",
        )

    return JsonResponse({"message": "Success"})
