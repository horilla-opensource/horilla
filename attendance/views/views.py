"""
views.py

This module contains the view functions for handling HTTP requests and rendering
responses in your application.

Each view function corresponds to a specific URL route and performs the necessary
actions to handle the request, process data, and generate a response.

This module is part of the recruitment project and is intended to
provide the main entry points for interacting with the application's functionality.
"""

import calendar
import json
import contextlib
from datetime import datetime, timedelta
from datetime import date
import pandas as pd
from urllib.parse import parse_qs
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as __
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from employee.models import Employee
from horilla.decorators import (
    permission_required,
    login_required,
    hx_request_required,
    manager_can_enter,
)
from base.methods import closest_numbers, export_data, get_pagination
from base.methods import get_key_instances
from base.models import EmployeeShiftSchedule
from base.methods import filtersubordinates, choosesubordinates
from leave.models import WEEK_DAYS, CompanyLeave, Holiday
from notifications.signals import notify
from attendance.views.handle_attendance_errors import handle_attendance_errors
from attendance.views.process_attendance_data import process_attendance_data
from attendance.filters import (
    AttendanceFilters,
    AttendanceOverTimeFilter,
    LateComeEarlyOutFilter,
    AttendanceActivityFilter,
)
from attendance.forms import (
    AttendanceActivityExportForm,
    AttendanceForm,
    AttendanceOverTimeExportForm,
    AttendanceOverTimeForm,
    AttendanceValidationConditionForm,
    AttendanceUpdateForm,
    AttendanceExportForm,
    AttendanceRequestCommentForm,
    GraceTimeForm,
    LateComeEarlyOutExportForm,
)

from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceOverTime,
    AttendanceLateComeEarlyOut,
    AttendanceValidationCondition,
    AttendanceRequestComment,
    AttendanceRequestFile,
    GraceTime,
)
from attendance.filters import (
    AttendanceReGroup,
    AttendanceOvertimeReGroup,
    LateComeEarlyOutReGroup,
    AttendanceActivityReGroup,
)
from payroll.models.models import WorkRecord


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


def attendance_day_checking(attendance_date, minimum_hour):
    # Convert the string to a datetime object
    attendance_datetime = datetime.strptime(attendance_date, "%Y-%m-%d")

    # Extract name of the day
    attendance_day = attendance_datetime.strftime("%A")

    # Taking all holidays into a list
    leaves = []
    holidays = Holiday.objects.all()
    for holi in holidays:
        start_date = holi.start_date
        end_date = holi.end_date

        # Convert start_date and end_date to datetime objects
        start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
        end_date = datetime.strptime(str(end_date), "%Y-%m-%d")

        # Add dates in between start date and end date including both
        current_date = start_date
        while current_date <= end_date:
            leaves.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

    # Checking attendance date is in holiday list, if found making the minimum hour to 00:00
    for leave in leaves:
        if str(leave) == str(attendance_date):
            minimum_hour = "00:00"
            break

    # Making a dictonary contains week day value and leave day pairs
    company_leaves = {}
    company_leave = CompanyLeave.objects.all()
    for com_leave in company_leave:
        a = dict(WEEK_DAYS).get(com_leave.based_on_week_day)
        b = com_leave.based_on_week
        company_leaves[b] = a

    # Checking the attendance date is in which week
    week_in_month = str(((attendance_datetime.day - 1) // 7 + 1) - 1)

    # Checking the attendance date is in the company leave or not
    for pairs in company_leaves.items():
        # For all weeks based_on_week is None
        if str(pairs[0]) == "None":
            if str(pairs[1]) == str(attendance_day):
                minimum_hour = "00:00"
                break
        # Checking with based_on_week and attendance_date week
        if str(pairs[0]) == week_in_month:
            if str(pairs[1]) == str(attendance_day):
                minimum_hour = "00:00"
                break
    return minimum_hour


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


def get_record_per_page():
    """
    This method will return the record per page count
    """
    return 50


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


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
        data_frame = pd.read_excel(file)
        attendance_dicts = data_frame.to_dict("records")
        attendance_import = process_attendance_data(attendance_dicts)

        if attendance_import:
            error_data = handle_attendance_errors(attendance_import)
            data_frame = pd.DataFrame(error_data, columns=error_data.keys())
            response = HttpResponse(content_type="application/ms-excel")
            response["Content-Disposition"] = 'attachment; filename="ImportError.xlsx"'
            data_frame.to_excel(response, index=False)
            return response

        return redirect(attendance_view)
    return redirect(attendance_view)


@login_required
def attendance_export(request):
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
    export_form = AttendanceExportForm()
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
    ot_attendances = Attendance.objects.filter(
        overtime_second__gte=minot,
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
            "export_form": export_form,
            "validate_attendances": paginator_qry(
                validate_attendances, request.GET.get("vpage")
            ),
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "overtime_attendances": paginator_qry(
                ot_attendances, request.GET.get("opage")
            ),
            "validate_attendances_ids": validate_attendances_ids,
            "ot_attendances_ids": ot_attendances_ids,
            "attendances_ids": attendances_ids,
            "f": filter_obj,
            "export": AttendanceFilters(queryset=Attendance.objects.all()),
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
        {
            "form": form,
            "urlencode": request.GET.urlencode(),
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

                except ProtectedError as e:
                    model_verbose_names_set = set()
                    for obj in e.protected_objects:
                        model_verbose_names_set.add(
                            __(obj._meta.verbose_name.capitalize())
                        )
                    model_names_str = ", ".join(model_verbose_names_set)
                    messages.error(
                        request,
                        _(
                            ("An attendance entry for {} already exists.").format(
                                model_names_str
                            )
                        ),
                    )
        except Attendance.DoesNotExist:
            messages.error(request, _("Attendance not found."))

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
    export_obj = AttendanceOverTimeFilter()
    export_fields = AttendanceOverTimeExportForm()
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
            "export_obj": export_obj,
            "export_fields": export_fields,
            "gp_fields": AttendanceOvertimeReGroup.fields,
            "filter_dict": data_dict,
        },
    )


def attendance_account_export(request):
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
        return redirect(f"/attendance/attendance-overtime-search?{previous_data}")
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
    export_form = AttendanceActivityExportForm()
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
            "export": AttendanceActivityFilter(
                queryset=AttendanceActivity.objects.all()
            ),
            "gp_fields": AttendanceActivityReGroup.fields,
            "export_form": export_form,
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
    This method is used to delete bulk of attendances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for attendance_id in ids:
        try:
            activity = AttendanceActivity.objects.get(id=attendance_id)
            activity.delete()
            messages.success(
                request,
                _("{employee} activity deleted.").format(employee=activity.employee_id),
            )

        except (AttendanceActivity.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Attendance not found."))
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("attendance.change_attendanceactivity")
def attendance_activity_export(request):
    return export_data(
        request=request,
        model=AttendanceActivity,
        filter_class=AttendanceActivityFilter,
        form_class=AttendanceActivityExportForm,
        file_name="Attendance_activity",
    )


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
    in_seconds = attendance_activity.clock_in.second
    # out
    out_year = attendance_activity.clock_out_date.year
    out_month = attendance_activity.clock_out_date.month
    out_day = attendance_activity.clock_out_date.day
    out_hour = attendance_activity.clock_out.hour
    out_minute = attendance_activity.clock_out.minute
    out_seconds = attendance_activity.clock_out.second
    return datetime(
        in_year, in_month, in_day, in_hour, in_minute, in_seconds
    ), datetime(out_year, out_month, out_day, out_hour, out_minute, out_seconds)


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
    export_form = LateComeEarlyOutExportForm()
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceLateComeEarlyOut, data_dict)
    return render(
        request,
        template,
        {
            "data": paginator_qry(reports, request.GET.get("page")),
            "f": filter_obj,
            "gp_fields": LateComeEarlyOutReGroup.fields,
            "export": LateComeEarlyOutFilter(
                queryset=AttendanceLateComeEarlyOut.objects.all()
            ),
            "filter_dict": data_dict,
            "export_form": export_form,
            "late_in_early_out_ids": late_in_early_out_ids,
        },
    )


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
    return export_data(
        request=request,
        model=AttendanceLateComeEarlyOut,
        filter_class=LateComeEarlyOutFilter,
        form_class=LateComeEarlyOutExportForm,
        file_name="Late_come_",
    )


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
    This method is used to validate bulk of attendances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for obj_id in ids:
        try:
            attendance = Attendance.objects.get(id=obj_id)
            if not attendance.is_validate_request:
                attendance.attendance_validated = True
                attendance.save()
                messages.success(request, _("Attendance validated."))
            else:
                messages.info(
                    request,
                    _(
                        "Pending attendance update request for {}'s attendance on {}!"
                    ).format(attendance.employee_id, attendance.attendance_date),
                )
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Your attendance for the date {attendance.attendance_date} is validated",
                verb_ar=f"تم التحقق من حضورك في تاريخ {attendance.attendance_date}",
                verb_de=f"Ihre Anwesenheit für das Datum {attendance.attendance_date} wurde bestätigt",
                verb_es=f"Se ha validado su asistencia para la fecha {attendance.attendance_date}",
                verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée",
                redirect=f"/attendance/view-my-attendance?id={attendance.id}",
                icon="checkmark",
            )
        except (Attendance.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Attendance not found"))
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
            redirect=f"/attendance/view-my-attendance?id={attendance.id}",
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
                redirect=f"/attendance/view-my-attendance?id={attendance.id}",
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
                redirect=f"/attendance/attendance-overtime-view?id={attendance.id}",
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
                redirect=f"/attendance/attendance-overtime-view?id={attendance.id}",
                icon="checkmark",
            )
        except (Attendance.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Attendance not found"))
    return JsonResponse({"message": "Success"})


def form_shift_dynamic_data(request):
    """
    This method is used to update the shift details to the form
    """
    shift_id = request.POST["shift_id"]
    attendance_date_str = request.POST.get("attendance_date")
    today = datetime.now()
    attendance_date = date(day=today.day, month=today.month, year=today.year)
    if attendance_date_str is not None and attendance_date_str != "":
        attendance_date = datetime.strptime(attendance_date_str, "%Y-%m-%d").date()
    day = attendance_date.strftime("%A").lower()
    schedule_today = EmployeeShiftSchedule.objects.filter(
        shift_id__id=shift_id, day__day=day
    ).first()
    shift_start_time = ""
    shift_end_time = ""
    minimum_hour = "00:00"
    attendance_clock_out_date = attendance_date
    if schedule_today is not None:
        shift_start_time = schedule_today.start_time
        shift_end_time = schedule_today.end_time
        minimum_hour = schedule_today.minimum_working_hour
        if shift_end_time < shift_start_time:
            attendance_clock_out_date = attendance_date + timedelta(days=1)
    worked_hour = minimum_hour
    if attendance_date == date(day=today.day, month=today.month, year=today.year):
        shift_end_time = datetime.now().strftime("%H:%M")
        worked_hour = "00:00"

    minimum_hour = attendance_day_checking(str(attendance_date), minimum_hour)

    return JsonResponse(
        {
            "shift_start_time": shift_start_time,
            "shift_end_time": shift_end_time,
            "checkin_date": attendance_date.strftime("%Y-%m-%d"),
            "minimum_hour": minimum_hour,
            "worked_hour": worked_hour,
            "checkout_date": attendance_clock_out_date.strftime("%Y-%m-%d"),
        }
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
@permission_required("attendance.add_gracetime")
def create_grace_time(request):
    """
    function used to create grace time .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return grace time form template
    """
    is_default = eval(request.GET.get("default"))
    form = GraceTimeForm(initial={"is_default": is_default})

    if request.method == "POST":
        form = GraceTimeForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            messages.success(request, _("Grace time created successfully."))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "attendance/grace_time/grace_time_form.html",
        {"form": form, "is_default": is_default},
    )


@login_required
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
    print('_______________________________________________________________________')
    print(grace_time.__dict__)
    print('_______________________________________________________________________')
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
    if request.GET.get("view") == "shift":
        return redirect("/settings/grace-settings-view")
    else:
        return redirect("/settings/grace-settings-view")


@login_required
@permission_required("attendance.update_gracetime")
def update_isactive_gracetime(request):
    """
    ajax function to update is active field in grace time.
    Args:
    - isChecked: Boolean value representing the state of grace time,
    - graceId: Id of grace time object
    """
    isChecked = request.POST.get("isChecked")
    graceId = request.POST.get("graceId")
    grace_time = GraceTime.objects.get(id=graceId)
    if isChecked == "true":
        grace_time.is_active = True

        response = {
            "type": "success",
            "message": _("Default grace time activated successfully."),
        }
    else:
        grace_time.is_active = False
        response = {
            "type": "success",
            "message": _("Default grace time deactivated successfully."),
        }
    grace_time.save()
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
                        redirect=f"/attendance/request-attendance-view?id={attendance.id}",
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
                        redirect=f"/attendance/request-attendance-view?id={attendance.id}",
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
                        redirect=f"/attendance/request-attendance-view?id={attendance.id}",
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
                    redirect=f"/attendance/request-attendance-view?id={attendance.id}",
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

    comment = AttendanceRequestComment.objects.get(id=comment_id)
    attendance_id = comment.request_id.id
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return redirect("attendance-request-view-comment", attendance_id=attendance_id)


@login_required
def delete_comment_file(request):
    """
    Used to delete attachment
    """
    ids = request.GET.getlist("ids")
    AttendanceRequestFile.objects.filter(id__in=ids).delete()
    leave_id = request.GET["leave_id"]
    comments = AttendanceRequestComment.objects.filter(request_id=leave_id).order_by(
        "-created_at"
    )
    return render(
        request,
        "requests/attendance/attendance_comment.html",
        {
            "comments": comments,
            "request_id": leave_id,
        },
    )


@login_required
def work_records(request):
    employees = Employee.objects.filter(is_active=True)
    data = []
    today = date.today()
    month_matrix = calendar.monthcalendar(today.year, today.month)

    days = [day for week in month_matrix for day in week if day != 0]
    current_month_date_list = [
        datetime(today.year, today.month, day).date() for day in days
    ]

    for employee in employees:
        work_record_list = []
        work_records_dict = {
            record.date: record
            for record in WorkRecord.objects.filter(
                employee_id=employee, date__in=current_month_date_list
            )
        }

        for day in current_month_date_list:
            work_record = work_records_dict.get(day, None)
            work_record_list.append(work_record)
        data.append(
            {
                "employee": employee,
                "work_record": work_record_list,
            }
        )

    context = {
        "current_date": today,
        "current_month_dates_list": current_month_date_list,
        "data": paginator_qry(data, 1),
    }
    return render(
        request, "attendance/work_record/work_record_view.html", context=context
    )


@login_required
@hx_request_required
def work_records_change_month(request):
    if request.GET.get("month"):
        date_obj = request.GET.get("month")
        month = int(date_obj.split("-")[1])
        year = int(date_obj.split("-")[0])
    else:
        month = date.today().month
        year = date.today().year

    employees = Employee.objects.filter(is_active=True)
    data = []
    month_matrix = calendar.monthcalendar(year, month)

    days = [day for week in month_matrix for day in week if day != 0]
    current_month_date_list = [datetime(year, month, day).date() for day in days]

    for employee in employees:
        work_record_list = []
        work_records_dict = {
            record.date: record
            for record in WorkRecord.objects.filter(
                employee_id=employee, date__in=current_month_date_list
            )
        }

        for day in current_month_date_list:
            work_record = work_records_dict.get(day, None)
            work_record_list.append(work_record)
        data.append(
            {
                "employee": employee,
                "work_record": work_record_list,
            }
        )

    context = {
        "current_month_dates_list": current_month_date_list,
        "data": paginator_qry(data, request.GET.get("page")),
    }
    return render(
        request, "attendance/work_record/work_record_list.html", context=context
    )


@login_required
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
