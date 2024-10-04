"""
search.py

This is moduel is used to register end point related to the search filter functionalities
"""

import json
from datetime import datetime
from urllib.parse import parse_qs

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from attendance.filters import (
    AttendanceActivityFilter,
    AttendanceFilters,
    AttendanceOverTimeFilter,
    LateComeEarlyOutFilter,
)
from attendance.forms import AttendanceOverTimeForm
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceValidationCondition,
)
from attendance.views.views import paginator_qry, strtime_seconds
from base.methods import filtersubordinates, get_key_instances, sortby
from horilla.decorators import hx_request_required, login_required, manager_can_enter
from horilla.group_by import group_by_queryset


@login_required
@hx_request_required
@manager_can_enter("attendance.view_attendance")
def attendance_search(request):
    """
    This method is used to search attendances
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
    all_attendances = Attendance.objects.all()
    if request.GET.get("sortby"):
        all_attendances = sortby(request, all_attendances, "sortby")

    if condition is not None and condition.minimum_overtime_to_approve is not None:
        minot = strtime_seconds(condition.minimum_overtime_to_approve)

    validate_attendances = all_attendances.filter(attendance_validated=False)
    attendances = all_attendances.filter(attendance_validated=True)
    ot_attendances = all_attendances.filter(
        overtime_second__gt=0,
        attendance_validated=True,
    )

    validate_attendances = AttendanceFilters(request.GET, validate_attendances).qs
    attendances = AttendanceFilters(request.GET, attendances).qs
    ot_attendances = AttendanceFilters(request.GET, ot_attendances).qs

    if not request.user.has_perm("attendance.view_attendance"):
        attendances = filtersubordinates(
            request, attendances, "attendance.view_attendance"
        )
        validate_attendances = filtersubordinates(
            request, validate_attendances, "attendance.view_attendance"
        )
        ot_attendances = filtersubordinates(
            request, ot_attendances, "attendance.view_attendance"
        )
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

    template = "attendance/attendance/tab_content.html"
    validate_attendances_ids, ot_attendances_ids, attendances_ids = [], [], []
    if field != "" and field is not None:
        attendances = group_by_queryset(
            attendances, field, request.GET.get("page"), "page"
        )
        list_values = [entry["list"] for entry in attendances]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        attendances_ids = json.dumps(list(id_list))

        validate_attendances = group_by_queryset(
            validate_attendances, field, request.GET.get("vpage"), "vpage"
        )
        list_values = [entry["list"] for entry in validate_attendances]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        validate_attendances_ids = json.dumps(list(id_list))

        ot_attendances = group_by_queryset(
            ot_attendances, field, request.GET.get("opage"), "opage"
        )
        list_values = [entry["list"] for entry in ot_attendances]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        ot_attendances_ids = json.dumps(list(id_list))

        template = "attendance/attendance/group_by.html"
    else:
        validate_attendances = paginator_qry(
            validate_attendances, request.GET.get("vpage")
        )
        ot_attendances = paginator_qry(ot_attendances, request.GET.get("opage"))
        attendances = paginator_qry(attendances, request.GET.get("page"))
        validate_attendances_ids = json.dumps(
            [instance.id for instance in validate_attendances.object_list]
        )
        ot_attendances_ids = json.dumps(
            [instance.id for instance in ot_attendances.object_list]
        )
        attendances_ids = json.dumps(
            [instance.id for instance in attendances.object_list]
        )
    return render(
        request,
        template,
        {
            "validate_attendances": validate_attendances,
            "attendances": attendances,
            "overtime_attendances": ot_attendances,
            "validate_attendances_ids": validate_attendances_ids,
            "ot_attendances_ids": ot_attendances_ids,
            "attendances_ids": attendances_ids,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
            "month_name": month_name,
            "minot": minot,
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
    if field != "" and field is not None:
        accounts = group_by_queryset(accounts, field, request.GET.get("page"), "page")
        template = "attendance/attendance_account/group_by.html"
    else:
        accounts = paginator_qry(accounts, request.GET.get("page"))
    return render(
        request,
        template,
        {
            "accounts": accounts,
            "form": form,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
        },
    )


@login_required
@hx_request_required
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
    attendance_activities = sortby(request, attendance_activities, "orderby")
    if field != "" and field is not None:
        attendance_activities = group_by_queryset(
            attendance_activities, field, request.GET.get("page"), "page"
        )
        list_values = [entry["list"] for entry in attendance_activities]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        activity_ids = json.dumps(list(id_list))
        template = "attendance/attendance_activity/group_by.html"
    else:
        attendance_activities = paginator_qry(
            attendance_activities, request.GET.get("page")
        )
        activity_ids = json.dumps(
            [instance.id for instance in paginator_qry(attendance_activities, None)]
        )
    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceActivity, data_dict)
    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)
    return render(
        request,
        template,
        {
            "data": attendance_activities,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
            "activity_ids": activity_ids,
        },
    )


@login_required
@hx_request_required
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
    self_reports = reports.filter(employee_id__employee_user_id=request.user)

    reports = filtersubordinates(
        request, reports, "attendance.view_attendancelatecomeearlyout"
    )
    reports = reports | self_reports
    reports.distinct()
    reports = sortby(request, reports, "sortby")
    template = "attendance/late_come_early_out/report_list.html"
    if field != "" and field is not None:
        template = "attendance/late_come_early_out/group_by.html"
        reports = group_by_queryset(reports, field, request.GET.get("page"), "page")
        list_values = [entry["list"] for entry in reports]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        late_in_early_out_ids = json.dumps(list(id_list))
    else:
        reports = paginator_qry(reports, request.GET.get("page"))
        late_in_early_out_ids = json.dumps(
            [instance.id for instance in reports.object_list]
        )

    data_dict = parse_qs(previous_data)
    get_key_instances(AttendanceLateComeEarlyOut, data_dict)
    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)

    return render(
        request,
        template,
        {
            "data": reports,
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
            "late_in_early_out_ids": late_in_early_out_ids,
        },
    )


@login_required
@hx_request_required
def filter_own_attendance(request):
    """
    This method is used to filter own attendances
    """
    params = [
        "employee_id",
        "attendance_validated",
        "attendance_date__gte",
        "attendance_date__lte",
    ]
    remove_params = []
    if params == list(request.GET.keys()):
        remove_params = [
            param
            for param in params
            if param != "attendance_date__gte" and param != "attendance_date__lte"
        ]

    attendances = Attendance.objects.filter(employee_id=request.user.employee_get)
    attendances = AttendanceFilters(request.GET, queryset=attendances).qs
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    field = request.GET.get("field")
    template = "attendance/own_attendance/attendances.html"
    previous_data = request.GET.urlencode()
    keys_to_remove = [
        key
        for key, value in data_dict.items()
        if value == ["unknown"] or key in remove_params
    ]
    for key in keys_to_remove:
        data_dict.pop(key)
    attendances_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                attendances, request.GET.get("page")
            ).object_list
        ]
    )
    if field != "" and field is not None:
        attendances = group_by_queryset(
            attendances, field, request.GET.get("page"), "page"
        )
        template = "attendance/own_attendance/group_by.html"
        attendances_ids = []
    return render(
        request,
        template,
        {
            "attendances": paginator_qry(attendances, request.GET.get("page")),
            "filter_dict": data_dict,
            "attendances_ids": attendances_ids,
            "pd": previous_data,
            "field": field,
        },
    )


@login_required
@hx_request_required
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
@hx_request_required
def search_attendance_requests(request):
    field = request.GET.get("field")
    all_attendance = Attendance.objects.all()
    if request.GET.get("sortby"):
        all_attendance = sortby(request, all_attendance, "sortby")

    requests = all_attendance.filter(
        is_validate_request=True, employee_id__is_active=True
    )
    requests = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=requests,
    )
    requests = requests | all_attendance.filter(
        employee_id__employee_user_id=request.user,
        is_validate_request=True,
    )
    requests = AttendanceFilters(request.GET, requests).qs
    attendances = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=all_attendance.all(),
    )
    attendances = attendances | all_attendance.filter(
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
    requests_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                requests, request.GET.get("rpage")
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
    if field != "" and field is not None:
        requests = group_by_queryset(requests, field, request.GET.get("rpage"), "rpage")
        attendances = group_by_queryset(
            attendances, field, request.GET.get("page"), "page"
        )
        template = "requests/attendance/group_by.html"
    else:
        requests = paginator_qry(requests, request.GET.get("rpage"))
        attendances = paginator_qry(attendances, request.GET.get("page"))
    return render(
        request,
        template,
        {
            "requests": requests,
            "attendances": attendances,
            "requests_ids": requests_ids,
            "attendances_ids": attendances_ids,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field": field,
        },
    )


@login_required
def widget_filter(request):
    """
    This method is used to return all the ids of the employees
    """
    ids = AttendanceFilters(request.GET).qs.values_list("id", flat=True)
    return JsonResponse({"ids": list(ids)})
