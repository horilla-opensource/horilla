from collections import defaultdict
import contextlib
from urllib.parse import parse_qs
from django.shortcuts import render, redirect
from horilla.decorators import login_required, hx_request_required
from .forms import *
from .models import *
from django.http import JsonResponse, HttpResponse
from employee.models import Employee
from .filters import *
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta, date
from django.utils import timezone
from base.models import *
from .methods import (
    calculate_requested_days,
    leave_requested_dates,
    holiday_dates_list,
    company_leave_dates_list,
)
import random
from django.core.paginator import Paginator
from django.db.models.functions import TruncYear
from horilla.decorators import permission_required
from horilla.decorators import manager_can_enter
from base.methods import filtersubordinates, choosesubordinates, get_key_instances
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from notifications.signals import notify
from django.db.models import ProtectedError


@login_required
@permission_required("leave.add_leavetype")
def leave_type_creation(request):
    """
    function used to create leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave type creation template
    POST : return leave view
    """
    form = LeaveTypeForm()
    if request.method == "POST":
        form = LeaveTypeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("New leave type Created.."))
            return redirect(leave_type_view)
    return render(request, "leave/leave_type_creation.html", {"form": form})


def paginator_qry(qryset, page_number):
    """
    function used to paginate query set
    """
    paginator = Paginator(qryset, 25)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@permission_required("leave.view_leavetype")
def leave_type_view(request):
    """
    function used to view leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave type template
    """
    queryset = LeaveType.objects.all()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    previous_data = request.GET.urlencode()
    leave_type_filter = LeaveTypeFilter()
    if not queryset.exists():
        template_name = "leave/user_leave_type_empty_view.html"
    else:
        template_name = "leave/leave_type_view.html"
    return render(
        request,
        template_name,
        {"leave_types": page_obj, "form": leave_type_filter.form, "pd": previous_data},
    )


@login_required
@hx_request_required
@permission_required("leave.view_leavetype")
def leave_type_filter(request):
    """
    function used to filter view leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave types template
    """
    queryset = LeaveType.objects.all()
    page_number = request.GET.get("page")
    leave_type_filter = LeaveTypeFilter(request.GET, queryset).qs
    page_obj = paginator_qry(leave_type_filter, page_number)
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(LeaveType, data_dict)
    return render(
        request,
        "leave/leave_type/leave_types.html",
        {"leave_types": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


@login_required
@permission_required("leave.update_leavetype")
def leave_type_update(request, id):
    """
    function used to update leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave type id

    Returns:
    GET : return leave type update template
    POST : return leave type view
    """
    leave_type = LeaveType.objects.get(id=id)
    form = UpdateLeaveTypeForm(instance=leave_type)
    if request.method == "POST":
        form_data = UpdateLeaveTypeForm(
            request.POST, request.FILES, instance=leave_type
        )
        if form_data.is_valid():
            form_data.save()
            messages.info(request, _("Leave type is updated successfully.."))
            return redirect(leave_type_view)
    return render(request, "leave/leave_type_update.html", {"form": form})


@login_required
@permission_required("leave.delete_leavetype")
def leave_type_delete(request, id):
    """
    function used to delete leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave type id

    Returns:
    GET : return leave type view template
    """
    try:
        LeaveType.objects.get(id=id).delete()
        messages.error(request, _("Leave type deleted successfully.."))
    except LeaveType.DoesNotExist:
        messages.error(request, _("Leave type not found."))
    except ProtectedError as e:
        models_verbose_name_sets = set()
        for obj in e.protected_objects:
            models_verbose_name_sets.add(__(obj._meta.verbose_name))
        models_verbose_name_str = (",").join(models_verbose_name_sets)
        messages.error(
            request,
            _(
                "This leave types are already in use for {}".format(
                    models_verbose_name_str
                )
            ),
        )
    return redirect(leave_type_view)


@login_required
@hx_request_required
@manager_can_enter("leave.add_leaverequest")
def leave_request_creation(request, type_id=None, emp_id=None):
    """
    function used to create leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave request form template
    POST : return leave request view
    """
    form = LeaveRequestCreationForm()
    if type_id and emp_id:
        initial_data = {
            "leave_type_id": type_id,
            "employee_id": emp_id,
        }
        form = LeaveRequestCreationForm(initial=initial_data)
    form = choosesubordinates(request, form, "leave.add_leaverequest")
    if request.method == "POST":
        form = LeaveRequestCreationForm(request.POST, request.FILES)
        form = choosesubordinates(request, form, "leave.add_leaverequest")
        if form.is_valid():
            leave_request = form.save()
            if leave_request.leave_type_id.require_approval == "no":
                employee_id = leave_request.employee_id
                leave_type_id = leave_request.leave_type_id
                available_leave = AvailableLeave.objects.get(
                    leave_type_id=leave_type_id, employee_id=employee_id
                )
                if leave_request.requested_days > available_leave.available_days:
                    leave = (
                        leave_request.requested_days - available_leave.available_days
                    )
                    leave_request.approved_available_days = (
                        available_leave.available_days
                    )
                    available_leave.available_days = 0
                    available_leave.carryforward_days = (
                        available_leave.carryforward_days - leave
                    )
                    leave_request.approved_carryforward_days = leave
                else:
                    available_leave.available_days = (
                        available_leave.available_days - leave_request.requested_days
                    )
                    leave_request.approved_available_days = leave_request.requested_days
                leave_request.status = "approved"
                leave_request.created_by = request.user.employee_get
                available_leave.save()
            leave_request.save()
            messages.success(request, _("Leave request created successfully.."))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"New leave request created for {leave_request.employee_id}.",
                    verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                    verb_de=f"Neuer Urlaubsantrag erstellt für {leave_request.employee_id}.",
                    verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                    verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                    icon="people-circle",
                    redirect="/leave/request-view",
                )
            response = render(request, "leave/leave_request_form.html", {"form": form})
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "leave/leave_request_form.html", {"form": form})


@login_required
@manager_can_enter("leave.view_leaverequest")
def leave_request_view(request):
    """
    function used to view leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave request view template
    """
    queryset = LeaveRequest.objects.all()
    queryset = filtersubordinates(request, queryset, "leave.view_leaverequest")
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    leave_request_filter = LeaveRequestFilter()
    requests = queryset.filter(status="requested").count()
    approved_requests = queryset.filter(status="approved").count()
    rejected_requests = queryset.filter(status="cancelled").count()
    previous_data = request.GET.urlencode()
    return render(
        request,
        "leave/request_view.html",
        {
            "leave_requests": page_obj,
            "pd": previous_data,
            "form": leave_request_filter.form,
            "requests": requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.view_leaverequest")
def leave_request_filter(request):
    """
    function used to filter leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave request view template
    """
    previous_data = request.GET.urlencode()
    queryset = LeaveRequest.objects.all()
    queryset = filtersubordinates(request, queryset, "leave.view_leaverequest")
    leave_request_filter = LeaveRequestFilter(request.GET, queryset).qs
    page_number = request.GET.get("page")
    page_obj = paginator_qry(leave_request_filter, page_number)
    data_dict = []
    if not request.GET.get("dashboard"):
        data_dict = parse_qs(previous_data)
        get_key_instances(LeaveRequest, data_dict)
    if "status" in data_dict:
        status_list = data_dict["status"]
        if len(status_list) > 1:
            data_dict["status"] = [status_list[-1]]
    return render(
        request,
        "leave/leave_request/leave_requests.html",
        {
            "leave_requests": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "dashboard": request.GET.get("dashboard"),
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.update_leaverequest")
def leave_request_update(request, id):
    """
    function used to update leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET : return leave request update template
    POST : return leave request view
    """
    leave_request = LeaveRequest.objects.get(id=id)
    form = LeaveRequestUpdationForm(instance=leave_request)
    form = choosesubordinates(request, form, "leave.add_leaverequest")
    if request.method == "POST":
        form = LeaveRequestUpdationForm(
            request.POST, request.FILES, instance=leave_request
        )
        form = choosesubordinates(request, form, "leave.add_leaverequest")
        if form.is_valid():
            leave_request = form.save()
            messages.info(request, _("Leave request is updated successfully.."))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"Leave request updated for {leave_request.employee_id}.",
                    verb_ar=f"تم تحديث طلب الإجازة لـ {leave_request.employee_id}.",
                    verb_de=f"Urlaubsantrag aktualisiert für {leave_request.employee_id}.",
                    verb_es=f"Solicitud de permiso actualizada para {leave_request.employee_id}.",
                    verb_fr=f"Demande de congé mise à jour pour {leave_request.employee_id}.",
                    icon="people-circle",
                    redirect="/leave/request-view",
                )
            response = render(
                request, "leave/request_update_form.html", {"form": form, "id": id}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "leave/request_update_form.html", {"form": form, "id": id})


@login_required
@manager_can_enter("leave.delete_leaverequest")
def leave_request_delete(request, id):
    """
    function used to delete leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET : return leave request view template
    """
    try:
        LeaveRequest.objects.get(id=id).delete()
        messages.success(request, _("Leave request deleted successfully.."))
    except LeaveRequest.DoesNotExist:
        messages.error(request, _("Leave request not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    return redirect(leave_request_view)


@login_required
@manager_can_enter("leave.update_leaverequest")
def leave_request_approve(request, id, emp_id=None):
    """
    function used to approve a leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id
    emp_id : employee id if the approval operation comes from "/employee/employee-view/{employee_id}/" template.


    Returns:
    GET : If `emp_id` is provided, it returns to the "/employee/employee-view/{employee_id}/" template after approval.
          Otherwise, it returns to the default leave request view template.
    """
    leave_request = LeaveRequest.objects.get(id=id)
    employee_id = leave_request.employee_id
    leave_type_id = leave_request.leave_type_id
    available_leave = AvailableLeave.objects.get(
        leave_type_id=leave_type_id, employee_id=employee_id
    )
    total_available_leave = (
        available_leave.available_days + available_leave.carryforward_days
    )
    if total_available_leave >= leave_request.requested_days:
        if leave_request.requested_days > available_leave.available_days:
            leave = leave_request.requested_days - available_leave.available_days
            leave_request.approved_available_days = available_leave.available_days
            available_leave.available_days = 0
            available_leave.carryforward_days = (
                available_leave.carryforward_days - leave
            )
            leave_request.approved_carryforward_days = leave
        else:
            temp = available_leave.available_days
            available_leave.available_days = temp - leave_request.requested_days
            leave_request.approved_available_days = leave_request.requested_days
        leave_request.status = "approved"
        available_leave.save()
        leave_request.save()
        messages.success(request, _("Leave request approved successfully.."))
        with contextlib.suppress(Exception):
            notify.send(
                request.user.employee_get,
                recipient=leave_request.employee_id.employee_user_id,
                verb="Your Leave request has been approved",
                verb_ar="تمت الموافقة على طلب الإجازة الخاص بك",
                verb_de="Ihr Urlaubsantrag wurde genehmigt",
                verb_es="Se ha aprobado su solicitud de permiso",
                verb_fr="Votre demande de congé a été approuvée",
                icon="people-circle",
                redirect="/leave/user-request-view",
            )
    else:
        messages.error(
            request,
            f"{employee_id} dont have enough leave days to approve the request..",
        )
    if emp_id is not None:
        employee_id = emp_id
        return redirect(f"/employee/employee-view/{employee_id}/")
    return redirect(leave_request_view)


@login_required
@manager_can_enter("leave.update_leaverequest")
def leave_request_cancel(request, id, emp_id=None):
    """
    function used to cancel leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id
    emp_id : employee id if the cancel operation comes from "/employee/employee-view/{employee_id}/" template.

    Returns:
    GET : If `emp_id` is provided, it returns to the "/employee/employee-view/{employee_id}/" template after cancel.
          Otherwise, it returns to the default leave request view template.

    """
    leave_request = LeaveRequest.objects.get(id=id)
    employee_id = leave_request.employee_id
    leave_type_id = leave_request.leave_type_id
    available_leave = AvailableLeave.objects.get(
        leave_type_id=leave_type_id, employee_id=employee_id
    )
    available_leave.available_days += leave_request.approved_available_days
    available_leave.carryforward_days += leave_request.approved_carryforward_days
    leave_request.approved_available_days = 0
    leave_request.approved_carryforward_days = 0
    leave_request.status = "cancelled"
    leave_request.save()
    available_leave.save()
    messages.success(request, _("Leave request cancelled successfully.."))
    with contextlib.suppress(Exception):
        notify.send(
            request.user.employee_get,
            recipient=leave_request.employee_id.employee_user_id,
            verb="Your Leave request has been cancelled",
            verb_ar="تم إلغاء طلب الإجازة الخاص بك",
            verb_de="Ihr Urlaubsantrag wurde storniert",
            verb_es="Se ha cancelado su solicitud de permiso",
            verb_fr="Votre demande de congé a été annulée",
            icon="people-circle",
            redirect="/leave/user-request-view",
        )
    if emp_id is not None:
        employee_id = emp_id
        return redirect(f"/employee/employee-view/{employee_id}/")
    return redirect(leave_request_view)


@login_required
@manager_can_enter("leave.view_leaverequest")
def one_request_view(request, id):
    """
    function used to view one leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return one leave request view template
    """
    leave_request = LeaveRequest.objects.get(id=id)
    return render(
        request, "leave/one_request_view.html", {"leave_request": leave_request}
    )


@login_required
@hx_request_required
@manager_can_enter("leave.add_availableleave")
def leave_assign_one(request, id):
    """
    function used to assign leave type to employees.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave type id

    Returns:
    GET : return leave type assign form template
    POST : return leave type assigned  view
    """
    form = LeaveOneAssignForm()
    form = choosesubordinates(request, form, "leave.add_availableleave")
    if request.method == "POST":
        leave_type = LeaveType.objects.get(id=id)
        employee_ids = request.POST.getlist("employee_id")
        for employee_id in employee_ids:
            employee = Employee.objects.get(id=employee_id)
            if not AvailableLeave.objects.filter(
                leave_type_id=leave_type, employee_id=employee
            ).exists():
                AvailableLeave(
                    leave_type_id=leave_type,
                    employee_id=employee,
                    available_days=leave_type.total_days,
                ).save()
                messages.success(request, _("Leave type assign is successfull.."))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=employee.employee_user_id,
                        verb="New leave type is assigned to you",
                        verb_ar="تم تعيين نوع إجازة جديد لك",
                        verb_de="Ihnen wurde ein neuer Urlaubstyp zugewiesen",
                        verb_es="Se le ha asignado un nuevo tipo de permiso",
                        verb_fr="Un nouveau type de congé vous a été attribué",
                        icon="people-circle",
                        redirect="/leave/user-leave",
                    )
            else:
                messages.info(
                    request, _("leave type is already assigned to the employee..")
                )
        response = render(
            request, "leave/leave_assign_one_form.html", {"form": form, "id": id}
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location.reload();</script>"
        )
    return render(request, "leave/leave_assign_one_form.html", {"form": form, "id": id})


@login_required
@manager_can_enter("leave.view_availableleave")
def leave_assign_view(request):
    """
    function used to view assigned employee leaves.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave assigned view template
    """
    queryset = AvailableLeave.objects.all()
    queryset = filtersubordinates(request, queryset, "leave.view_availableleave")
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    assigned_leave_filter = AssignedLeaveFilter()
    return render(
        request,
        "leave/assign_view.html",
        {
            "available_leaves": page_obj,
            "form": assigned_leave_filter.form,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.view_availableleave")
def leave_assign_filter(request):
    """
    function used to filter assign leave type to employees.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave type assigned view template
    """
    queryset = AvailableLeave.objects.all()
    queryset = filtersubordinates(request, queryset, "leave.view_availableleave")
    assigned_leave_filter = AssignedLeaveFilter(request.GET, queryset).qs
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(assigned_leave_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(AvailableLeave, data_dict)
    return render(
        request,
        "leave/leave_assign/assigned_leave.html",
        {"available_leaves": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


# Function to assign the created leave type to employee
@login_required
@hx_request_required
@manager_can_enter("leave.add_availableleave")
def leave_assign(request):
    """
    function used to assign multiple leave types to employees.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return multiple leave type assign form template
    POST : return leave type assigned  view
    """
    form = AvailableLeaveForm()
    form = choosesubordinates(request, form, "leave.add_availableleave")
    if request.method == "POST":
        leave_type_ids = request.POST.getlist("leave_type_id")
        employee_ids = request.POST.getlist("employee_id")
        for employee_id in employee_ids:
            if employee_id != "":
                for leave_type_id in leave_type_ids:
                    if leave_type_id != "":
                        employee = Employee.objects.get(id=employee_id)
                        leave_type = LeaveType.objects.get(id=leave_type_id)
                        if not AvailableLeave.objects.filter(
                            leave_type_id=leave_type, employee_id=employee
                        ).exists():
                            AvailableLeave(
                                leave_type_id=leave_type,
                                employee_id=employee,
                                available_days=leave_type.total_days,
                            ).save()
                            messages.success(
                                request, _("Leave type assign is successfull..")
                            )
                            with contextlib.suppress(Exception):
                                notify.send(
                                    request.user.employee_get,
                                    recipient=employee.employee_user_id,
                                    verb="New leave type is assigned to you",
                                    verb_ar="تم تعيين نوع إجازة جديد لك",
                                    verb_de="Ihnen wurde ein neuer Urlaubstyp zugewiesen",
                                    verb_es="Se le ha asignado un nuevo tipo de permiso",
                                    verb_fr="Un nouveau type de congé vous a été attribué",
                                    icon="people-circle",
                                    redirect="/leave/user-leave",
                                )
                        else:
                            messages.info(
                                request,
                                _("Leave type is already assigned to the employee.."),
                            )
        response = render(
            request, "leave/leave_assign_form.html", {"form": form, "id": id}
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location. reload();</script>"
        )
    return render(request, "leave/leave_assign_form.html", {"form": form})


@login_required
@hx_request_required
@manager_can_enter("leave.update_availableleave")
def available_leave_update(request, id):
    """
    function used to update available leave of an assigned leave type of an employee.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : available leave id

    Returns:
    GET : return available leave update form template
    POST : return leave type assigned  view
    """
    leave_assign = AvailableLeave.objects.get(id=id)
    form = AvailableLeaveUpdateForm(instance=leave_assign)
    if request.method == "POST":
        form = AvailableLeaveUpdateForm(request.POST, instance=leave_assign)
        if form.is_valid():
            available_leave = form.save()
            messages.info(request, _("Available leaves updated successfully..."))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=available_leave.employee_id.employee_user_id,
                    verb=f"Your {available_leave.leave_type_id} leave type updated.",
                    verb_ar=f"تم تحديث نوع الإجازة {available_leave.leave_type_id} الخاص بك.",
                    verb_de=f"Ihr Urlaubstyp {available_leave.leave_type_id} wurde aktualisiert.",
                    verb_es=f"Se ha actualizado su tipo de permiso {available_leave.leave_type_id}.",
                    verb_fr=f"Votre type de congé {available_leave.leave_type_id} a été mis à jour.",
                    icon="people-circle",
                    redirect="/leave/user-leave",
                )
        response = render(
            request, "leave/available_update_form.html", {"form": form, "id": id}
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location. reload();</script>"
        )
    return render(request, "leave/available_update_form.html", {"form": form, "id": id})


@login_required
@manager_can_enter("leave.delete_availableleave")
def leave_assign_delete(request, id):
    """
    function used to delete assign leave type of an employee.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : available leave id

    Returns:
    GET : return leave type assigned view template
    """
    try:
        AvailableLeave.objects.get(id=id).delete()
        messages.success(request, _("Assigned leave is successfully deleted."))
    except AvailableLeave.DoesNotExist:
        messages.error(request, _("Assigned leave not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    return redirect(leave_assign_view)


@login_required
@hx_request_required
@permission_required("leave.add_holiday")
def holiday_creation(request):
    """
    function used to create holidays.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return holiday creation form template
    POST : return holiday view template
    """
    form = HolidayForm()
    if request.method == "POST":
        form = HolidayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("New holiday created successfully.."))
            response = render(request, "leave/holiday_form.html", {"form": form})
            return HttpResponse(
                response.content.decode("utf-8")
                + "<script>location. reload();</script>"
            )
    return render(request, "leave/holiday_form.html", {"form": form})


@login_required
@permission_required("leave.view_holiday")
def holiday_view(request):
    """
    function used to view holidays.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return holiday view  template
    """
    queryset = Holiday.objects.all()
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    holiday_filter = HolidayFilter()
    return render(
        request,
        "leave/holiday_view.html",
        {"holidays": page_obj, "form": holiday_filter.form, "pd": previous_data},
    )


@login_required
@hx_request_required
@permission_required("leave.view_holiday")
def holiday_filter(request):
    """
    function used to filter holidays.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return holiday view template
    """
    queryset = Holiday.objects.all()
    previous_data = request.GET.urlencode()
    holiday_filter = HolidayFilter(request.GET, queryset).qs
    page_number = request.GET.get("page")
    page_obj = paginator_qry(holiday_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(Holiday, data_dict)
    return render(
        request,
        "leave/holiday/holiday.html",
        {"holidays": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


@login_required
@hx_request_required
@permission_required("leave.update_holiday")
def holiday_update(request, id):
    """
    function used to update holiday.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : holiday id

    Returns:
    GET : return holiday update form template
    POST : return holiday view template
    """
    holiday = Holiday.objects.get(id=id)
    form = HolidayForm(instance=holiday)
    if request.method == "POST":
        form = HolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            form.save()
            messages.info(request, _("Holiday updated successfully.."))
            response = render(
                request, "leave/holiday_update_form.html", {"form": form, "id": id}
            )
            return HttpResponse(
                response.content.decode("utf-8")
                + "<script>location. reload();</script>"
            )
    return render(request, "leave/holiday_update_form.html", {"form": form, "id": id})


@login_required
@permission_required("leave.delete_holiday")
def holiday_delete(request, id):
    """
    function used to delete holiday.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : holiday id

    Returns:
    GET : return holiday view template
    """
    try:
        Holiday.objects.get(id=id).delete()
        messages.success(request, _("Holiday deleted successfully.."))
    except Holiday.DoesNotExist:
        messages.error(request, _("Holiday not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    return redirect(holiday_view)


@login_required
@hx_request_required
@permission_required("leave.add_companyleave")
def company_leave_creation(request):
    """
    function used to create company leave.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return company leave creation form template
    POST : return company leave view template
    """
    form = CompanyLeaveForm()
    if request.method == "POST":
        form = CompanyLeaveForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("New company leave created successfully.."))
            response = render(
                request, "leave/company_leave_creation_form.html", {"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8")
                + "<script>location. reload();</script>"
            )
    return render(request, "leave/company_leave_creation_form.html", {"form": form})


@login_required
@permission_required("leave.view_companyleave")
def company_leave_view(request):
    """
    function used to view company leave.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return company leave view template
    """
    queryset = CompanyLeave.objects.all()
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    company_leave_filter = CompanyLeaveFilter()
    return render(
        request,
        "leave/company_leave_view.html",
        {
            "company_leaves": page_obj,
            "weeks": WEEKS,
            "week_days": WEEK_DAYS,
            "form": company_leave_filter.form,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
@permission_required("leave.view_companyleave")
def company_leave_filter(request):
    """
    function used to filter company leave.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return company leave view template
    """
    queryset = CompanyLeave.objects.all()
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    company_leave_filter = CompanyLeaveFilter(request.GET, queryset).qs
    page_obj = paginator_qry(company_leave_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(CompanyLeave, data_dict)

    return render(
        request,
        "leave/company_leave/company_leave.html",
        {
            "company_leaves": page_obj,
            "weeks": WEEKS,
            "week_days": WEEK_DAYS,
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@hx_request_required
@permission_required("leave.update_companyleave")
def company_leave_update(request, id):
    """
    function used to update company leave.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : company leave id

    Returns:
    GET : return company leave update form template
    POST : return company leave view template
    """
    company_leave = CompanyLeave.objects.get(id=id)
    form = CompanyLeaveForm(instance=company_leave)
    if request.method == "POST":
        form = CompanyLeaveForm(request.POST, instance=company_leave)
        if form.is_valid():
            form.save()
            messages.info(request, _("Company leave updated successfully.."))
            response = render(
                request,
                "leave/company_leave_update_form.html",
                {"form": form, "id": id},
            )
            return HttpResponse(
                response.content.decode("utf-8")
                + "<script>location. reload();</script>"
            )
    return render(
        request, "leave/company_leave_update_form.html", {"form": form, "id": id}
    )


@login_required
@permission_required("leave.delete_companyleave")
def company_leave_delete(request, id):
    """
    function used to create company leave.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return company leave creation form template
    POST : return company leave view template
    """
    try:
        CompanyLeave.objects.get(id=id).delete()
        messages.success(request, _("Company leave deleted successfully.."))
    except CompanyLeave.DoesNotExist:
        messages.error(request, _("Company leave not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    return redirect(company_leave_view)


@login_required
@hx_request_required
def user_leave_request(request, id):
    """
    function used to create user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave type id

    Returns:
    GET : return user leave request creation form template
    POST : user my leave view template
    """
    employee = request.user.employee_get
    form = UserLeaveRequestForm(employee=employee)
    leave_type = LeaveType.objects.get(id=id)
    if request.method == "POST":
        form = UserLeaveRequestForm(request.POST, request.FILES)
        start_date = datetime.strptime(request.POST.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(request.POST.get("end_date"), "%Y-%m-%d")
        attachment = request.FILES.get("attachment")
        start_date_breakdown = request.POST.get("start_date_breakdown")
        end_date_breakdown = request.POST.get("end_date_breakdown")
        available_leave = AvailableLeave.objects.get(
            employee_id=employee, leave_type_id=leave_type
        )
        available_total_leave = (
            available_leave.available_days + available_leave.carryforward_days
        )
        requested_days = calculate_requested_days(
            start_date, end_date, start_date_breakdown, end_date_breakdown
        )
        requested_dates = leave_requested_dates(start_date, end_date)
        requested_dates = [date.date() for date in requested_dates]
        holidays = Holiday.objects.all()
        holiday_dates = holiday_dates_list(holidays)
        company_leaves = CompanyLeave.objects.all()
        company_leave_dates = company_leave_dates_list(company_leaves, start_date)
        if leave_type.require_attachment == "yes":
            if attachment is None:
                form.add_error(
                    None, _("An attachment is required for this leave request")
                )
        if (
            leave_type.exclude_company_leave == "yes"
            and leave_type.exclude_holiday == "yes"
        ):
            total_leaves = list(set(holiday_dates + company_leave_dates))
            total_leave_count = sum(
                requested_date in total_leaves for requested_date in requested_dates
            )
            requested_days = requested_days - total_leave_count
        else:
            holiday_count = 0
            if leave_type.exclude_holiday == "yes":
                for requested_date in requested_dates:
                    if requested_date in holiday_dates:
                        holiday_count += 1
                requested_days = requested_days - holiday_count
            if leave_type.exclude_company_leave == "yes":
                company_leave_count = sum(
                    requested_date in company_leave_dates
                    for requested_date in requested_dates
                )
                requested_days = requested_days - company_leave_count

        overlapping_requests = LeaveRequest.objects.filter(
            employee_id=employee, start_date__lte=end_date, end_date__gte=start_date
        ).exclude(status="cancelled")
        if overlapping_requests.exists():
            form.add_error(
                None, _("There is already a leave request for this date range..")
            )
        elif requested_days <= available_total_leave:
            if form.is_valid():
                leave_request = form.save(commit=False)
                leave_request.leave_type_id = leave_type
                leave_request.employee_id = employee
                leave_request.save()
                if leave_request.leave_type_id.require_approval == "no":
                    employee_id = leave_request.employee_id
                    leave_type_id = leave_request.leave_type_id
                    available_leave = AvailableLeave.objects.get(
                        leave_type_id=leave_type_id, employee_id=employee_id
                    )
                    if leave_request.requested_days > available_leave.available_days:
                        leave = (
                            leave_request.requested_days
                            - available_leave.available_days
                        )
                        leave_request.approved_available_days = (
                            available_leave.available_days
                        )
                        available_leave.available_days = 0
                        available_leave.carryforward_days = (
                            available_leave.carryforward_days - leave
                        )
                        leave_request.approved_carryforward_days = leave
                    else:
                        available_leave.available_days = (
                            available_leave.available_days
                            - leave_request.requested_days
                        )
                        leave_request.approved_available_days = (
                            leave_request.requested_days
                        )
                    leave_request.status = "approved"
                    leave_request.created_by = employee
                    available_leave.save()
                leave_request.save()
                messages.success(request, _("Leave request created successfully.."))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb="You have a new leave request to validate.",
                        verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                        verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                        verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                        verb_fr="Vous avez une nouvelle demande de congé à valider.",
                        icon="people-circle",
                        redirect="/leave/user-request-view",
                    )
                response = render(
                    request, "leave/user_request_form.html", {"form": form, "id": id}
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location. reload();</script>"
                )
        else:
            form.add_error(
                None, _("You dont have enough leave days to make the request..")
            )
    return render(
        request,
        "leave/user_request_form.html",
        {"form": form, "id": id, "leave_type": leave_type},
    )


@login_required
@hx_request_required
def user_request_update(request, id):
    """
    function used to update user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET : return user leave request update form template
    POST : return user leave request view template
    """
    leave_request = LeaveRequest.objects.get(id=id)
    try:
        if request.user.employee_get == leave_request.employee_id:
            form = UserLeaveRequestForm(instance=leave_request)
            if request.method == "POST":
                form = UserLeaveRequestForm(
                    request.POST, request.FILES, instance=leave_request
                )
                if form.is_valid():
                    leave_request = form.save(commit=False)
                    start_date = leave_request.start_date
                    end_date = leave_request.end_date
                    start_date_breakdown = leave_request.start_date_breakdown
                    end_date_breakdown = leave_request.end_date_breakdown
                    leave_type = leave_request.leave_type_id
                    employee = request.user.employee_get
                    available_leave = AvailableLeave.objects.get(
                        employee_id=employee, leave_type_id=leave_type
                    )
                    available_total_leave = (
                        available_leave.available_days
                        + available_leave.carryforward_days
                    )
                    requested_days = calculate_requested_days(
                        start_date, end_date, start_date_breakdown, end_date_breakdown
                    )
                    requested_dates = leave_requested_dates(start_date, end_date)
                    holidays = Holiday.objects.all()
                    holiday_dates = holiday_dates_list(holidays)
                    company_leaves = CompanyLeave.objects.all()
                    company_leave_dates = company_leave_dates_list(
                        company_leaves, start_date
                    )
                    if (
                        leave_type.exclude_company_leave == "yes"
                        and leave_type.exclude_holiday == "yes"
                    ):
                        total_leaves = list(set(holiday_dates + company_leave_dates))
                        total_leave_count = sum(
                            requested_date in total_leaves
                            for requested_date in requested_dates
                        )
                        requested_days = requested_days - total_leave_count
                    else:
                        holiday_count = 0
                        if leave_type.exclude_holiday == "yes":
                            for requested_date in requested_dates:
                                if requested_date in holiday_dates:
                                    holiday_count += 1
                            requested_days = requested_days - holiday_count
                        if leave_type.exclude_company_leave == "yes":
                            company_leave_count = sum(
                                requested_date in company_leave_dates
                                for requested_date in requested_dates
                            )
                            requested_days = requested_days - company_leave_count
                    if requested_days <= available_total_leave:
                        leave_request.save()
                        messages.info(
                            request, _("Leave request updated successfully..")
                        )
                        response = render(
                            request,
                            "leave/user_request_update.html",
                            {"form": form, "id": id},
                        )
                        return HttpResponse(
                            response.content.decode("utf-8")
                            + "<script>location. reload();</script>"
                        )
                    else:
                        form.add_error(
                            None,
                            _("You dont have enough leave days to make the request.."),
                        )
            return render(
                request, "leave/user_request_update.html", {"form": form, "id": id}
            )
    except Exception as e:
        messages.error(request, _("User has no leave request.."))


@login_required
def user_request_delete(request, id):
    """
    function used to delete user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET : return user leave request view template
    """
    try:
        leave_request = LeaveRequest.objects.get(id=id)
        if request.user.employee_get == leave_request.employee_id:
            LeaveRequest.objects.get(id=id).delete()
            messages.success(request, _("Leave request deleted successfully.."))
    except LeaveRequest.DoesNotExist:
        messages.error(request, _("User has no leave request.."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    return redirect(user_request_view)


@login_required
def user_leave_view(request):
    """
    function used to view user assigned leave types.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return user assigned leave types view template
    """
    try:
        employee = request.user.employee_get
        queryset = employee.available_leave.all()
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        page_obj = paginator_qry(queryset, page_number)
        assigned_leave_filter = AssignedLeaveFilter()
        if not queryset.exists():
            template_name = "leave/user_leave_empty_view.html"
        else:
            template_name = "leave/user_leave_view.html"
        return render(
            request,
            template_name,
            {
                "user_leaves": page_obj,
                "form": assigned_leave_filter.form,
                "pd": previous_data,
            },
        )
    except Exception:
        messages.error(request, _("User is not an employee.."))
        return redirect("/")


@login_required
@hx_request_required
def user_leave_filter(request):
    """
    function used to filter user assigned leave types.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return user assigned leave types view template
    """
    try:
        employee = request.user.employee_get
        queryset = employee.available_leave.all()
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        assigned_leave_filter = AssignedLeaveFilter(request.GET, queryset).qs
        data_dict = parse_qs(previous_data)
        get_key_instances(AvailableLeave, data_dict)
        page_obj = paginator_qry(assigned_leave_filter, page_number)
        return render(
            request,
            "leave/user_leave/user_leave.html",
            {"user_leaves": page_obj, "pd": previous_data, "filter_dict": data_dict},
        )
    except Exception as e:
        messages.error(request, _("User is not an employee.."))
        return redirect("/")


@login_required
def user_request_view(request):
    """
    function used to view user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return user leave request view template
    """
    try:
        user = request.user.employee_get
        queryset = user.leaverequest_set.all()
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        page_obj = paginator_qry(queryset, page_number)
        user_request_filter = UserLeaveRequestFilter()
        return render(
            request,
            "leave/user_request_view.html",
            {
                "leave_requests": page_obj,
                "form": user_request_filter.form,
                "pd": previous_data,
            },
        )
    except Exception as e:
        messages.error(request, _("User is not an employee.."))
        return redirect("/")


@login_required
@hx_request_required
def user_request_filter(request):
    """
    function used to filter user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return user leave request view template
    """
    try:
        user = request.user.employee_get
        queryset = user.leaverequest_set.all()
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        user_request_filter = UserLeaveRequestFilter(request.GET, queryset).qs
        page_obj = paginator_qry(user_request_filter, page_number)
        data_dict = parse_qs(previous_data)
        get_key_instances(LeaveRequest, data_dict)
        if "status" in data_dict:
            status_list = data_dict["status"]
            if len(status_list) > 1:
                data_dict["status"] = [status_list[-1]]
        return render(
            request,
            "leave/user_requests.html",
            {"leave_requests": page_obj, "pd": previous_data, "filter_dict": data_dict},
        )
    except Exception as e:
        messages.error(request, _("User is not an employee.."))
        return redirect("/")


@login_required
@hx_request_required
def user_request_one(request, id):
    """
    function used to view one user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return one user leave request view template
    """
    leave_request = LeaveRequest.objects.get(id=id)
    try:
        if request.user.employee_get == leave_request.employee_id:
            return render(
                request, "leave/user_request_one.html", {"leave_request": leave_request}
            )
    except Exception as e:
        messages.error(request, _("User has no leave request.."))
        return redirect("/")


@login_required
def employee_leave(request):
    """
    function used to view employees are leave today.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of employee
    """
    today = date.today()
    employees = []
    leave_requests = LeaveRequest.objects.filter(
        Q(start_date__lte=today) & Q(end_date__gte=today) & Q(status="approved")
    )
    for leave_request in leave_requests:
        if leave_request.employee_id.__str__() not in employees:
            employees.append(leave_request.employee_id.__str__())
    return JsonResponse({"employees": employees})


@login_required
def overall_leave(request):
    """
    function used to view overall leave in the company.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, data
    """

    selected = request.GET.get("selected")
    labels = []
    data = []
    departments = Department.objects.all()
    today = date.today()
    today_leave_requests = LeaveRequest.objects.filter(
        Q(start_date__lte=today) & Q(end_date__gte=today) & Q(status="approved")
    )
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    weekly_leave_requests = LeaveRequest.objects.filter(
        status="approved", start_date__lte=end_of_week, end_date__gte=start_of_week
    )
    start_of_month = today.replace(day=1)
    end_of_month = start_of_month.replace(day=28) + timedelta(days=4)
    if end_of_month.month != today.month:
        end_of_month = end_of_month - timedelta(days=end_of_month.day)
    monthly_leave_requests = LeaveRequest.objects.filter(
        status="approved", start_date__lte=end_of_month, end_date__gte=start_of_month
    )
    start_of_year = today.replace(month=1, day=1)
    end_of_year = today.replace(month=12, day=31)
    yearly_leave_requests = (
        LeaveRequest.objects.filter(
            status="approved", start_date__lte=end_of_year, end_date__gte=start_of_year
        )
        .annotate(year=TruncYear("start_date"))
        .filter(year=start_of_year)
    )
    if selected == "month":
        leave_requests = monthly_leave_requests
    elif selected == "week":
        leave_requests = weekly_leave_requests
    elif selected == "year":
        leave_requests = yearly_leave_requests
    else:
        leave_requests = today_leave_requests
    employees = [leave_request.employee_id for leave_request in leave_requests]
    for department in departments:
        labels.append(department.department)
        count = sum(
            employee.employee_work_info.department_id == department
            for employee in employees
        )
        data.append(count)
    return JsonResponse({"labels": labels, "data": data})


@login_required
@permission_required("leave_deleteleaverequest")
def dashboard(request):
    today = date.today()
    leave_requests = LeaveRequest.objects.filter(start_date__month=today.month)
    requested = LeaveRequest.objects.filter(status="requested")
    approved = LeaveRequest.objects.filter(status="approved")
    cancelled = LeaveRequest.objects.filter(status="cancelled")
    holidays = Holiday.objects.filter(start_date__gte=today)
    next_holiday = (
        holidays.order_by("start_date").first() if holidays.exists() else None
    )
    holidays = holidays.filter(
        start_date__gte=today, start_date__month=today.month
    ).order_by("start_date")[1:]

    leave_today = LeaveRequest.objects.filter(
        status="approved", start_date__lte=today, end_date__gte=today
    )

    context = {
        "leave_requests": leave_requests,
        "requested": requested,
        "approved": approved,
        "cancelled": cancelled,
        "next_holiday": next_holiday,
        "holidays": holidays,
        "leave_today_employees": leave_today,
        "dashboard": "dashboard",
    }
    return render(request, "leave/dashboard.html", context)


@login_required
def employee_dashboard(request):
    today = date.today()
    user = Employee.objects.get(employee_user_id=request.user)
    leave_requests = LeaveRequest.objects.filter(employee_id=user)
    requested = leave_requests.filter(status="requested")
    approved = leave_requests.filter(status="approved")
    cancelled = leave_requests.filter(status="cancelled")

    holidays = Holiday.objects.filter(start_date__gte=today)
    next_holiday = (
        holidays.order_by("start_date").first() if holidays.exists() else None
    )
    holidays = holidays.filter(
        start_date__gte=today, start_date__month=today.month
    ).order_by("start_date")[1:]

    context = {
        "leave_requests": leave_requests.filter(
            start_date__month=today.month, start_date__year=today.year
        ),
        "requested": requested,
        "approved": approved,
        "cancelled": cancelled,
        "next_holiday": next_holiday,
        "holidays": holidays,
        "dashboard": "dashboard",
    }
    return render(request, "leave/employee_dashboard.html", context)


@login_required
def dashboard_leave_request(request):
    user = Employee.objects.get(employee_user_id=request.user)
    day = request.GET.get("date")
    if day:
        day = datetime.strptime(day, "%Y-%m")
        leave_requests = LeaveRequest.objects.filter(
            employee_id=user, start_date__month=day.month, start_date__year=day.year
        )
    else:
        leave_requests = []
    context = {"leave_requests": leave_requests, "dashboard": "dashboard"}
    return render(request, "leave/leave_request/leave_requests.html", context)


@login_required
def available_leave_chart(request):
    user = Employee.objects.get(employee_user_id=request.user)
    available_leaves = AvailableLeave.objects.filter(employee_id=user)
    leave_count = []
    for leave in available_leaves:
        leave_count.append(leave.available_days + leave.carryforward_days)

    labels = [available.leave_type_id.name for available in available_leaves]
    dataset = [
        {
            "label": _("Total leaves available"),
            "data": leave_count,
        },
    ]
    response = {
        "labels": labels,
        "dataset": dataset,
        "message": _("Oops!! No leaves available for you this month..."),
    }
    return JsonResponse(response)


@login_required
def employee_leave_chart(request):
    leave_requests = LeaveRequest.objects.filter(status="approved")
    leave_types = LeaveType.objects.all()
    day = date.today()
    if request.GET.get("date"):
        day = request.GET.get("date")
        day = datetime.strptime(day, "%Y-%m")

    labels = []
    dataset = []
    for employee in leave_requests.filter(
        start_date__month=day.month, start_date__year=day.year
    ):
        labels.append(employee.employee_id)

    for leave_type in leave_types:
        dataset.append(
            {
                "label": leave_type.name,
                "data": [],
            }
        )

    labels = list(set(labels))
    total_leave_with_type = defaultdict(lambda: defaultdict(float))

    for label in labels:
        leaves = leave_requests.filter(
            employee_id=label, start_date__month=day.month, start_date__year=day.year
        )
        for leave in leaves:
            total_leave_with_type[leave.leave_type_id.name][label] += round(
                leave.requested_days, 2
            )

    for data in dataset:
        dataset_label = data["label"]
        data["data"] = [total_leave_with_type[dataset_label][label] for label in labels]

    employee_label = []
    for employee in list(set(labels)):
        employee_label.append(
            f"{employee.employee_first_name} {employee.employee_last_name}"
        )

    response = {
        "labels": employee_label,
        "dataset": dataset,
        "message": _("No leave request this month"),
    }
    return JsonResponse(response)


@login_required
def department_leave_chart(request):
    today = date.today()

    departments = Department.objects.all()
    department_counts = {dep.department: 0 for dep in departments}
    leave_request = LeaveRequest.objects.filter(status="approved")
    leave_dates = []

    for leave in leave_request:
        for leave_date in leave.requested_dates():
            leave_dates.append(leave_date.strftime("%Y-%m-%d"))

        if str(today) in leave_dates:
            for dep in departments:
                if dep == leave.employee_id.employee_work_info.department_id:
                    department_counts[dep.department] += 1

    labels = [department.department for department in departments]
    dataset = [
        {
            "label": _(""),
            "data": list(department_counts.values()),
        },
    ]
    response = {
        "labels": labels,
        "dataset": dataset,
    }
    return JsonResponse(response)


@login_required
def leave_type_chart(request):
    leave_types = LeaveType.objects.all()
    leave_type_count = {types.name: 0 for types in leave_types}
    leave_request = LeaveRequest.objects.filter(status="approved")
    for leave in leave_request:
        for lev in leave_types:
            if lev == leave.leave_type_id:
                leave_type_count[lev.name] += leave.requested_days

    labels = [leave_type.name for leave_type in leave_types]

    response = {
        "labels": labels,
        "dataset": [
            {
                "data": list(leave_type_count.values()),
            },
        ],
    }
    return JsonResponse(response)


@login_required
def leave_over_period(request):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    week_dates = [start_of_week + timedelta(days=i) for i in range(6)]

    leave_in_week = []

    leave_request = LeaveRequest.objects.filter(status="approved")
    leave_dates = []
    for leave in leave_request:
        for leave_date in leave.requested_dates():
            leave_dates.append(leave_date)

    filtered_dates = [
        day
        for day in leave_dates
        if day.month == today.month and day.year == today.year
    ]
    for week_date in week_dates:
        days = []
        for filtered_date in filtered_dates:
            if filtered_date == week_date:
                days.append(filtered_date)
        leave_in_week.append(len(days))

    dataset = (
        {
            "label": _("Leave Trends"),
            "data": leave_in_week,
        },
    )

    labels = [week_date.strftime("%d-%m-%Y") for week_date in week_dates]

    response = {
        "labels": labels,
        "dataset": dataset,
    }
    return JsonResponse(response)
