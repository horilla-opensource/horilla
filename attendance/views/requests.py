"""
requests.py

This module is used to register the endpoints to the attendance requests
"""
import json
import copy
from urllib.parse import parse_qs
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from notifications.signals import notify
from horilla.decorators import login_required, manager_can_enter
from base.methods import (
    filtersubordinates,
    is_reportingmanager,
    choosesubordinates,
    get_key_instances,
)
from employee.models import Employee
from attendance.models import Attendance
from attendance.forms import AttendanceRequestForm, NewRequestForm
from attendance.methods.differentiate import get_diff_dict
from attendance.views.views import paginator_qry
from attendance.filters import AttendanceFilters, AttendanceRequestReGroup
from base.methods import closest_numbers


def get_employee_last_name(attendance):
    """
    This method is used to return the last name
    """
    if attendance.employee_id.employee_last_name:
        return attendance.employee_id.employee_last_name
    return ""


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
    requests = AttendanceFilters(request.GET, requests).qs
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(Attendance, data_dict)

    keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
    for key in keys_to_remove:
        data_dict.pop(key)
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
    requests_ids = json.dumps(
        [instance.id for instance in paginator_qry(requests, None).object_list]
    )
    attendances_ids = json.dumps(
        [instance.id for instance in paginator_qry(attendances, None).object_list]
    )
    return render(
        request,
        template,
        {
            "requests": paginator_qry(requests, None),
            "attendances": paginator_qry(attendances, None),
            "requests_ids": requests_ids,
            "attendances_ids": attendances_ids,
            "f": filter_obj,
            "filter_dict": data_dict,
            "gp_fields": AttendanceRequestReGroup.fields,
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
    form.fields["employee_id"].initial = request.user.employee_get.id
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
    form.fields["work_type_id"].widget.attrs.update(
        {
            "class": "w-100",
            "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
        }
    )
    form.fields["shift_id"].widget.attrs.update(
        {
            "class": "w-100",
            "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
        }
    )
    if request.method == "POST":
        form = AttendanceRequestForm(request.POST, instance=copy.copy(attendance))
        form.fields["work_type_id"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
            }
        )
        form.fields["shift_id"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
            }
        )
        work_type_id = form.data["work_type_id"]
        shift_id = form.data["shift_id"]
        if work_type_id is None or not len(work_type_id):
            form.add_error("work_type_id", "This field is required")
        if shift_id is None or not len(shift_id):
            form.add_error("shift_id", "This field is required")
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
                instance.is_validate_request_approved = False
                instance.is_validate_request = True
                instance.save()
            messages.success(request, "Attendance update request created.")
            employee = attendance.employee_id
            if attendance.employee_id.employee_work_info.reporting_manager_id:
                reporting_manager = (
                    attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                )
                user_last_name = get_employee_last_name(attendance)
                notify.send(
                    request.user,
                    recipient=reporting_manager,
                    verb=f"{employee.employee_first_name} {user_last_name}'s\
                          attendance update request for {attendance.attendance_date} is created",
                    verb_ar=f"تم إنشاء طلب تحديث الحضور لـ {employee.employee_first_name} \
                        {user_last_name }في {attendance.attendance_date}",
                    verb_de=f"Die Anfrage zur Aktualisierung der Anwesenheit von \
                        {employee.employee_first_name} {user_last_name} \
                            für den {attendance.attendance_date} wurde erstellt",
                    verb_es=f"Se ha creado la solicitud de actualización de asistencia para {employee.employee_first_name}\
                          {user_last_name} el {attendance.attendance_date}",
                    verb_fr=f"La demande de mise à jour de présence de {employee.employee_first_name}\
                          {user_last_name} pour le {attendance.attendance_date} a été créée",
                    redirect=f"/attendance/request-attendance-view?search={employee}&attendance_date={attendance.attendance_date}",
                    icon="checkmark-circle-outline",
                )
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
    requests_ids_json = request.GET["requests_ids"]

    previous_instance_id, next_instance_id = closest_numbers(
        json.loads(requests_ids_json), attendance_id
    )
    return render(
        request,
        "requests/attendance/individual_view.html",
        {
            "data": get_diff_dict(first_dict, other_dict, Attendance),
            "attendance": attendance,
            "previous": previous_instance_id,
            "next": next_instance_id,
            "requests_ids": requests_ids_json,
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
        requested_data["attendance_clock_out"] = (
            None
            if requested_data["attendance_clock_out"] == "None"
            else requested_data["attendance_clock_out"]
        )
        requested_data["attendance_clock_out_date"] = (
            None
            if requested_data["attendance_clock_out_date"] == "None"
            else requested_data["attendance_clock_out_date"]
        )
        Attendance.objects.filter(id=attendance_id).update(**requested_data)
        # DUE TO AFFECT THE OVERTIME CALCULATION ON SAVE METHOD, SAVE THE INSTANCE ONCE MORE
        attendance = Attendance.objects.get(id=attendance_id)
        attendance.save()
    messages.success(request, "Attendance request has been approved")
    employee = attendance.employee_id
    notify.send(
        request.user,
        recipient=employee.employee_user_id,
        verb=f"Your attendance request for \
            {attendance.attendance_date} is validated",
        verb_ar=f"تم التحقق من طلب حضورك في تاريخ \
            {attendance.attendance_date}",
        verb_de=f"Ihr Anwesenheitsantrag für das Datum \
            {attendance.attendance_date} wurde bestätigt",
        verb_es=f"Se ha validado su solicitud de asistencia \
            para la fecha {attendance.attendance_date}",
        verb_fr=f"Votre demande de présence pour la date \
            {attendance.attendance_date} est validée",
        redirect=f"/attendance/request-attendance-view?search={employee}&attendance_date={attendance.attendance_date}",
        icon="checkmark-circle-outline",
    )
    if attendance.employee_id.employee_work_info.reporting_manager_id:
        reporting_manager = (
            attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
        )
        user_last_name = get_employee_last_name(attendance)
        notify.send(
            request.user,
            recipient=reporting_manager,
            verb=f"{employee.employee_first_name} {user_last_name}'s\
                  attendance request for {attendance.attendance_date} is validated",
            verb_ar=f"تم التحقق من طلب الحضور لـ {employee.employee_first_name} \
                {user_last_name} في {attendance.attendance_date}",
            verb_de=f"Die Anwesenheitsanfrage von {employee.employee_first_name} \
                {user_last_name} für den {attendance.attendance_date} wurde validiert",
            verb_es=f"Se ha validado la solicitud de asistencia de \
                {employee.employee_first_name} {user_last_name} para el {attendance.attendance_date}",
            verb_fr=f"La demande de présence de {employee.employee_first_name} \
                {user_last_name} pour le {attendance.attendance_date} a été validée",
            redirect=f"/attendance/request-attendance-view?search={employee}&attendance_date={attendance.attendance_date}",
            icon="checkmark-circle-outline",
        )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


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
        employee = attendance.employee_id
        notify.send(
            request.user,
            recipient=employee.employee_user_id,
            verb=f"Your attendance request for {attendance.attendance_date} is cancelled",
            verb_ar=f"تم إلغاء طلب حضورك في تاريخ {attendance.attendance_date}",
            verb_de=f"Ihr Antrag auf Teilnahme am {attendance.attendance_date} wurde storniert",
            verb_es=f"Se ha cancelado su solicitud de asistencia para el {attendance.attendance_date}",
            verb_fr=f"Votre demande de participation pour le {attendance.attendance_date} a été annulée",
            redirect="/attendance/request-attendance-view",
            icon="close-circle-outline",
        )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


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
        form = AttendanceRequestForm(request.POST, instance=copy.copy(attendance))
        if form.is_valid():
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
                instance.is_validate_request_approved = False
                instance.is_validate_request = True
                instance.save()
            return HttpResponse(
                f"""
                                <script>
                                $('#editValidateAttendanceRequest').removeClass('oh-modal--show');
                                $('[data-target="#validateAttendanceRequest"][data-attendance-id={attendance.id}]').click();
                                $('#messages').html(
                                `
                                <div class="oh-alert-container">
                                <div class="oh-alert oh-alert--animated oh-alert--success">
                                Attendance request updated.
                                </div>
                                </div>
                                `
                                )
                                </script>
                                """
            )
    return render(request, "requests/attendance/update_form.html", {"form": form})
