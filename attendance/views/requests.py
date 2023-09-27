"""
requests.py

This module is used to register the endpoints to the attendance requests
"""
import json
import copy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from notifications.signals import notify
from horilla.decorators import login_required, manager_can_enter
from base.methods import filtersubordinates, is_reportingmanager, choosesubordinates
from employee.models import Employee
from attendance.models import Attendance
from attendance.forms import AttendanceRequestForm, NewRequestForm
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
    filter_obj = AttendanceFilters()
    check_attendance = Attendance.objects.all()
    if check_attendance.exists():
        template = "requests/attendance/view-requests.html"
    else:
        template = "requests/attendance/requests_empty.html"
    return render(
        request,
        template,
        {
            "requests": paginator_qry(requests, None),
            "attendances": paginator_qry(attendances, None),
            "f": filter_obj,
        },
    )


@login_required
def request_new(request):
    """
    This method is used to create new attendance requests
    """
    form = NewRequestForm()
    form = choosesubordinates(request, form, "attendance.change_attendance")
    form.fields["employee_id"].queryset = form.fields[
        "employee_id"
    ].queryset | Employee.objects.filter(employee_user_id=request.user)
    form.fields['employee_id'].initial = request.user.employee_get.id
    if request.method == "POST":
        form = NewRequestForm(request.POST)
        form = choosesubordinates(request, form, "attendance.change_attendance")
        form.fields["employee_id"].queryset = form.fields[
            "employee_id"
        ].queryset | Employee.objects.filter(employee_user_id=request.user)
        if form.is_valid():
            if form.new_instance is not None:
                form.new_instance.save()
                messages.success(request, "New attendance request created")
                return HttpResponse(
                    render(
                        request,
                        "requests/attendance/request_new_form.html",
                        {"form": form},
                    ).content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )
            messages.success(request, "Update request updated")
            return HttpResponse(
                render(
                    request,
                    "requests/attendance/request_new_form.html",
                    {"form": form},
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )

    return render(request, "requests/attendance/request_new_form.html", {"form": form})


@login_required
def attendance_request_changes(request, attendance_id):
    """
    This method is used to store the requested changes to the instance
    """
    attendance = Attendance.objects.get(id=attendance_id)
    form = AttendanceRequestForm(instance=attendance)
    if request.method == "POST":
        form = AttendanceRequestForm(request.POST, instance=copy.copy(attendance))
        if form.is_valid():
            # commit already set to False
            # so the changes not affected to the db
            instance = form.save()
            instance.employee_id = attendance.employee_id
            instance.id = attendance.id
            if attendance.request_type != "create_request":
                attendance.requested_data = json.dumps(instance.serialize())
                attendance.request_description = instance.request_description
                # set the user level validation here
                attendance.is_validate_request = True
                attendance.save()
            else:
                instance.save()

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
    empty_data = {
        "employee_id": None,
        "attendance_date": None,
        "attendance_clock_in_date": None,
        "attendance_clock_in": None,
        "attendance_clock_out": None,
        "attendance_clock_out_date": None,
        "shift_id": None,
        "work_type_id": None,
        "attendance_worked_hour": None,
    }
    if attendance.request_type == "create_request":
        other_dict = first_dict
        first_dict = empty_data
    else:
        other_dict = json.loads(attendance.requested_data)

    return render(
        request,
        "requests/attendance/individual_view.html",
        {
            "data": get_diff_dict(first_dict, other_dict, Attendance),
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
    attendance.attendance_validated = True
    attendance.is_validate_request_approved = True
    attendance.is_validate_request = False
    attendance.request_description = None
    attendance.save()
    if attendance.requested_data is not None:
        requested_data = json.loads(attendance.requested_data)
        Attendance.objects.filter(id=attendance_id).update(**requested_data)
    messages.success(request, "Attendance request has been approved")
    notify.send(
        request.user,
        recipient=attendance.employee_id.employee_user_id,
        verb = f"Your attendance request for {attendance.attendance_date} is validated",
        verb_ar = f"تم التحقق من طلب حضورك في تاريخ {attendance.attendance_date}",
        verb_de = f"Ihr Anwesenheitsantrag für das Datum {attendance.attendance_date} wurde bestätigt",
        verb_es = f"Se ha validado su solicitud de asistencia para la fecha {attendance.attendance_date}",
        verb_fr = f"Votre demande de présence pour la date {attendance.attendance_date} est validée",
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
        attendance.request_type = None

        attendance.save()
        if attendance.request_type == "create_request":
            attendance.delete()
            messages.success(request, "The requested attendance is removed.")
        else:
            messages.success(request, "Attendance request has been cancelled")
        notify.send(
            request.user,
            recipient=attendance.employee_id.employee_user_id,
            verb=f"Your attendance request for {attendance.attendance_date} is cancelled",
            verb_ar = f"تم إلغاء طلب حضورك في تاريخ {attendance.attendance_date}",
            verb_de = f"Ihr Antrag auf Teilnahme am {attendance.attendance_date} wurde storniert",
            verb_es = f"Se ha cancelado su solicitud de asistencia para el {attendance.attendance_date}",
            verb_fr = f"Votre demande de participation pour le {attendance.attendance_date} a été annulée",
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
    initial = attendance.serialize()
    if attendance.request_type != "create_request":
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
            instance.request_type = None
            instance.save()
            messages.success(request, "Attendance request has been approved")

            return HttpResponse(
                render(
                    request, "requests/attendance/update_form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "requests/attendance/update_form.html", {"form": form})
