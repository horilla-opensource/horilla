"""
search.py

This is moduel is used to register end point related to the search filter functionalities
"""
import json
from datetime import datetime
from urllib.parse import parse_qs
from django.shortcuts import render
from base.methods import filtersubordinates, sortby, get_key_instances
from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from attendance.filters import (
    AttendanceActivityFilter,
    AttendanceFilters,
    LateComeEarlyOutFilter,
)
from attendance.forms import AttendanceOverTimeForm
from attendance.filters import AttendanceOverTimeFilter
from attendance.models import (
    Attendance,
    AttendanceValidationCondition,
    AttendanceOverTime,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
)
from attendance.views.views import paginator_qry, strtime_seconds
from django.utils.translation import gettext_lazy as _


@login_required
@manager_can_enter("attendance.view_attendance")
def attendance_search(request):
    """
    This method is used to search attendance by employee
    """
    month_name = ""
    params = [
        "employee_id",
        "attendance_validated",
        "attendance_date__gte",
        "attendance_date__lte",
    ]
    remove_params = []
    if params == list(request.GET.keys()):
        remove_params = [param for param in params if param != "employee_id"]
    previous_data = request.GET.urlencode()
    field = request.GET.get("field")
    minot = strtime_seconds("00:00")
    condition = AttendanceValidationCondition.objects.first()
    if condition is not None and condition.minimum_overtime_to_approve is not None:
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
    data_dict = parse_qs(previous_data)
    get_key_instances(Attendance, data_dict)
    keys_to_remove = [
        key
        for key, value in data_dict.items()
        if value == ["unknown"] or key in remove_params
    ]
    for key in keys_to_remove:
        data_dict.pop(key)
    if params == list(request.GET.keys()):
        ot_attendances = validate_attendances = attendances
        template = "attendance/attendance/validate_attendance.html"
        if not attendances:
            date_object = datetime.strptime(
                request.GET.get("attendance_date__gte"), "%Y-%m-%d"
            )
            month_name = _(date_object.strftime("%B"))
            template = "attendance/attendance/validate_attendance_empty.html"
    validate_attendances_ids = json.dumps([instance.id for instance in paginator_qry(validate_attendances, request.GET.get("vpage")).object_list])
    ot_attendances_ids = json.dumps([instance.id for instance in paginator_qry(ot_attendances, request.GET.get("opage")).object_list])
    attendances_ids = json.dumps([instance.id for instance in paginator_qry(attendances, request.GET.get("page")).object_list])   
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
            "validate_attendances_ids": validate_attendances_ids,
            "ot_attendances_ids": ot_attendances_ids,
            "attendances_ids": attendances_ids,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
            "month_name": month_name,
        },
    )


@login_required
def attendance_overtime_search(request):
    """
    This method is used to search attendance overtime account by employee.
    """
    field = request.GET.get("field")
    previous_data = request.GET.urlencode()

    accounts = AttendanceOverTimeFilter(request.GET).qs
    form = AttendanceOverTimeForm()
    template = "attendance/attendance_account/overtime_list.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        accounts = accounts.order_by(field_copy)
        template = "attendance/attendance_account/group_by.html"
    self_account = accounts.filter(employee_id__employee_user_id=request.user)
    accounts = sortby(request, accounts, "sortby")
    accounts = filtersubordinates(
        request, accounts, "attendance.view_attendanceovertime"
    )
    accounts = accounts | self_account
    accounts = accounts.distinct()
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceOverTime, data_dict)
    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)
    return render(
        request,
        template,
        {
            "accounts": paginator_qry(accounts, request.GET.get("page")),
            "form": form,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
        },
    )


@login_required
def attendance_activity_search(request):
    """
    This method is used to search attendance activity
    """
    previous_data = request.GET.urlencode()
    field = request.GET.get("field")
    attendance_activities = AttendanceActivityFilter(
        request.GET,
    ).qs
    self_attendance_activities = attendance_activities.filter(
        employee_id__employee_user_id=request.user
    )
    attendance_activities = filtersubordinates(
        request, attendance_activities, "attendance.view_attendanceovertime"
    )
    attendance_activities = attendance_activities | self_attendance_activities
    attendance_activities = attendance_activities.distinct()
    template = "attendance/attendance_activity/activity_list.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        attendance_activities = attendance_activities.order_by(field_copy)
        template = "attendance/attendance_activity/group_by.html"


    attendance_activities = sortby(request, attendance_activities, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceActivity, data_dict)
    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)
    return render(
        request,
        template,
        {
            "data": paginator_qry(attendance_activities, request.GET.get("page")),
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
        },
    )


@login_required
def late_come_early_out_search(request):
    """
    This method is used to search late come early out by employee.
    Also include filter and pagination.
    """
    field = request.GET.get("field")
    previous_data = request.GET.urlencode()
    reports = LateComeEarlyOutFilter(
        request.GET,
    ).qs
    self_reports = reports.filter(
        employee_id__employee_user_id=request.user
    )
    
    reports = filtersubordinates(
        request, reports, "attendance.view_attendancelatecomeearlyout"
    )
    reports = reports | self_reports
    reports.distinct()
    template = "attendance/late_come_early_out/report_list.html"
    if field != "" and field is not None:
        template = "attendance/late_come_early_out/group_by.html"
        field_copy = field.replace(".", "__")
        reports = reports.order_by(field_copy)
   
    reports = sortby(request, reports, "sortby")
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceLateComeEarlyOut, data_dict)
    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)

    return render(
        request,
        template,
        {
            "data": paginator_qry(reports, request.GET.get("page")),
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
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
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)

    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)
    attendances_ids = json.dumps([instance.id for instance in paginator_qry(attendances, request.GET.get("page")).object_list])
    return render(
        request,
        "attendance/own_attendance/attendances.html",
        {
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "filter_dict": data_dict,
            "attendances_ids": attendances_ids,
        },
    )


@login_required
def own_attendance_sort(request):
    """
    This method is used to sort out attendances
    """
    attendances = Attendance.objects.filter(employee_id=request.user.employee_get)
    previous_data = request.GET.urlencode()
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
def search_attendance_requests(request):
    field = request.GET.get("field")
    requests = Attendance.objects.filter(
        is_validate_request=True,
    )
    requests = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=requests,
    )
    requests = requests | Attendance.objects.filter(
        employee_id__employee_user_id=request.user,
        is_validate_request=True,
    )
    requests = AttendanceFilters(request.GET, requests).qs
    attendances = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=Attendance.objects.all(),
    )
    attendances = attendances | Attendance.objects.filter(
        employee_id__employee_user_id=request.user
    )
    attendances = AttendanceFilters(request.GET, attendances).qs
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(Attendance, data_dict)

    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)

    template = "requests/attendance/request_lines.html"
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        requests = requests.order_by(field_copy)
        attendances = attendances.order_by(field_copy)
        template = "requests/attendance/group_by.html"

    requests_ids = json.dumps([instance.id for instance in paginator_qry(requests, request.GET.get("rpage")).object_list])
    attendances_ids = json.dumps([instance.id for instance in paginator_qry(attendances, request.GET.get("page")).object_list])
    return render(
        request,
        template,
        {
            "requests": paginator_qry(requests, request.GET.get("rpage")),
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "requests_ids": requests_ids,
            "attendances_ids": attendances_ids,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field": field,
        },
    )


from django.http import JsonResponse


@login_required
def widget_filter(request):
    """
    This method is used to return all the ids of the employees
    """
    ids = AttendanceFilters(request.GET).qs.values_list("id", flat=True)
    return JsonResponse({"ids": list(ids)})
