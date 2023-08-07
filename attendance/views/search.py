"""
search.py

This is moduel is used to register end point related to the search filter functionalities
"""
from django.shortcuts import render
from base.methods import filtersubordinates, sortby
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
from attendance.models import Attendance, AttendanceValidationCondition
from attendance.views.views import paginator_qry, strtime_seconds


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
def search_attendance_requests(request):
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
    requests = AttendanceFilters(request.GET,requests).qs
    attendances = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=Attendance.objects.all(),
    )
    attendances = attendances | Attendance.objects.filter(
        employee_id__employee_user_id=request.user
    )
    attendances = AttendanceFilters(request.GET,attendances).qs
    return render(
        request,
        "requests/attendance/request_lines.html",
        {"requests": paginator_qry(requests,request.GET.get("rpage")), "attendances": paginator_qry(attendances,request.GET.get("page")),"pd":request.environ["QUERY_STRING"]},
    )
