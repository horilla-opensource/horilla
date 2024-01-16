"""
views.py

This module is used to map url patterns with request and approve methods in Dashboard.
"""

from datetime import date
import json
from django.shortcuts import render
from attendance.models import Attendance, AttendanceValidationCondition
from attendance.views.views import strtime_seconds
from base.methods import filtersubordinates
from base.models import ShiftRequest, WorkTypeRequest
from employee.not_in_out_dashboard import paginator_qry
from horilla.decorators import login_required
from leave.models import LeaveAllocationRequest, LeaveRequest


@login_required
def dashboard_shift_request(request):
    requests = ShiftRequest.objects.filter(approved= False,canceled = False)
    requests = filtersubordinates(
        request, requests, "base.add_shiftrequest"
    )
    requests_ids = json.dumps(
        [
            instance.id for instance in requests
        ]
    )
    return render(request, "request_and_approve/shift_request.html",{"requests": requests,"requests_ids": requests_ids,})


@login_required
def dashboard_work_type_request(request):
    requests = WorkTypeRequest.objects.filter(approved= False,canceled = False)
    requests = filtersubordinates(
        request, requests, "base.add_worktyperequest"
    )
    requests_ids = json.dumps(
        [
            instance.id for instance in requests
        ]
    )
    return render(request, "request_and_approve/work_type_request.html",{"requests": requests,"requests_ids": requests_ids,})


@login_required
def dashboard_overtime_approve(request):
    condition = AttendanceValidationCondition.objects.first()
    min_ot = strtime_seconds("00:00")
    if condition is not None and condition.minimum_overtime_to_approve is not None:
        min_ot = strtime_seconds(condition.minimum_overtime_to_approve)
    ot_attendances = Attendance.objects.filter(
        overtime_second__gte=min_ot,
        attendance_validated=True,
        employee_id__is_active=True,
        attendance_overtime_approve =False,
    )
    ot_attendances =  filtersubordinates(
        request, ot_attendances, "attendance.change_attendance"
    )
    ot_attendances_ids = json.dumps(
        [
            instance.id for instance in ot_attendances
        ]
    )
    return render(request, "request_and_approve/overtime_approve.html",{"overtime_attendances": ot_attendances,"ot_attendances_ids": ot_attendances_ids,})


@login_required
def dashboard_attendance_validate(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id__is_active=True
    )
    validate_attendances =  filtersubordinates(
        request, validate_attendances, "attendance.change_attendance"
    )
    validate_attendances = paginator_qry(validate_attendances, page_number)
    validate_attendances_ids = json.dumps(
        [
            instance.id for instance in validate_attendances
        ]
    )
    return render(request, "request_and_approve/attendance_validate.html",{"validate_attendances": validate_attendances,"validate_attendances_ids": validate_attendances_ids, "pd": previous_data,})


@login_required
def leave_request_and_approve(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    leave_requests = LeaveRequest.objects.filter(status = "requested")
    leave_requests =  filtersubordinates(
        request, leave_requests, "leave.change_leaverequest"
    )
    leave_requests = paginator_qry(leave_requests, page_number)
    leave_requests_ids = json.dumps(
        [
            instance.id for instance in leave_requests
        ]
    )
    return render(
        request,
        "request_and_approve/leave_request_approve.html",
        {
            "leave_requests": leave_requests,
            "requests_ids": leave_requests_ids, 
            "pd": previous_data,
            # "current_date":date.today(),
        }
    )


@login_required
def leave_allocation_approve(request):
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    allocation_reqests = LeaveAllocationRequest.objects.filter(status = "requested")
    allocation_reqests =  filtersubordinates(
        request, allocation_reqests, "leave.view_leaveallocationrequest"
    )
    # allocation_reqests = paginator_qry(allocation_reqests, page_number)
    allocation_reqests_ids = json.dumps(
        [
            instance.id for instance in allocation_reqests
        ]
    )
    return render(
        request,
        "request_and_approve/leave_allocation_approve.html",
        {
            "allocation_reqests": allocation_reqests,
            "reqests_ids": allocation_reqests_ids, 
            "pd": previous_data,
            # "current_date":date.today(),
        }
    )
