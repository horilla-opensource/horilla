"""
requests.py

This module is used to register the endpoints to the attendance requests
"""
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from notifications.signals import notify
from horilla.decorators import login_required, manager_can_enter
from base.methods import filtersubordinates, is_reportingmanager
from attendance.models import Attendance
from attendance.forms import AttendanceRequestForm
from attendance.methods.differentiate import get_diff_dict
from attendance.views.views import paginator_qry
from attendance.filters import AttendanceFilters


@login_required
def request_attendance(request):
    """
    This method is used to render template to register new attendance for a normal user
    """
    form = AttendanceRequestForm()
    if request.method == "POST":
        form = AttendanceRequestForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
    return render(request, "requests/attendance/form.html", {"form": form})


@login_required
def request_attendance_view(request):
    """
    This method is used to view the attendances for to request
    """
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
    attendances = filtersubordinates(
        request=request,
        perm="attendance.view_attendance",
        queryset=Attendance.objects.all(),
    )
    attendances = attendances | Attendance.objects.filter(
        employee_id__employee_user_id=request.user
    )
    filter = AttendanceFilters()

    return render(
        request,
        "requests/attendance/view-requests.html",
        {
            "requests": paginator_qry(requests, None),
            "attendances": paginator_qry(attendances, None),
            "f": filter,
        },
    )


@login_required
def attendance_request_changes(request, attendance_id):
    """
    This method is used to store the requested changes to the instance
    """
    attendance = Attendance.objects.get(id=attendance_id)
    form = AttendanceRequestForm(instance=attendance)
    if request.method == "POST":
        form = AttendanceRequestForm(request.POST)
        if form.is_valid():
            # commit already set to False
            # so the changes not affected to the db
            instance = form.save()
            instance.employee_id = attendance.employee_id
            instance.id = attendance.id
            attendance.requested_data = json.dumps(instance.serialize())
            attendance.request_description = instance.request_description
            # set the user level validation here
            attendance.is_validate_request = True
            attendance.save()
            messages.success(request, "Attendance update request created.")
            return HttpResponse(
                render(
                    request, "requests/attendance/form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "requests/attendance/form.html", {"form": form})


@login_required
def validate_attendance_request(request, attendance_id):
    """
    This method to validate the requested attendance
    args:
        attendance_id : attendance id
    """
    attendance = Attendance.objects.get(id=attendance_id)
    first_dict = attendance.serialize()
    other_dict = json.loads(attendance.requested_data)
    
    return render(
        request,
        "requests/attendance/individual_view.html",
        {
            "data": get_diff_dict(first_dict, other_dict,Attendance),
            "attendance": attendance,
        },
    )


@login_required
@manager_can_enter("attendance.change_attendance")
def approve_validate_attendance_request(request, attendance_id):
    """
    This method is used to validate the attendance requests
    """
    attendance = Attendance.objects.get(id=attendance_id)
    requested_data = json.loads(attendance.requested_data)
    attendance.attendance_validated = True
    attendance.is_validate_request_approved = True
    attendance.is_validate_request = False
    attendance.request_description = None
    attendance.save()
    Attendance.objects.filter(id=attendance_id).update(**requested_data)
    messages.success(request, "Attendance request has been approved")
    notify.send(
        request.user,
        recipient=attendance.employee_id.employee_user_id,
        verb=f"Your attendance for {attendance.attendance_date} is validated",
        redirect="/attendance/request-attendance-view",
        icon="checkmark-circle-outline",
    )
    return redirect(request_attendance_view)


@login_required
def cancel_attendance_request(request, attendance_id):
    """
    This method is used to cancel attendance request
    """
    attendance = Attendance.objects.get(id=attendance_id)
    if (
        attendance.employee_id.employee_user_id == request.user
        or is_reportingmanager(request)
        or request.user.has_perm("attendance.change_attendance")
    ):
        attendance.is_validate_request_approved = False
        attendance.is_validate_request = False
        attendance.request_description = None
        attendance.requested_data = None
        attendance.save()
        messages.success(request, "Attendance request has been cancelled")
        notify.send(
            request.user,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your attendance for {attendance.attendance_date} is cancelled",
            redirect="/attendance/request-attendance-view",
            icon="close-circle-outline",
        )
    return redirect(request_attendance_view)


@login_required
@manager_can_enter("attendance.change_attendance")
def edit_validate_attendance(request, attendance_id):
    """
    This method is used to edit and update the validate request attendance
    """
    attendance = Attendance.objects.get(id=attendance_id)
    initial = json.loads(attendance.requested_data)
    initial["request_description"] = attendance.request_description
    form = AttendanceRequestForm(initial=initial)
    form.instance.id = attendance.id
    if request.method == "POST":
        form = AttendanceRequestForm(request.POST, instance=attendance)
        if form.is_valid():
            instance = form.save()
            instance.attendance_validated = True
            instance.is_validate_request_approved = True
            instance.is_validate_request = False
            instance.request_description = None
            instance.save()
            messages.success(request, "Attendance request has been approved")

            return HttpResponse(
                render(
                    request, "requests/attendance/update_form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "requests/attendance/update_form.html", {"form": form})
