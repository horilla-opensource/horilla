"""
views.py

This module contains the view functions for handling HTTP requests and rendering
responses in your application.

Each view function corresponds to a specific URL route and performs the necessary
actions to handle the request, process data, and generate a response.

This module is part of the recruitment project and is intended to
provide the main entry points for interacting with the application's functionality.
"""

import logging
import uuid

from horilla.horilla_settings import DYNAMIC_URL_PATTERNS, HORILLA_DATE_FORMATS
from horilla.methods import remove_dynamic_url

logger = logging.getLogger(__name__)

import calendar
import contextlib
import io
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs

import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.validators import validate_ipv46_address
from django.db import transaction
from django.db.models import ProtectedError
from django.forms import ValidationError
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone as django_timezone
from django.utils.timezone import now
from django.utils.translation import gettext as __
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
    AttendanceActivityExportForm,
    AttendanceExportForm,
    AttendanceForm,
    AttendanceOverTimeExportForm,
    AttendanceOverTimeForm,
    AttendanceRequestCommentForm,
    AttendanceUpdateForm,
    AttendanceValidationConditionForm,
    GraceTimeAssignForm,
    GraceTimeForm,
    LateComeEarlyOutExportForm,
    NewRequestForm,
)
from attendance.methods.utils import (
    Request,
    attendance_day_checking,
    format_time,
    is_reportingmanger,
    monthly_leave_days,
    paginator_qry,
    parse_date,
    parse_datetime,
    parse_time,
    sort_activity_dicts,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceRequestComment,
    AttendanceRequestFile,
    AttendanceValidationCondition,
    BatchAttendance,
    GraceTime,
    WorkRecords,
)
from attendance.views.handle_attendance_errors import handle_attendance_errors
from attendance.views.process_attendance_data import process_attendance_data
from base.forms import AttendanceAllowedIPForm, TrackLateComeEarlyOutForm
from base.methods import (
    choosesubordinates,
    closest_numbers,
    eval_validate,
    export_data,
    filtersubordinates,
    filtersubordinatesemployeemodel,
    get_key_instances,
    get_pagination,
)
from base.models import (
    AttendanceAllowedIP,
    EmployeeShiftSchedule,
    TrackLateComeEarlyOut,
    WorkType,
)
from employee.filters import EmployeeFilter
from employee.models import Employee, EmployeeWorkInformation
from horilla.decorators import (
    hx_request_required,
    install_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from notifications.signals import notify


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
@hx_request_required
def profile_attendance_tab(request):
    """
    This function is used to view attendance tab of an employee in profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return asset-request-tab template

    """
    user = request.user
    employee = user.employee_get
    employee_attendances = employee.employee_attendances.all()
    attendances_ids = json.dumps([instance.id for instance in employee_attendances])
    context = {
        "attendances": employee_attendances,
        "attendances_ids": attendances_ids,
    }
    return render(request, "tabs/profile-attendance-tab.html", context)


@login_required
@manager_can_enter("employee.view_employee")
def attendance_tab(request, emp_id):
    """
    This function is used to view attendance tab of an employee in individual view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return attendance-tab template
    """

    requests = Attendance.objects.filter(
        is_validate_request=True,
        employee_id=emp_id,
    )
    attendances_ids = json.dumps([instance.id for instance in requests])
    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id=emp_id
    )
    validate_attendances_ids = json.dumps(
        [instance.id for instance in validate_attendances]
    )
    accounts = AttendanceOverTime.objects.filter(employee_id=emp_id)
    accounts_ids = json.dumps([instance.id for instance in accounts])

    context = {
        "requests": requests,
        "attendances_ids": attendances_ids,
        "accounts": accounts,
        "accounts_ids": accounts_ids,
        "validate_attendances": validate_attendances,
        "validate_attendances_ids": validate_attendances_ids,
    }
    return render(request, "tabs/attendance-tab.html", context=context)


@login_required
@hx_request_required
@manager_can_enter("attendance.add_attendance")
def attendance_create(request):
    """
    This method is used to render attendance create form and save if it is valid
    """
    if request.GET.get("previous_url"):
        data = request.GET.dict()
        employee_list = request.GET.getlist("employee_id")
        data["employee_id"] = employee_list
        form = AttendanceForm(initial=data)
    else:
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


@login_required
@permission_required("attendance.add_attendance")
def attendance_excel(_request):
    """
    Generate an empty Excel template for attendance data with predefined columns.

    Returns:
        HttpResponse: An HTTP response containing an empty Excel template with predefined columns.
    """
    try:
        columns = [
            "Badge ID",
            "Shift",
            "Work type",
            "Attendance date",
            "Check-in date",
            "Check-in",
            "Check-out date",
            "Check-out",
            "Worked hour",
            "Minimum hour",
        ]
        data_frame = pd.DataFrame(columns=columns)
        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = 'attachment; filename="my_excel_file.xlsx"'
        data_frame.to_excel(response, index=False)
        return response
    except Exception as exception:
        return HttpResponse(exception)


@login_required
@permission_required("attendance.add_attendance")
def attendance_import(request):
    """
    Save the import of attendance data from an uploaded Excel file, validate the data,
    and return an Excel file with error details if validation fails for anyone
    of the attendance data.

    Parameters:
        request (HttpRequest): The HTTP request object containing the uploaded Excel file.

    Returns:
        HttpResponse or redirect: An HTTP response with an Excel file containing error details
        if validation fails, or a redirect to the attendance view if successful.
    """
    if request.method == "POST":
        file = request.FILES["attendance_import"]
        file_extension = file.name.split(".")[-1].lower()
        data_frame = (
            pd.read_csv(file) if file_extension == "csv" else pd.read_excel(file)
        )
        attendance_dicts = data_frame.to_dict("records")
        attendance_import = process_attendance_data(attendance_dicts)
        path_info = None
        if attendance_import:
            path_info = handle_attendance_errors(attendance_import)

    created_attendance_count = len(attendance_dicts) - len(attendance_import)
    context = {
        "created_count": created_attendance_count,
        "error_count": len(attendance_import),
        "model": _("Attendance"),
        "path_info": path_info,
    }
    html = render_to_string("import_popup.html", context)
    return HttpResponse(html)


@login_required
def attendance_export(request):
    resolver_match = request.resolver_match
    if (
        resolver_match
        and resolver_match.url_name
        and resolver_match.url_name == "attendance-info-export-form"
    ):
        return render(
            request,
            "attendance/attendance/export_filter.html",
            context={
                "export": AttendanceFilters(queryset=Attendance.objects.all()),
                "export_form": AttendanceExportForm(),
            },
        )
    return export_data(
        request=request,
        model=Attendance,
        filter_class=AttendanceFilters,
        form_class=AttendanceExportForm,
        file_name="Attendance_export",
    )


@login_required
@manager_can_enter("attendance.view_attendance")
def attendance_view(request):
    """
    This method is used to view attendances.
    """
    previous_data = request.GET.urlencode()
    form = AttendanceForm()
    condition = AttendanceValidationCondition.objects.first()
    minot = strtime_seconds("00:00")
    if condition is not None and condition.minimum_overtime_to_approve is not None:
        minot = strtime_seconds(condition.minimum_overtime_to_approve)
    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id__is_active=True
    )
    attendances = Attendance.objects.filter(
        attendance_validated=True, employee_id__is_active=True
    )
    # ot_attendances = Attendance.objects.filter(
    #     overtime_second__gte=minot,
    #     attendance_validated=True,
    #     employee_id__is_active=True,
    # )
    # for attendance in ot_attendances:
    #     attendance.min_ot_achieved = True
    ot_attendances = Attendance.objects.filter(
        overtime_second__gt=0,
        attendance_validated=True,
        employee_id__is_active=True,
    )
    filter_obj = AttendanceFilters(request.GET, queryset=attendances)
    attendances = filtersubordinates(
        request, filter_obj.qs, "attendance.view_attendance"
    )
    validate_attendances = AttendanceFilters(
        request.GET, queryset=validate_attendances
    ).qs
    validate_attendances = filtersubordinates(
        request, validate_attendances, "attendance.view_attendance"
    )
    ot_attendances = AttendanceFilters(request.GET, queryset=ot_attendances).qs
    ot_attendances = filtersubordinates(
        request, ot_attendances, "attendance.view_attendance"
    )
    check_attendance = Attendance.objects.all()
    if check_attendance.exists():
        template = "attendance/attendance/attendance_view.html"
    else:
        template = "attendance/attendance/attendance_empty.html"
    validate_attendances_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                validate_attendances, request.GET.get("vpage")
            ).object_list
        ]
    )
    ot_attendances_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                ot_attendances, request.GET.get("opage")
            ).object_list
        ]
    )
    attendances_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                attendances, request.GET.get("page")
            ).object_list
        ]
    )
    return render(
        request,
        template,
        {
            "form": form,
            # "validate_attendances": paginator_qry(
            #     validate_attendances, request.GET.get("vpage")
            # ),
            # "attendances": paginator_qry(attendances, request.GET.get("page")),
            # "overtime_attendances": paginator_qry(
            #     ot_attendances, request.GET.get("opage")
            # ),
            "validate_attendances_ids": validate_attendances_ids,
            "ot_attendances_ids": ot_attendances_ids,
            "attendances_ids": attendances_ids,
            "f": filter_obj,
            "pd": previous_data,
            "gp_fields": AttendanceReGroup.fields,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("attendance.change_attendance")
def attendance_update(request, obj_id):
    """
    This method render form to update attendance and save if the form is valid
    args:
        obj_id : attendance id
    """
    attendance = Attendance.objects.get(id=obj_id)
    if request.GET.get("previous_url"):
        form = AttendanceUpdateForm(initial=request.GET.dict())
    else:
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
            urlencode = request.GET.urlencode()
            modified_url = f"/attendance/attendance-view/?{urlencode}"
            return HttpResponse(
                f"""
                    <script>
                        window.location.reload();
                    </script>
                """
            )
    return render(
        request,
        "attendance/attendance/update_form.html",
        {"form": form, "urlencode": request.GET.urlencode(), "obj_id": obj_id},
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
    try:
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
            except ProtectedError as e:
                model_verbose_names_set = set()
                for obj in e.protected_objects:
                    model_verbose_names_set.add(__(obj._meta.verbose_name.capitalize()))
                model_names_str = ", ".join(model_verbose_names_set)
                messages.error(
                    request,
                    _(
                        ("An attendance entry for {} already exists.").format(
                            model_names_str
                        )
                    ),
                )
    except (Attendance.DoesNotExist, OverflowError):
        messages.error(request, _("Attendance Does not exists.."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("attendance.delete_attendance")
@require_http_methods(["POST"])
def attendance_bulk_delete(request):
    """
    This method is used to delete a bulk of attendances
    """
    success_count = 0
    error_messages = []
    ids = request.POST.getlist("ids", "[]")
    attendances = Attendance.objects.filter(id__in=ids)
    employee_ids = attendances.values_list("employee_id", flat=True)
    overtimes = AttendanceOverTime.objects.filter(
        employee_id__in=employee_ids
    ).in_bulk()

    with transaction.atomic():
        for attendance in attendances:
            try:
                month = attendance.attendance_date.strftime("%B").lower()
                overtime = overtimes.get(attendance.employee_id.id)

                if overtime and attendance.attendance_overtime_approve:
                    # Calculate the new overtime
                    total_overtime = strtime_seconds(overtime.overtime)
                    attendance_overtime_seconds = strtime_seconds(
                        attendance.attendance_overtime
                    )
                    total_overtime = abs(total_overtime - attendance_overtime_seconds)
                    overtime.overtime = format_time(total_overtime)
                    overtime.save()

                attendance.delete()
                success_count += 1

            except ProtectedError as e:
                model_verbose_names_set = {
                    __(obj._meta.verbose_name.capitalize())
                    for obj in e.protected_objects
                }
                model_names_str = ", ".join(model_verbose_names_set)
                error_messages.append(
                    f"An attendance entry is protected by: {model_names_str}."
                )

    # Build response messages
    if success_count:
        messages.success(request, f"{success_count} attendances deleted successfully.")
    for error in error_messages:
        messages.error(request, error)
    return redirect("/attendance/attendance-search")


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
    if employee_attendances.exists():
        template = "attendance/own_attendance/view_own_attendances.html"
    else:
        template = "attendance/own_attendance/own_empty.html"
    attendances_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                employee_attendances, request.GET.get("page")
            ).object_list
        ]
    )
    return render(
        request,
        template,
        {
            "attendances": paginator_qry(employee_attendances, request.GET.get("page")),
            "attendances_ids": attendances_ids,
            "f": filter,
            "gp_fields": AttendanceReGroup.fields,
        },
    )


@login_required
@hx_request_required
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
def attendance_overtime_view(request):
    """
    This method is used to view attendance account or overtime account.
    """
    previous_data = request.GET.urlencode()
    filter_obj = AttendanceOverTimeFilter(request.GET)
    if filter_obj.qs.exists():
        template = "attendance/attendance_account/attendance_overtime_view.html"
    else:
        template = "attendance/attendance_account/overtime_empty.html"
    self_account = filter_obj.qs.filter(employee_id__employee_user_id=request.user)
    accounts = filtersubordinates(
        request, filter_obj.qs, "attendance.view_attendanceovertime"
    )
    accounts = accounts | self_account
    accounts = accounts.distinct()
    form = AttendanceOverTimeForm()
    form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceOverTime, data_dict)
    return render(
        request,
        template,
        {
            "accounts": paginator_qry(accounts, request.GET.get("page")),
            "form": form,
            "pd": previous_data,
            "f": filter_obj,
            "gp_fields": AttendanceOvertimeReGroup.fields,
            "filter_dict": data_dict,
        },
    )


def attendance_account_export(request):
    if request.META.get("HTTP_HX_REQUEST") == "true":
        context = {
            "export_obj": AttendanceOverTimeFilter(),
            "export_fields": AttendanceOverTimeExportForm(),
        }

        return render(
            request,
            "attendance/attendance_account/attendance_account_export_filter.html",
            context=context,
        )
    return export_data(
        request=request,
        model=AttendanceOverTime,
        filter_class=AttendanceOverTimeFilter,
        form_class=AttendanceOverTimeExportForm,
        file_name="Attendance_Account",
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
@permission_required("attendance.delete_attendanceoverTime")
@require_http_methods(["POST"])
def attendance_overtime_delete(request, obj_id):
    """
    This method is used to delete attendance overtime
    args:
        obj_id : attendance overtime id
    """
    previous_data = request.GET.urlencode()
    hx_target = request.META.get("HTTP_HX_TARGET", None)
    try:
        attendance = AttendanceOverTime.objects.get(id=obj_id)
        attendance.delete()
        if hx_target == "ot-table":
            messages.success(request, _("Hour account deleted."))
    except (AttendanceOverTime.DoesNotExist, OverflowError, ValueError):
        if hx_target == "ot-table":
            messages.error(request, _("Hour account not found"))
    except ProtectedError:
        if hx_target == "ot-table":
            messages.error(request, _("You cannot delete this hour account"))
    if hx_target and hx_target == "ot-table":
        hour_account = AttendanceOverTime.objects.all()
        if hour_account.exists():
            return redirect(f"/attendance/attendance-overtime-search?{previous_data}")
        else:
            return HttpResponse("<script>window.location.reload()</script>")
    elif hx_target:
        return HttpResponse()


@login_required
@permission_required("attendance.delete_attendanceovertime")
def attendance_account_bulk_delete(request):
    """
    This method is used to bulk delete for Payslip
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for id in ids:
        try:
            hour_account = AttendanceOverTime.objects.get(id=id)
            hour_account.delete()
            messages.success(
                request,
                _("{employee} hour account deleted.").format(
                    employee=hour_account.employee_id
                ),
            )
        except AttendanceOverTime.DoesNotExist:
            messages.error(request, _("Hour account not found."))
        except ProtectedError:
            messages.error(
                request,
                _("You cannot delete {hour_account}").format(hour_account=hour_account),
            )
    return JsonResponse({"message": "Success"})


@login_required
def attendance_activity_view(request):
    """
    This method will render a template to view all attendance activities
    """
    previous_data = request.GET.urlencode()
    filter_obj = AttendanceActivityFilter(request.GET)
    attendance_activities = filter_obj.qs
    self_attendance_activities = attendance_activities.filter(
        employee_id__employee_user_id=request.user
    )
    attendance_activities = filtersubordinates(
        request, filter_obj.qs, "attendance.view_attendanceovertime"
    )
    attendance_activities = attendance_activities | self_attendance_activities
    attendance_activities = attendance_activities.distinct()
    attendance_activities = attendance_activities.order_by("-pk")
    activity_ids = json.dumps(
        [instance.id for instance in paginator_qry(attendance_activities, None)]
    )
    if attendance_activities.exists():
        template = "attendance/attendance_activity/attendance_activity_view.html"
    else:
        template = "attendance/attendance_activity/activity_empty.html"
    return render(
        request,
        template,
        {
            "data": paginator_qry(attendance_activities, request.GET.get("page")),
            "pd": previous_data,
            "f": filter_obj,
            "gp_fields": AttendanceActivityReGroup.fields,
            "activity_ids": activity_ids,
        },
    )


@login_required
def activity_single_view(request, obj_id):
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()
    activity = AttendanceActivity.objects.filter(id=obj_id).first()

    instance_ids_json = request.GET["instances_ids"]
    instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
    previous_instance, next_instance = closest_numbers(instance_ids, obj_id)
    context = {
        "pd": previous_data,
        "activity": activity,
        "previous_instance": previous_instance,
        "next_instance": next_instance,
        "instance_ids_json": instance_ids_json,
    }
    if activity:
        attendance = Attendance.objects.filter(
            attendance_date=activity.attendance_date
        ).first()
        context["attendance"] = attendance

    return render(
        request,
        "attendance/attendance_activity/single_attendance_activity.html",
        context=context,
    )


@login_required
@permission_required("attendance.delete_attendanceactivity")
@require_http_methods(["POST", "DELETE"])
def attendance_activity_delete(request, obj_id):
    """
    This method is used to delete attendance activity
    args:
        obj_id : attendance activity id
    """
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()
    try:
        AttendanceActivity.objects.get(id=obj_id).delete()
        messages.success(request, _("Attendance activity deleted"))
    except AttendanceActivity.DoesNotExist:
        messages.error(request, _("Attendance activity Does not exists.."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this activity"))
    if not request.GET.get("instances_ids"):
        return redirect(f"/attendance/attendance-activity-search?{previous_data}")
    else:
        instances_ids = request.GET.get("instances_ids")
        instances_list = json.loads(instances_ids)
        if obj_id in instances_list:
            instances_list.remove(obj_id)
        previous_instance, next_instance = closest_numbers(
            json.loads(instances_ids), obj_id
        )
        return redirect(
            f"/attendance/attendance-activity-single-view/{next_instance}/?{previous_data}&instances_ids={instances_list}"
        )


@login_required
@permission_required("attendance.delete_attendanceactivity")
@require_http_methods(["POST"])
def attendance_activity_bulk_delete(request):
    """
    Deletes a bulk of AttendanceActivity records based on a list of IDs.
    """
    try:
        ids_json = request.POST.get("ids", "[]")

        try:
            ids = json.loads(ids_json)
        except json.JSONDecodeError:
            messages.error(request, _("Invalid list of IDs provided."))
            return HttpResponse("<script>$('.filterButton')[0].click()</script>")

        try:
            ids = [int(i) for i in ids]
        except (ValueError, TypeError):
            messages.error(request, _("Invalid list of IDs provided."))
            return HttpResponse("<script>$('.filterButton')[0].click()</script>")

        if not ids:
            messages.warning(
                request, _("No attendance activities selected for deletion.")
            )
            return HttpResponse("<script>$('.filterButton')[0].click()</script>")

        # Perform the delete operation in a transaction
        with transaction.atomic():
            activities = AttendanceActivity.objects.filter(id__in=ids)
            count = activities.count()
            activities.delete()

        if count > 0:
            messages.success(
                request,
                _("{count} attendance activities deleted successfully.").format(
                    count=count
                ),
            )
        else:
            messages.info(
                request,
                _("No matching attendance activities were found to delete."),
            )

    except Exception as e:
        logger.exception("Error during bulk delete of attendance activities")
        messages.error(
            request,
            _("Failed to delete attendance activities: {error}").format(error=str(e)),
        )

    return HttpResponse("<script>$('.filterButton')[0].click()</script>")


def process_activity_dicts(activity_dicts):
    from attendance.views.clock_in_out import clock_in, clock_out

    if not activity_dicts:
        return []

    sorted_activity_dicts = sort_activity_dicts(activity_dicts)
    error_dicts = []  # List to store dictionaries with errors

    for activity in sorted_activity_dicts:
        badge_id = activity.get("Badge ID")
        if not badge_id:
            activity["Error 1"] = "Please add the Badge ID column in the Excel sheet."
            error_dicts.append(activity)
            continue

        employee = Employee.objects.filter(badge_id=badge_id).first()
        if not employee:
            activity["Error 2"] = "Invalid Badge ID"
            error_dicts.append(activity)
            continue

        check_in_date = parse_date(activity["In Date"], "Error 4", activity)
        check_out_date = parse_date(activity["Out Date"], "Error 5", activity)
        check_in_time = (
            parse_time(activity["Check In"])
            if not pd.isna(activity["Check In"])
            else None
        )
        check_out_time = (
            parse_time(activity["Check Out"])
            if not pd.isna(activity["Check Out"])
            else None
        )

        if any(key.startswith("Error") for key in activity.keys()):
            error_dicts.append(activity)
            continue

        if check_in_time:
            try:
                clock_in(
                    Request(
                        user=employee.employee_user_id,
                        date=check_in_date,
                        time=check_in_time,
                        datetime=django_timezone.make_aware(
                            datetime.combine(check_in_date, check_in_time)
                        ),
                    )
                )
            except Exception as e:
                activity["Error 6"] = f"Got an error in import clock in {e}"
                error_dicts.append(activity)

        if check_out_time and check_out_date:
            try:
                clock_out(
                    Request(
                        user=employee.employee_user_id,
                        date=check_out_date,
                        time=check_out_time,
                        datetime=django_timezone.make_aware(
                            datetime.combine(check_out_date, check_out_time)
                        ),
                    )
                )
            except Exception as e:
                activity["Error 7"] = f"Got an error in import clock out {e}"
                error_dicts.append(activity)

    return error_dicts


def handle_activity_import_error(error_data):

    # Directly create the DataFrame from the list of dictionaries
    data_frame = pd.DataFrame(error_data)

    # Create an HTTP response with an Excel attachment
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="ImportError.xlsx"'
    data_frame.to_excel(response, index=False)

    def get_activity_error_sheet(request):
        remove_dynamic_url(path_info)
        return response

    from attendance.urls import path, urlpatterns

    # Create a unique path for the error file download
    path_info = f"activity-error-sheet-{uuid.uuid4()}"
    urlpatterns.append(path(path_info, get_activity_error_sheet, name=path_info))
    DYNAMIC_URL_PATTERNS.append(path_info)

    # Return the path information
    path_info = f"attendance/{path_info}"
    return path_info


@login_required
@permission_required("attendance.add_attendanceactivity")
def attendance_activity_import(request):
    if request.method == "POST":
        file = request.FILES["activity_import"]
        data_frame = pd.read_excel(file)
        activity_dicts = data_frame.to_dict("records")
        if activity_dicts:
            import_error_dicts = process_activity_dicts(activity_dicts)
            path_info = handle_activity_import_error(import_error_dicts)
            created_activity_count = len(activity_dicts) - len(import_error_dicts)
            context = {
                "created_count": created_activity_count,
                "error_count": len(import_error_dicts),
                "model": _("Attendance Activity"),
                "path_info": path_info,
            }
            html = render_to_string("import_popup.html", context)
            messages.success(request, _("Attendance activity imported successfully"))
            return HttpResponse(html)
    return render(request, "attendance/attendance_activity/import_activity.html")


@login_required
@permission_required("attendance.add_attendanceactivity")
def attendance_activity_import_excel(request):
    if request.method == "GET":
        data_frame = pd.DataFrame(
            columns=[
                "Badge ID",
                "Employee",
                "Attendance Date",
                "In Date",
                "Check In",
                "Check Out",
                "Out Date",
            ]
        )
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="activity_excel.xlsx"'
        data_frame.to_excel(response, index=False)
        return response


@login_required
@permission_required("attendance.change_attendanceactivity")
def attendance_activity_export(request):
    if request.META.get("HTTP_HX_REQUEST") == "true":
        export_form = AttendanceActivityExportForm()
        context = {
            "export_form": export_form,
            "export": AttendanceActivityFilter(
                queryset=AttendanceActivity.objects.all()
            ),
        }
        return render(
            request,
            "attendance/attendance_activity/export_filter.html",
            context=context,
        )
    return export_data(
        request=request,
        model=AttendanceActivity,
        filter_class=AttendanceActivityFilter,
        form_class=AttendanceActivityExportForm,
        file_name="Attendance_activity",
    )


@login_required
def on_time_view(request):
    """
    This method render template to view all on come early out entries
    """
    total_attendances = AttendanceFilters(request.GET).qs
    ids_to_exclude = AttendanceLateComeEarlyOut.objects.filter(
        attendance_id__id__in=[attendance.id for attendance in total_attendances],
        type="late_come",
    ).values_list("attendance_id__id", flat=True)
    # Exclude attendances with related objects in AttendanceLateComeEarlyOut
    total_attendances = total_attendances.exclude(id__in=ids_to_exclude)
    context = {
        "attendances": total_attendances,
    }
    return render(
        request, "attendance/attendance/attendance_on_time.html", context=context
    )


@login_required
@install_required
def late_come_early_out_view(request):
    """
    This method render template to view all late come early out entries
    """
    filter_obj = LateComeEarlyOutFilter(request.GET)
    if filter_obj.qs.exists():
        template = "attendance/late_come_early_out/reports.html"
    else:
        template = "attendance/late_come_early_out/reports_empty.html"
    self_reports = filter_obj.qs.filter(employee_id__employee_user_id=request.user)
    reports = filtersubordinates(
        request, filter_obj.qs, "attendance.view_attendancelatecomeearlyout"
    )

    reports = reports | self_reports
    reports = reports.distinct()
    late_in_early_out_ids = json.dumps(
        [instance.id for instance in paginator_qry(reports, None)]
    )
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceLateComeEarlyOut, data_dict)
    return render(
        request,
        template,
        {
            "data": paginator_qry(reports, request.GET.get("page")),
            "f": filter_obj,
            "gp_fields": LateComeEarlyOutReGroup.fields,
            "filter_dict": data_dict,
            "late_in_early_out_ids": late_in_early_out_ids,
        },
    )


@login_required
@hx_request_required
def late_in_early_out_single_view(request, obj_id):
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()
    late_in_early_out = AttendanceLateComeEarlyOut.objects.filter(id=obj_id).first()
    instance_ids_json = request.GET["instances_ids"]
    instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
    previous_instance, next_instance = closest_numbers(instance_ids, obj_id)
    context = {
        "late_in_early_out": late_in_early_out,
        "previous_instance": previous_instance,
        "next_instance": next_instance,
        "instance_ids_json": instance_ids_json,
        "pd": previous_data,
    }
    return render(
        request, "attendance/late_come_early_out/single_report.html", context=context
    )


@login_required
@permission_required("attendance.delete_attendancelatecomeearlyout")
@hx_request_required
@require_http_methods(["POST"])
def late_come_early_out_delete(request, obj_id):
    """
    This method is used to delete the late come early out instance
    args:
        obj_id : late come early out instance id
    """
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()
    try:
        AttendanceLateComeEarlyOut.objects.get(id=obj_id).delete()
        messages.success(request, _("Late-in early-out deleted"))
    except AttendanceLateComeEarlyOut.DoesNotExist:
        messages.error(request, _("Late-in early-out does not exists.."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this Late-in early-out"))
    if not request.GET.get("instances_ids"):
        return redirect(f"/attendance/late-come-early-out-search?{previous_data}")
    else:
        instances_ids = request.GET.get("instances_ids")
        instances_list = json.loads(instances_ids)
        if obj_id in instances_list:
            instances_list.remove(obj_id)
        previous_instance, next_instance = closest_numbers(
            json.loads(instances_ids), obj_id
        )
        return redirect(
            f"/attendance/late-in-early-out-single-view/{next_instance}/?{previous_data}&instances_ids={instances_list}"
        )


@login_required
@permission_required("attendance.delete_attendancelatecomeearlyout")
@require_http_methods(["POST"])
def late_come_early_out_bulk_delete(request):
    """
    This method is used to delete bulk of attendances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for attendance_id in ids:
        try:
            late_come = AttendanceLateComeEarlyOut.objects.get(id=attendance_id)
            late_come.delete()
            messages.success(
                request,
                _("{employee} Late-in early-out deleted.").format(
                    employee=late_come.employee_id
                ),
            )
        except (AttendanceLateComeEarlyOut.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Attendance not found."))
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("attendance.change_attendancelatecomeearlyout")
def late_come_early_out_export(request):
    """
    Export late come early out data to an Excel file.
    This view function takes a GET request and exports attendance late come early out data into an Excel file.
    The exported Excel file will include the selected fields from the AttendanceLateComeEarlyOut model.
    """
    if request.META.get("HTTP_HX_REQUEST") == "true":
        context = {
            "export": LateComeEarlyOutFilter(
                queryset=AttendanceLateComeEarlyOut.objects.all()
            ),
            "export_form": LateComeEarlyOutExportForm(),
        }

        return render(
            request,
            "attendance/late_come_early_out/export_filter.html",
            context=context,
        )
    return export_data(
        request=request,
        model=AttendanceLateComeEarlyOut,
        filter_class=LateComeEarlyOutFilter,
        form_class=LateComeEarlyOutExportForm,
        file_name="Late_come_",
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
    except AttendanceValidationCondition.DoesNotExist:
        messages.error(request, _("validation condition Does not exists.."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this validation condition."))
    return redirect("/attendance/validation-condition-view")


@login_required
@require_http_methods(["POST"])
@manager_can_enter("attendance.change_attendance")
def validate_bulk_attendance(request):
    """
    This method is used to validate a bulk of attendances.
    """
    ids = json.loads(request.POST["ids"])
    validate_req_count = 0
    success_messages = []
    error_messages = []

    for obj_id in ids:
        try:
            attendance = Attendance.objects.get(id=obj_id)

            if attendance.is_validate_request:
                error_messages.append(
                    _(
                        "Pending attendance update request for {}'s attendance on {}!"
                    ).format(attendance.employee_id, attendance.attendance_date)
                )
                continue

            attendance.attendance_validated = True
            attendance.save()
            validate_req_count += 1

            # Send notification
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Your attendance for the date {attendance.attendance_date} is validated",
                verb_ar=f"تم التحقق من حضورك في تاريخ {attendance.attendance_date}",
                verb_de=f"Ihre Anwesenheit für das Datum {attendance.attendance_date} wurde bestätigt",
                verb_es=f"Se ha validado su asistencia para la fecha {attendance.attendance_date}",
                verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée",
                redirect=reverse("view-my-attendance") + f"?id={attendance.id}",
                icon="checkmark",
            )

        except Attendance.DoesNotExist:
            error_messages.append(_("Attendance not found"))
        except (OverflowError, ValueError):
            error_messages.append(_("Invalid attendance ID"))

    # Handle messages
    if validate_req_count > 0:
        messages.success(
            request, _("{} Attendances validated.").format(validate_req_count)
        )
    for msg in success_messages + error_messages:
        if "Pending" in msg:
            messages.info(request, msg)
        else:
            messages.error(request, msg)

    return JsonResponse({"message": "success"})


@login_required
@manager_can_enter("attendance.change_attendance")
def validate_this_attendance(request, obj_id):
    """
    This method is used to validate attendance
    args:
        id  : attendance id
    """
    try:
        attendance = Attendance.objects.get(id=obj_id)
        attendance.attendance_validated = True
        attendance.save()
        urlencode = request.GET.urlencode()
        modified_url = f"/attendance/attendance-view/?{urlencode}"
        messages.success(
            request,
            (
                f"{attendance.employee_id} {attendance.attendance_date.strftime('%d %b %Y') }"
                + " "
                + _("Attendance validated.")
            ),
        )
        notify.send(
            request.user.employee_get,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your attendance for the date {attendance.attendance_date} is validated",
            verb_ar=f"تم تحقيق حضورك في تاريخ {attendance.attendance_date}",
            verb_de=f"Deine Anwesenheit für das Datum {attendance.attendance_date} ist bestätigt.",
            verb_es=f"Se valida tu asistencia para la fecha {attendance.attendance_date}.",
            verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée.",
            redirect=reverse("view-my-attendance") + f"?id={attendance.id}",
            icon="checkmark",
        )
    except (Attendance.DoesNotExist, ValueError):
        messages.error(request, _("Attendance not found"))

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


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
                verb_ar=f"{attendance.employee_id} طلب إعادة\
                      التحقق من حضور تاريخ {attendance.attendance_date}",
                verb_de=f"{attendance.employee_id} beantragte eine Neubewertung der \
                    Teilnahme am {attendance.attendance_date}",
                verb_es=f"{attendance.employee_id} solicitó la validación nuevamente \
                    para la asistencia del {attendance.attendance_date}",
                verb_fr=f"{attendance.employee_id} a demandé une revalidation pour la \
                    présence du {attendance.attendance_date}",
                redirect=reverse("view-my-attendance") + f"?id={attendance.id}",
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
    try:
        attendance = Attendance.objects.get(id=obj_id)
        attendance.attendance_overtime_approve = True
        attendance.save()
        urlencode = request.GET.urlencode()
        modified_url = f"/attendance/attendance-view/?{urlencode}"
        messages.success(
            request,
            f"{attendance.employee_id}'s {attendance.attendance_date.strftime('%d %b %Y')} overtime approved",
        )
        with contextlib.suppress(Exception):
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Your {attendance.attendance_date}'s attendance \
                    overtime approved.",
                verb_ar=f"تمت الموافقة على إضافة ساعات العمل الإضافية لتاريخ \
                    {attendance.attendance_date}.",
                verb_de=f"Die Überstunden für den {attendance.attendance_date}\
                      wurden genehmigt.",
                verb_es=f"Se ha aprobado el tiempo extra de asistencia para el \
                    {attendance.attendance_date}.",
                verb_fr=f"Les heures supplémentaires pour la date\
                      {attendance.attendance_date} ont été approuvées.",
                redirect=reverse("attendance-overtime-view") + f"?id={attendance.id}",
                icon="checkmark",
            )
    except (Attendance.DoesNotExist, OverflowError):
        messages.error(request, _("Attendance not found"))
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
        try:
            attendance = Attendance.objects.get(id=attendance_id)
            attendance.attendance_overtime_approve = True
            attendance.save()
            messages.success(request, _("Overtime approved"))
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Overtime approved for\
                      {attendance.attendance_date}'s attendance",
                verb_ar=f"تمت الموافقة على العمل الإضافي لحضور تاريخ \
                    {attendance.attendance_date}",
                verb_de=f"Überstunden für die Anwesenheit am \
                    {attendance.attendance_date} genehmigt",
                verb_es=f"Horas extra aprobadas para la asistencia del \
                    {attendance.attendance_date}",
                verb_fr=f"Heures supplémentaires approuvées pour la présence du \
                    {attendance.attendance_date}",
                redirect=reverse("attendance-overtime-view") + f"?id={attendance.id}",
                icon="checkmark",
            )
        except (Attendance.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Attendance not found"))
    return JsonResponse({"message": "Success"})


@login_required
# @manager_can_enter("attendance.change_attendance")
def attendance_add_to_batch(request):
    """
    This method is used to add attendance to a batch
    """
    batches = BatchAttendance.objects.all()
    ids = request.GET.getlist("ids")
    if request.method == "POST":
        ids = request.GET["ids"]
        # Remove brackets and quotes, then split and convert to integers
        int_ids = [int(x.strip().strip("'")) for x in ids.strip("[]").split(",")]
        batch_id = request.POST.get("batch_attendance_id")
        if batch_id:
            batch = BatchAttendance.objects.filter(id=batch_id).first()
            for id in int_ids:
                try:
                    attendance_req = Attendance.objects.filter(id=id).first()
                    attendance_req.batch_attendance_id = batch
                    attendance_req.save()
                except Exception as e:
                    logger.error(e)
                    messages.error(request, _("Something went wrong."))
                    return HttpResponse("<script>window.location.reload()</script>")
            messages.success(request, _(f"Attendances added to {batch}."))
            return HttpResponse("<script>window.location.reload()</script>")
        else:
            messages.error(request, _("Something went wrong."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "attendance/attendance/attendance_add_batch.html",
        {"batches": batches, "ids": ids},
    )


@login_required
@hx_request_required
def update_fields_based_shift(request):
    shift_id = request.GET.get("shift_id")
    hx_target = request.META.get("HTTP_HX_TARGET")

    employee_ids = (
        request.GET.get("employee_id")
        if hx_target == "attendanceUpdateForm" or hx_target == "attendanceRequestDiv"
        else request.GET.getlist("employee_id")
    )
    employee_queryset = (
        (
            Employee.objects.get(id=employee_ids)
            if hx_target == "attendanceUpdateForm"
            or hx_target == "attendanceRequestDiv"
            else Employee.objects.filter(id__in=employee_ids)
        )
        if employee_ids
        else None
    )
    attendance_date_str = request.GET.get("attendance_date")

    attendance_date = (
        datetime.strptime(attendance_date_str, "%Y-%m-%d").date()
        if attendance_date_str
        else datetime.today().date()
    )
    day = attendance_date.strftime("%A").lower()

    schedule_today = (
        EmployeeShiftSchedule.objects.filter(shift_id=shift_id, day__day=day).first()
        if shift_id
        else None
    )

    shift_start_time = schedule_today.start_time if schedule_today else ""
    shift_end_time = schedule_today.end_time if schedule_today else ""
    minimum_hour = schedule_today.minimum_working_hour if schedule_today else "00:00"

    if schedule_today and shift_end_time < shift_start_time:
        attendance_clock_out_date = (attendance_date + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
    else:
        attendance_clock_out_date = attendance_date.strftime("%Y-%m-%d")

    if attendance_date == datetime.today().date():
        shift_end_time = datetime.now().time()
        worked_hour = "00:00"
    else:
        worked_hour = minimum_hour

    minimum_hour = attendance_day_checking(str(attendance_date), minimum_hour)

    initial_data = {
        "work_type_id": WorkType.find(request.GET.get("work_type_id")),
        "shift_id": shift_id,
        "employee_id": employee_queryset,
        "minimum_hour": minimum_hour,
        "attendance_date": attendance_date.strftime("%Y-%m-%d"),
        "attendance_clock_in": (
            shift_start_time.strftime("%H:%M") if shift_start_time else ""
        ),
        "attendance_clock_out": (
            shift_end_time.strftime("%H:%M") if shift_end_time else ""
        ),
        "attendance_worked_hour": worked_hour,
        "attendance_clock_in_date": attendance_date.strftime("%Y-%m-%d"),
        "attendance_clock_out_date": attendance_clock_out_date,
    }
    form = (
        AttendanceUpdateForm(initial=initial_data)
        if hx_target == "attendanceUpdateForm"
        else (
            NewRequestForm(initial=initial_data)
            if hx_target == "attendanceRequestDiv"
            else AttendanceForm(initial=initial_data)
        )
    )
    return render(
        request,
        "attendance/attendance/update_hx_form.html",
        {"request": request, "form": form},
    )


@login_required
@hx_request_required
def update_worked_hour_field(request):
    """
    Update the worked hour field based on clock-in and clock-out times.

    This view function calculates the total worked hours for an employee
    by parsing the clock-in and clock-out dates and times from the request
    parameters. It computes the duration between the two times and formats
    the result as a string in the "HH:MM" format. The computed worked hours
    are then initialized in an AttendanceForm, which is rendered in the
    specified HTML template.
    """
    clock_in = parse_datetime(
        (
            now().strftime("%Y-%m-%d")
            if request.GET.get("create_bulk")
            else request.GET.get("attendance_clock_in_date")
        ),
        request.GET.get("attendance_clock_in"),
    )
    clock_out = parse_datetime(
        (
            now().strftime("%Y-%m-%d")
            if request.GET.get("create_bulk")
            else request.GET.get("attendance_clock_out_date")
        ),
        request.GET.get("attendance_clock_out"),
    )

    total_seconds = (
        (clock_out - clock_in).total_seconds() if clock_in and clock_out else -1
    )
    hours, minutes = divmod(max(total_seconds, 0), 3600)
    worked_hours_str = f"{int(hours):02}:{int(minutes // 60):02}"

    form = AttendanceForm(initial={"attendance_worked_hour": worked_hours_str})
    return render(
        request,
        "attendance/attendance/update_hx_form.html",
        {"request": request, "form": form},
    )


@login_required
def form_date_checking(request):
    attendance_date_str = request.POST["attendance_date"]
    minimum_hour = "00:00"
    # Converting to date type.
    attendance_date = datetime.strptime(attendance_date_str, "%Y-%m-%d").date()

    if request.POST["shift_id"]:
        shift_id = request.POST["shift_id"]
        day = attendance_date.strftime("%A").lower()
        schedule_today = EmployeeShiftSchedule.objects.filter(
            shift_id__id=shift_id, day__day=day
        ).first()

        # Checking the Shift is present in the selected attendance day.
        if schedule_today is not None:
            minimum_hour = schedule_today.minimum_working_hour

    attendance_date = str(attendance_date)
    minimum_hour = attendance_day_checking(attendance_date, minimum_hour)

    return JsonResponse(
        {
            "minimum_hour": minimum_hour,
        }
    )


@login_required
def user_request_one_view(request, id):
    """
    function used to view one user attendance request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return one user attendance request view template
    """
    attendance_request = Attendance.objects.get(id=id)

    at_work_seconds = attendance_request.at_work_second
    hours_at_work = at_work_seconds // 3600
    minutes_at_work = (at_work_seconds % 3600) // 60
    at_work = "{:02}:{:02}".format(hours_at_work, minutes_at_work)

    over_time_seconds = attendance_request.overtime_second
    hours_over_time = over_time_seconds // 3600
    minutes_over_time = (over_time_seconds % 3600) // 60
    over_time = "{:02}:{:02}".format(hours_over_time, minutes_over_time)
    instance_ids_json = request.GET["instances_ids"]
    instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
    previous_instance, next_instance = closest_numbers(instance_ids, id)
    return render(
        request,
        "attendance/attendance/attendance_request_one.html",
        {
            "attendance_request": attendance_request,
            "at_work": at_work,
            "over_time": over_time,
            "previous_instance": previous_instance,
            "next_instance": next_instance,
            "instance_ids_json": instance_ids_json,
            "dashboard": request.GET.get("dashboard"),
        },
    )


@login_required
@hx_request_required
def get_attendance_activities(request, obj_id):
    attendance = Attendance.find(obj_id)
    return render(
        request,
        "attendance/attendance/attendance_activites_view.html",
        context={"attendance": attendance},
    )


@login_required
def hour_attendance_select(request):
    page_number = request.GET.get("page")
    context = {}

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendanceovertime"):
            employees = AttendanceOverTime.objects.all()
        else:
            employees = AttendanceOverTime.objects.filter(
                employee_id__employee_user_id=request.user
            ) | AttendanceOverTime.objects.filter(
                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
            )

        employee_ids = [str(emp.id) for emp in employees]
        total_count = employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def hour_attendance_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendanceovertime"):
            employee_filter = AttendanceOverTimeFilter(
                filters, queryset=AttendanceOverTime.objects.all()
            )
        else:
            employee_filter = AttendanceOverTimeFilter(
                filters,
                queryset=AttendanceOverTime.objects.filter(
                    employee_id__employee_user_id=request.user
                )
                | AttendanceOverTime.objects.filter(
                    employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                ),
            )

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
def activity_attendance_select(request):
    page_number = request.GET.get("page")

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendanceovertime"):
            employees = AttendanceActivity.objects.all()
        else:
            employees = AttendanceActivity.objects.filter(
                employee_id__employee_user_id=request.user
            ) | AttendanceActivity.objects.filter(
                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
            )

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def activity_attendance_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendanceovertime"):
            employee_filter = AttendanceActivityFilter(
                filters, queryset=AttendanceActivity.objects.all()
            )
        else:
            employee_filter = AttendanceActivityFilter(
                filters,
                queryset=AttendanceActivity.objects.filter(
                    employee_id__employee_user_id=request.user
                )
                | AttendanceActivity.objects.filter(
                    employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                ),
            )

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
def latecome_attendance_select(request):
    page_number = request.GET.get("page")

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendancelatecomeearlyout"):
            employees = AttendanceLateComeEarlyOut.objects.all()
        else:
            employees = AttendanceLateComeEarlyOut.objects.filter(
                employee_id__employee_user_id=request.user
            ) | AttendanceLateComeEarlyOut.objects.filter(
                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
            )

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def latecome_attendance_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        if request.user.has_perm("attendance.view_attendancelatecomeearlyout"):
            employee_filter = LateComeEarlyOutFilter(
                filters, queryset=AttendanceLateComeEarlyOut.objects.all()
            )
        else:
            employee_filter = LateComeEarlyOutFilter(
                filters,
                queryset=AttendanceLateComeEarlyOut.objects.filter(
                    employee_id__employee_user_id=request.user
                )
                | AttendanceLateComeEarlyOut.objects.filter(
                    employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                ),
            )

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
@hx_request_required
@permission_required("attendance.add_gracetime")
def create_grace_time(request):
    """
    function used to create grace time .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return grace time form template
    """
    is_default = eval_validate(request.GET.get("default"))
    form = GraceTimeForm(initial={"is_default": is_default})
    if request.method == "POST":
        form = GraceTimeForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            gracetime = form.save()
            shifts = cleaned_data.get("shifts")
            for shift in shifts:
                shift.grace_time_id = gracetime
                shift.save()
            messages.success(request, _("Grace time created successfully."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "attendance/grace_time/grace_time_form.html",
        {"form": form, "is_default": is_default},
    )


@login_required
@hx_request_required
@permission_required("base.change_employeeshift")
def assign_shift(request, grace_id):
    gracetime = GraceTime.objects.filter(id=grace_id).first() if grace_id else None
    if gracetime:
        form = GraceTimeAssignForm()
        if request.method == "POST":
            form = GraceTimeAssignForm(request.POST)
            if form.is_valid():
                cleaned_data = form.cleaned_data
                shifts = cleaned_data.get("shifts")
                for shift in shifts:
                    shift.grace_time_id = gracetime
                    shift.save()
                messages.success(request, _("Grace time added to shifts successfully."))
                return HttpResponse("<script>window.location.reload()</script>")
        return render(
            request,
            "attendance/grace_time/assign_shift.html",
            {"form": form, "grace_time": gracetime},
        )


@login_required
@hx_request_required
@permission_required("attendance.change_gracetime")
def update_grace_time(request, grace_id):
    """
    function used to create grace time .

    Parameters:
    request (HttpRequest): The HTTP request object.
    grace_id: id of grace time object
    Returns:
    GET : return grace time form template
    """
    grace_time = GraceTime.objects.get(id=grace_id)
    form = GraceTimeForm(instance=grace_time)
    if request.method == "POST":
        form = GraceTimeForm(request.POST, instance=grace_time)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            messages.success(request, _("Grace time updated successfully."))
            return HttpResponse("<script>window.location.reload()</script>")
    context = {
        "form": form,
        "grace_id": grace_id,
    }
    return render(
        request, "attendance/grace_time/grace_time_form.html", context=context
    )


@login_required
@permission_required("attendance.delete_gracetime")
def delete_grace_time(request, grace_id):
    """
    function used to delete grace time .

    Parameters:
    request (HttpRequest): The HTTP request object.
    grace_id: id of grace time object
    Returns:
    GET : return grace time form template
    """
    try:
        GraceTime.objects.get(id=grace_id).delete()
        messages.success(request, _("Grace time deleted successfully."))
    except GraceTime.DoesNotExist:
        messages.error(request, _("Grace Time Does not exists.."))
    except ProtectedError:
        messages.error(request, _("Related datas exists."))
    context = {
        "condition": AttendanceValidationCondition.objects.first(),
        "default_grace_time": GraceTime.objects.filter(is_default=True).first(),
        "grace_times": GraceTime.objects.all().exclude(is_default=True),
    }

    return render(request, "attendance/grace_time/grace_time_table.html", context)


@login_required
@permission_required("attendance.update_gracetime")
def update_isactive_gracetime(request):
    """
    ajax function to update is active field in GraceTime.
    Args:
    - isChecked: Boolean value representing the state of grace time,
    - gracetimeId: Id of GraceTime object
    """
    isChecked = request.POST.get("isChecked")
    gracetimeId = request.POST.get("gracetimeId")
    gracetime = GraceTime.objects.get(id=gracetimeId)
    if isChecked == "true":
        gracetime.is_active = True
        response = {
            "type": "success",
            "message": _("Gracetime activated successfully."),
        }
    else:
        gracetime.is_active = False
        response = {
            "type": "success",
            "message": _("Gracetime deactivated successfully."),
        }
    gracetime.save()
    return JsonResponse(response)


@login_required
@permission_required("attendance.update_gracetime")
def update_gracetime_clock_in_clock_out(request):
    """
    ajax function to update is active field in grace time.
    Args:
    - isChecked: Boolean value representing the state of grace time,
    - gracetimeId: Id of PayslipAutoGenerate object
    """
    isChecked = request.POST.get("isChecked")
    gracetimeId = request.POST.get("gracetimeId")
    update = request.POST.get("update")
    garcetime = GraceTime.objects.get(id=gracetimeId)
    if update == "clock_in":
        if isChecked == "true":
            garcetime.allowed_clock_in = True
            response = {
                "type": "success",
                "message": _("Gracetime applicable on clock-In successfully."),
            }
        else:
            garcetime.allowed_clock_in = False
            response = {
                "type": "success",
                "message": _("Gracetime unapplicable on clock-In  successfully."),
            }
    elif update == "clock_out":
        if isChecked == "true":
            garcetime.allowed_clock_out = True
            response = {
                "type": "success",
                "message": _("Gracetime applicable on clock-out successfully."),
            }
        else:
            garcetime.allowed_clock_out = False
            response = {
                "type": "success",
                "message": _("Gracetime unapplicable on clock-out successfully."),
            }
    else:
        response = {
            "type": "error",
            "message": _("Something went wrong ."),
        }
    garcetime.save()
    return JsonResponse(response)


@login_required
def create_attendancerequest_comment(request, attendance_id):
    """
    This method renders form and template to create Attendance request comments
    """
    previous_data = request.GET.urlencode()
    attendance = Attendance.objects.filter(id=attendance_id).first()
    emp = request.user.employee_get
    form = AttendanceRequestCommentForm(
        initial={"employee_id": emp.id, "request_id": attendance_id}
    )

    if request.method == "POST":
        form = AttendanceRequestCommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.request_id = attendance
            form.save()
            comments = AttendanceRequestComment.objects.filter(
                request_id=attendance_id
            ).order_by("-created_at")
            no_comments = False
            if not comments.exists():
                no_comments = True
            form = AttendanceRequestCommentForm(
                initial={"employee_id": emp.id, "request_id": attendance_id}
            )
            messages.success(request, _("Comment added successfully!"))
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=attendance.employee_id
            )
            if work_info.exists():
                if (
                    attendance.employee_id.employee_work_info.reporting_manager_id
                    is not None
                ):
                    if request.user.employee_get.id == attendance.employee_id.id:
                        rec = (
                            attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        )
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{attendance.employee_id}'s attendance request has received a comment.",
                            verb_ar=f"تلقت طلب الحضور {attendance.employee_id} تعليقًا.",
                            verb_de=f"{attendance.employee_id}s Anfrage zur Anwesenheit hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de asistencia de {attendance.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de présence de {attendance.employee_id} a reçu un commentaire.",
                            redirect=reverse("request-attendance-view")
                            + f"?id={attendance.id}",
                            icon="chatbox-ellipses",
                        )
                    elif (
                        request.user.employee_get.id
                        == attendance.employee_id.employee_work_info.reporting_manager_id.id
                    ):
                        rec = attendance.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your attendance request has received a comment.",
                            verb_ar="تلقى طلب الحضور الخاص بك تعليقًا.",
                            verb_de="Ihr Antrag auf Anwesenheit hat einen Kommentar erhalten.",
                            verb_es="Tu solicitud de asistencia ha recibido un comentario.",
                            verb_fr="Votre demande de présence a reçu un commentaire.",
                            redirect=reverse("request-attendance-view")
                            + f"?id={attendance.id}",
                            icon="chatbox-ellipses",
                        )
                    else:
                        rec = [
                            attendance.employee_id.employee_user_id,
                            attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{attendance.employee_id}'s attendance request has received a comment.",
                            verb_ar=f"تلقت طلب الحضور {attendance.employee_id} تعليقًا.",
                            verb_de=f"{attendance.employee_id}s Anfrage zur Anwesenheit hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de asistencia de {attendance.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de présence de {attendance.employee_id} a reçu un commentaire.",
                            redirect=reverse("request-attendance-view")
                            + f"?id={attendance.id}",
                            icon="chatbox-ellipses",
                        )
                else:
                    rec = attendance.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your attendance request has received a comment.",
                        verb_ar="تلقى طلب الحضور الخاص بك تعليقًا.",
                        verb_de="Ihr Antrag auf Anwesenheit hat einen Kommentar erhalten.",
                        verb_es="Tu solicitud de asistencia ha recibido un comentario.",
                        verb_fr="Votre demande de présence a reçu un commentaire.",
                        redirect=reverse("request-attendance-view")
                        + f"?id={attendance.id}",
                        icon="chatbox-ellipses",
                    )
            return render(
                request,
                "requests/attendance/attendance_comment.html",
                {
                    "comments": comments,
                    "no_comments": no_comments,
                    "request_id": attendance_id,
                },
            )
    return render(
        request,
        "requests/attendance/attendance_comment.html",
        {
            "form": form,
            "request_id": attendance_id,
            "pd": previous_data,
        },
    )


@login_required
def view_attendancerequest_comment(request, attendance_id):
    """
    This method is used to show Attendance request comments
    """
    comments = AttendanceRequestComment.objects.filter(
        request_id=attendance_id
    ).order_by("-created_at")
    no_comments = False
    if not comments.exists():
        no_comments = True

    if request.FILES:
        files = request.FILES.getlist("files")
        comment_id = request.GET["comment_id"]
        comment = AttendanceRequestComment.objects.get(id=comment_id)
        attachments = []
        for file in files:
            file_instance = AttendanceRequestFile()
            file_instance.file = file
            file_instance.save()
            attachments.append(file_instance)
        comment.files.add(*attachments)

    return render(
        request,
        "requests/attendance/attendance_comment.html",
        {"comments": comments, "no_comments": no_comments, "request_id": attendance_id},
    )


@login_required
def delete_attendancerequest_comment(request, comment_id):
    """
    This method is used to delete Attendance request comments
    """
    script = ""
    comment = AttendanceRequestComment.objects.get(id=comment_id)
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return HttpResponse(script)


@login_required
def delete_comment_file(request):
    """
    Used to delete attachment
    """
    script = ""
    ids = request.GET.getlist("ids")
    AttendanceRequestFile.objects.filter(id__in=ids).delete()
    messages.success(request, _("File deleted successfully"))
    return HttpResponse(script)


@login_required
def work_records(request):
    today = date.today()
    previous_data = request.GET.urlencode()
    context = {
        "current_date": today,
        "pd": previous_data,
    }
    return render(
        request, "attendance/work_record/work_record_view.html", context=context
    )


@login_required
@hx_request_required
def work_records_change_month(request):
    previous_data = request.GET.urlencode()
    employee_filter_form = EmployeeFilter(request.GET or None)

    employees = filtersubordinatesemployeemodel(
        request, employee_filter_form.qs, "attendance.view_attendance"
    )

    month_str = request.GET.get("month", f"{date.today().year}-{date.today().month}")
    try:
        year, month = map(int, month_str.split("-"))
    except ValueError:
        year, month = date.today().year, date.today().month

    employees = [request.user.employee_get] + list(employees)

    month_dates = [
        datetime(year, month, day).date()
        for week in calendar.monthcalendar(year, month)
        for day in week
        if day
    ]

    work_records = WorkRecords.objects.filter(
        date__in=month_dates, employee_id__in=employees
    ).select_related("employee_id", "shift_id", "attendance_id")

    work_records_dict = {(wr.employee_id.id, wr.date): wr for wr in work_records}

    data = {
        employee: [
            work_records_dict.get((employee.id, current_date))
            for current_date in month_dates
        ]
        for employee in employees
    }

    paginator = Paginator(list(data.items()), get_pagination())
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "current_month_dates_list": month_dates,
        "leave_dates": monthly_leave_days(month, year),
        "data": page,
        "pd": previous_data,
        "current_date": date.today(),
        "f": employee_filter_form,
    }

    return render(request, "attendance/work_record/work_record_list.html", context)


@login_required
@permission_required("attendance.view_workrecords")
def work_record_export(request):
    try:
        month = int(request.GET.get("month") or date.today().month)
        year = int(request.GET.get("year") or date.today().year)
    except ValueError:
        return HttpResponseBadRequest("Invalid month or year parameter.")

    employees = EmployeeFilter(request.GET).qs
    records = WorkRecords.objects.filter(date__month=month, date__year=year)
    num_days = calendar.monthrange(year, month)[1]
    all_date_objects = [date(year, month, day) for day in range(1, num_days + 1)]
    leave_dates = set(monthly_leave_days(month, year))

    record_lookup = defaultdict(lambda: "ABS")
    for record in records:
        if record.date <= date.today():
            record_key = (record.employee_id, record.date)
            record_lookup[record_key] = record.work_record_type

    date_format = request.user.employee_get.get_date_format()
    format_string = HORILLA_DATE_FORMATS.get(date_format)
    formatted_dates = [day.strftime(format_string) for day in all_date_objects]
    data_rows = []

    for employee in employees:
        row_data = {"Employee": employee}
        for day, formatted_day in zip(all_date_objects, formatted_dates):
            if not day in leave_dates and day < date.today():
                row_data[formatted_day] = record_lookup.get((employee, day), "DFT")
            else:
                data = record_lookup.get((employee, day), "")
                row_data[formatted_day] = data if data != "DFT" else ""
        data_rows.append(row_data)

    columns = ["Employee"] + formatted_dates
    df = pd.DataFrame(data_rows, columns=columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        formats = {
            "ABS": workbook.add_format(
                {"bg_color": "#808080", "font_color": "#ffffff"}
            ),
            "FDP": workbook.add_format(
                {"bg_color": "#38c338", "font_color": "#ffffff"}
            ),
            "HDP": workbook.add_format(
                {"bg_color": "#dfdf52", "font_color": "#000000"}
            ),
            "CONF": workbook.add_format(
                {"bg_color": "#ed4c4c", "font_color": "#ffffff"}
            ),
            "DFT": workbook.add_format(
                {"bg_color": "#a8b1ff", "font_color": "#ffffff"}
            ),
        }

        for row_idx, row in enumerate(df.itertuples(index=False), start=1):
            for col_idx, cell_value in enumerate(row[1:], start=1):
                if cell_value in formats:
                    worksheet.write(row_idx, col_idx, cell_value, formats[cell_value])

        for col_idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(col_idx, col_idx, max_len)

    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="work_record_export.xlsx"'
    return response


@login_required
@hx_request_required
@permission_required("attendance.add_attendancegeneralsetting")
def enable_timerunner(request):
    """
    This method is used to enable/disable the timerunner feature
    """

    time_runner = AttendanceGeneralSetting.objects.first()
    time_runner = time_runner if time_runner else AttendanceGeneralSetting()
    time_runner.time_runner = "time_runner" in request.GET.keys()
    time_runner.save()
    return HttpResponse("success")


@login_required
@permission_required("base.view_tracklatecomeearlyout")
def track_late_come_early_out(request):
    """
    Renders the form to track late arrivals and early departures in attendance.
    """
    tracking = TrackLateComeEarlyOut.objects.first()
    form = TrackLateComeEarlyOutForm(
        initial={"is_enable": tracking.is_enable} if tracking else {}
    )
    return render(
        request, "attendance/late_come_early_out/tracking.html", {"form": form}
    )


@login_required
@permission_required("base.change_tracklatecomeearlyout")
def enable_disable_tracking_late_come_early_out(request):
    """
    Enables or disables the tracking of late arrivals and early departures in attendance.
    """
    if request.method == "POST":
        enable = bool(request.POST.get("is_enable"))
        tracking, created = TrackLateComeEarlyOut.objects.get_or_create()
        tracking.is_enable = enable
        tracking.save()
        message = _("enabled") if enable else _("disabled")
        messages.success(
            request, _("Tracking late come early out {} successfully").format(message)
        )
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
def check_in_check_out_setting(request):
    """
    Check in check out setting
    """
    attendance_settings = AttendanceGeneralSetting.objects.all()
    return render(
        request,
        "attendance/settings/check_in_check_out_enable_form.html",
        {"attendance_settings": attendance_settings},
    )


@login_required
@hx_request_required
@permission_required("attendance.change_attendancegeneralsetting")
def enable_disable_check_in(request):
    """
    Enables or disables check-in check-out.
    """
    if request.method == "POST":
        is_checked = request.POST.get("isChecked")
        setting_id = request.POST.get("setting_Id")
        enable = bool(is_checked)

        updated = AttendanceGeneralSetting.objects.filter(id=setting_id).update(
            enable_check_in=enable
        )

        if updated:
            message = _("Check In/Check Out has been successfully {}.").format(
                _("enabled") if enable else _("disabled")
            )
            messages.success(request, message)
            if enable:
                return render(request, "attendance/components/in_out_component.html")

    return HttpResponse("")


@login_required
@permission_required("attendance.view_attendancevalidationcondition")
def grace_time_view(request):
    """
    This method view attendance validation conditions.
    """
    condition = AttendanceValidationCondition.objects.first()
    default_grace_time = GraceTime.objects.filter(is_default=True).first()
    grace_times = GraceTime.objects.all().exclude(is_default=True)
    return render(
        request,
        "attendance/grace_time/grace_time.html",
        {
            "condition": condition,
            "default_grace_time": default_grace_time,
            "grace_times": grace_times,
        },
    )


@login_required
@permission_required("attendance.view_attendancevalidationcondition")
def validation_condition_view(request):
    """
    This method view attendance validation conditions.
    """

    condition = AttendanceValidationCondition.objects.first()
    default_grace_time = GraceTime.objects.filter(is_default=True).first()
    return render(
        request,
        "attendance/break_point/condition.html",
        {"condition": condition, "default_grace_time": default_grace_time},
    )


@login_required
@permission_required("attendance.add_attendancevalidationcondition")
def validation_condition_create(request):
    """
    This method render a form to create attendance validation conditions,
    and create if the form is valid.
    """
    form = AttendanceValidationConditionForm()
    if request.method == "POST":
        form = AttendanceValidationConditionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance Break-point settings created."))
            form = AttendanceValidationConditionForm()
    return render(
        request,
        "attendance/break_point/condition_form.html",
        {"form": form},
    )


@login_required
@hx_request_required
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
            messages.success(request, _("Attendance Break-point settings updated."))
    return render(
        request,
        "attendance/break_point/condition_form.html",
        {"form": form, "condition": condition},
    )


@login_required
@permission_required("attendance.add_attendance")
def allowed_ips(request):
    """
    This function is used to view the allowed ips
    """
    allowed_ips = AttendanceAllowedIP.objects.first()
    return render(
        request,
        "attendance/ip_restriction/ip_restriction.html",
        {"allowed_ips": allowed_ips},
    )


@login_required
@permission_required("attendance.add_attendance")
def enable_ip_restriction(request):
    """
    This function is used to enable the allowed ips
    """
    form = AttendanceAllowedIPForm()
    if request.method == "POST":
        ip_restiction = AttendanceAllowedIP.objects.first()

        if not ip_restiction:
            ip_restiction = AttendanceAllowedIP.objects.create(is_enabled=True)
            return HttpResponse("<script>window.location.reload()</script>")

        if not ip_restiction.is_enabled:
            ip_restiction.is_enabled = True
        elif ip_restiction.is_enabled:
            ip_restiction.is_enabled = False

        ip_restiction.save()
        return HttpResponse("<script>window.location.reload()</script>")


def validate_ip_address(self, value):
    """
    This function is used to check if the provided IP is in the ipv4 or ipv6 format.

    Args:
        value: The IP address to validate
    """
    try:
        validate_ipv46_address(value)
    except ValidationError:
        raise ValidationError("Enter a valid IPv4 or IPv6 address.")
    return value


@login_required
@permission_required("attendance.add_attendance")
def create_allowed_ips(request):
    """
    This function is used to create the allowed IPs.
    """
    if request.method == "POST":
        form = AttendanceAllowedIPForm(request.POST)
        if form.is_valid():
            ip_addresses = form.cleaned_data.get("ip_addresses")
            allowed_ips = AttendanceAllowedIP.objects.first()
            if allowed_ips:
                existing_ips = set(allowed_ips.additional_data.get("allowed_ips", []))
                new_ips = set(ip_addresses)
                duplicates = new_ips.intersection(existing_ips)

                if duplicates:
                    messages.error(
                        request, f"IP addresses already exist: {', '.join(duplicates)}"
                    )

                non_duplicates = new_ips - duplicates

                if non_duplicates:
                    allowed_ips.additional_data["allowed_ips"] = list(
                        existing_ips.union(non_duplicates)
                    )
                    allowed_ips.save()
                    messages.success(request, "IP addresses saved successfully")
                else:
                    messages.info(
                        request,
                        "All provided IP addresses are already in the allowed list.",
                    )

            else:
                AttendanceAllowedIP.objects.create(
                    is_enabled=True, additional_data={"allowed_ips": ip_addresses}
                )
                messages.success(request, "IP addresses saved successfully")

            return HttpResponse("<script>window.location.reload()</script>")
    else:
        form = AttendanceAllowedIPForm()

    return render(
        request, "attendance/ip_restriction/restrict_form.html", {"form": form}
    )


@login_required
@permission_required("attendance.delete_attendance")
def delete_allowed_ips(request):
    """
    This function is used to delete the allowed ips
    """
    try:
        ids = request.GET.getlist("id")
        allowed_ips = AttendanceAllowedIP.objects.first()
        ips = allowed_ips.additional_data["allowed_ips"]
        for id in ids:
            ips.pop(eval_validate(id))

        allowed_ips.additional_data["allowed_ips"] = ips
        allowed_ips.save()

        messages.success(request, "IP address removed successfully")
    except:
        messages.error(request, "Invalid id")
    return redirect("allowed-ips")


@login_required
@permission_required("attendance.change_attendance")
def edit_allowed_ips(request):
    """
    This function is used to edit the allowed IPs.
    """
    allowed_ips = AttendanceAllowedIP.objects.first()
    if not allowed_ips:
        messages.error(request, "No allowed IPs found.")
        return redirect("allowed-ips")

    ips = allowed_ips.additional_data.get("allowed_ips", [])
    id = request.GET.get("id")

    try:
        id = int(id)
        if id < 0 or id >= len(ips):
            raise IndexError

        initial_ip = ips[id]
        form = AttendanceAllowedIPForm(initial={"ip_addresses": initial_ip})

        if request.method == "POST":
            form = AttendanceAllowedIPForm(request.POST)
            if form.is_valid():
                new_ip = form.cleaned_data["ip_addresses"][0]

                existing_ips = set(allowed_ips.additional_data.get("allowed_ips", []))

                if new_ip in existing_ips:
                    messages.error(request, "IP address already exists.")
                else:
                    existing_ips.discard(initial_ip)
                    existing_ips.add(new_ip)

                    allowed_ips.additional_data["allowed_ips"] = list(existing_ips)
                    allowed_ips.save()
                    messages.success(request, "IP address updated successfully")
                return HttpResponse("<script>window.location.reload()</script>")

    except (ValueError, IndexError):
        messages.error(request, "Invalid ID provided.")

    return render(
        request,
        "attendance/ip_restriction/restrict_form.html",
        {"form": form, "id": id},
    )
