"""
views.py

This module is used to map url patterns with request and approve methods in Dashboard.
"""

import json
from datetime import date

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from asset.models import AssetRequest
from attendance.models import Attendance, AttendanceValidationCondition
from attendance.views.views import strtime_seconds
from base.methods import filtersubordinates
from base.models import ShiftRequest, WorkTypeRequest
from horilla.decorators import login_required
from leave.models import LeaveAllocationRequest, LeaveRequest
from pms.models import Feedback


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate query set
    """
    paginator = Paginator(qryset, 10)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
def dashboard_shift_request(request):
    requests = ShiftRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_shiftrequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    return render(
        request,
        "request_and_approve/shift_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
        },
    )


@login_required
def dashboard_work_type_request(request):
    requests = WorkTypeRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_worktyperequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    return render(
        request,
        "request_and_approve/work_type_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
        },
    )


@login_required
def dashboard_overtime_approve(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    condition = AttendanceValidationCondition.objects.first()
    min_ot = strtime_seconds("00:00")
    if condition is not None and condition.minimum_overtime_to_approve is not None:
        min_ot = strtime_seconds(condition.minimum_overtime_to_approve)
    ot_attendances = Attendance.objects.filter(
        overtime_second__gte=min_ot,
        attendance_validated=True,
        employee_id__is_active=True,
        attendance_overtime_approve=False,
    )
    ot_attendances = filtersubordinates(
        request, ot_attendances, "attendance.change_attendance"
    )
    ot_attendances = paginator_qry(ot_attendances, page_number)
    ot_attendances_ids = json.dumps([instance.id for instance in ot_attendances])
    return render(
        request,
        "request_and_approve/overtime_approve.html",
        {
            "overtime_attendances": ot_attendances,
            "ot_attendances_ids": ot_attendances_ids,
            "pd": previous_data,
        },
    )


@login_required
def dashboard_attendance_validate(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id__is_active=True
    )
    validate_attendances = filtersubordinates(
        request, validate_attendances, "attendance.change_attendance"
    )
    validate_attendances = paginator_qry(validate_attendances, page_number)
    validate_attendances_ids = json.dumps(
        [instance.id for instance in validate_attendances]
    )
    return render(
        request,
        "request_and_approve/attendance_validate.html",
        {
            "validate_attendances": validate_attendances,
            "validate_attendances_ids": validate_attendances_ids,
            "pd": previous_data,
        },
    )


@login_required
def leave_request_and_approve(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    leave_requests = LeaveRequest.objects.filter(
        status="requested", employee_id__is_active=True, start_date__gte=date.today()
    )
    leave_requests = filtersubordinates(
        request, leave_requests, "leave.change_leaverequest"
    )
    leave_requests = paginator_qry(leave_requests, page_number)
    leave_requests_ids = json.dumps([instance.id for instance in leave_requests])
    return render(
        request,
        "request_and_approve/leave_request_approve.html",
        {
            "leave_requests": leave_requests,
            "requests_ids": leave_requests_ids,
            "pd": previous_data,
            # "current_date":date.today(),
        },
    )


@login_required
def leave_allocation_approve(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    allocation_reqests = LeaveAllocationRequest.objects.filter(
        status="requested", employee_id__is_active=True
    )
    allocation_reqests = filtersubordinates(
        request, allocation_reqests, "leave.view_leaveallocationrequest"
    )
    # allocation_reqests = paginator_qry(allocation_reqests, page_number)
    allocation_reqests_ids = json.dumps(
        [instance.id for instance in allocation_reqests]
    )
    return render(
        request,
        "request_and_approve/leave_allocation_approve.html",
        {
            "allocation_reqests": allocation_reqests,
            "reqests_ids": allocation_reqests_ids,
            "pd": previous_data,
            # "current_date":date.today(),
        },
    )


@login_required
def dashboard_feedback_answer(request):
    employee = request.user.employee_get
    feedback_requested = Feedback.objects.filter(
        Q(manager_id=employee, manager_id__is_active=True)
        | Q(colleague_id=employee, colleague_id__is_active=True)
        | Q(subordinate_id=employee, subordinate_id__is_active=True)
    ).distinct()
    feedbacks = feedback_requested.exclude(feedback_answer__employee_id=employee)

    return render(
        request,
        "request_and_approve/feedback_answer.html",
        {"feedbacks": feedbacks, "current_date": date.today()},
    )


@login_required
def dashboard_asset_request_approve(request):
    asset_requests = AssetRequest.objects.filter(
        asset_request_status="Requested", requested_employee_id__is_active=True
    )

    asset_requests = filtersubordinates(
        request,
        asset_requests,
        "asset.change_assetrequest",
        field="requested_employee_id",
    )
    requests_ids = json.dumps([instance.id for instance in asset_requests])

    return render(
        request,
        "request_and_approve/asset_requests_approve.html",
        {
            "asset_requests": asset_requests,
            "requests_ids": requests_ids,
        },
    )
