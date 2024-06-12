"""
views.py
"""

import contextlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, unquote

import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from attendance.filters import PenaltyFilter
from attendance.forms import PenaltyAccountForm
from attendance.methods.group_by import group_by_queryset
from attendance.models import PenaltyAccount
from base.methods import (
    choosesubordinates,
    closest_numbers,
    export_data,
    filter_conditional_leave_request,
    filtersubordinates,
    get_key_instances,
    get_pagination,
    sortby,
)
from base.models import *
from employee.models import Employee
from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    owner_can_enter,
    permission_required,
)
from leave.decorators import *
from leave.filters import *
from leave.forms import *
from leave.models import *
from leave.threading import LeaveMailSendThread
from notifications.signals import notify
from recruitment.models import InterviewSchedule

from .methods import (
    calculate_requested_days,
    company_leave_dates_list,
    holiday_dates_list,
    leave_requested_dates,
)


def generate_error_report(error_list, error_data, file_name):
    for item in error_list:
        for key, value in error_data.items():
            if key in item:
                value.append(item[key])
            else:
                value.append(None)
    keys_to_remove = [
        key for key, value in error_data.items() if all(v is None for v in value)
    ]
    for key in keys_to_remove:
        del error_data[key]
    data_frame = pd.DataFrame(error_data, columns=error_data.keys())
    styled_data_frame = data_frame.style.applymap(
        lambda x: "text-align: center", subset=pd.IndexSlice[:, :]
    )
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    writer = pd.ExcelWriter(response, engine="xlsxwriter")
    styled_data_frame.to_excel(writer, index=False, sheet_name="Sheet1")
    worksheet = writer.sheets["Sheet1"]
    worksheet.set_column("A:Z", 30)
    writer.close()
    return response


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
    return render(request, "leave/leave_type/leave_type_creation.html", {"form": form})


def paginator_qry(qryset, page_number):
    """
    function used to paginate query set
    """
    paginator = Paginator(qryset, get_pagination())
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

    queryset = LeaveType.objects.all().exclude(is_compensatory_leave=True)
    if (
        LeaveGeneralSetting.objects.first()
        and LeaveGeneralSetting.objects.first().compensatory_leave
    ):
        queryset = LeaveType.objects.all()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    previous_data = request.GET.urlencode()
    leave_type_filter = LeaveTypeFilter()
    requests_ids = json.dumps(list(queryset.values_list("id", flat=True)))
    if not queryset.exists():
        template_name = "leave/leave_type/leave_type_empty_view.html"
    else:
        template_name = "leave/leave_type/leave_type_view.html"
    return render(
        request,
        template_name,
        {
            "leave_types": page_obj,
            "form": leave_type_filter.form,
            "pd": previous_data,
            "requests_ids": requests_ids,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.view_leavetype")
def leave_type_individual_view(request, id):
    """
    function used to view one leave type.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return one leave type view template
    """
    leave_type = LeaveType.objects.get(id=id)
    requests_ids_json = request.GET.get("instances_ids")
    compensatory = request.GET.get("compensatory")
    context = {"leave_type": leave_type, "compensatory": compensatory}
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, id)
        context["previous"] = previous_id
        context["next"] = next_id
        context["requests_ids"] = requests_ids_json
    return render(request, "leave/leave_type/leave_type_individual_view.html", context)


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
    requests_ids = json.dumps(list(leave_type_filter.values_list("id", flat=True)))
    data_dict = parse_qs(previous_data)
    get_key_instances(LeaveType, data_dict)
    return render(
        request,
        "leave/leave_type/leave_types.html",
        {
            "leave_types": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "requests_ids": requests_ids,
        },
    )


@login_required
@permission_required("leave.change_leavetype")
def leave_type_update(request, id, **kwargs):
    """
    function used to update leave type.

    request (HttpRequest): The HTTP request object.
    id : leave type id

    Returns:
    GET : return leave type update template
    POST : return leave type view
    """
    try:
        leave_type = LeaveType.objects.get(id=id)
    except (LeaveType.DoesNotExist, OverflowError, ValueError):
        messages.error(request, _("Leave type not found"))
        return redirect(leave_type_view)
    form = UpdateLeaveTypeForm(instance=leave_type)
    compensatory = request.GET.get("compensatory")
    redirect_url = leave_type_view
    if compensatory:
        redirect_url = compensatory_leave_settings_view
    if request.method == "POST":
        form_data = UpdateLeaveTypeForm(
            request.POST, request.FILES, instance=leave_type
        )
        if form_data.is_valid():
            form_data.save()
            messages.success(request, _("Leave type is updated successfully.."))
            return redirect(redirect_url)
    return render(
        request,
        "leave/leave_type/leave_type_update.html",
        {"form": form, "compensatory": compensatory},
    )


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
        messages.success(request, _("Leave type deleted successfully.."))
    except (LeaveType.DoesNotExist, OverflowError, ValueError):
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
def get_employee_leave_types(request):
    employee_id = request.GET.get("employee_id")
    form = LeaveRequestCreationForm()

    if employee_id:
        employee = get_object_or_404(Employee, id=employee_id)
        assigned_leave_types = LeaveType.objects.filter(
            id__in=employee.available_leave.values_list("leave_type_id", flat=True)
        )
        form.fields["leave_type_id"].queryset = assigned_leave_types
    else:
        form.fields["leave_type_id"].queryset = LeaveType.objects.none()

    leave_type_field_html = render_to_string(
        "leave/leave_request/leave_type_field.html",
        {
            "form": form,
            "field_name": "leave_type_id",
            "field": form.fields["leave_type_id"],
        },
    )
    return HttpResponse(leave_type_field_html)


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
    referer_parts = [
        part for part in request.META.get("HTTP_REFERER").split("/") if part != ""
    ]
    confirm = request.GET.get("confirm")
    if request.GET.urlencode().startswith("pd="):
        previous_data = unquote(request.GET.urlencode())[len("pd=") :]
    else:
        request_copy = request.GET.copy()
        if "confirm" in request_copy:
            request_copy.pop("confirm")
        previous_data = request_copy.urlencode()
    form = LeaveRequestCreationForm()
    if request:
        employee = request.user.employee_get
        if employee:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            form.fields["leave_type_id"].queryset = assigned_leave_types
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
            leave_request = form.save(commit=False)
            save = True

            if not confirm == "True":
                interview = InterviewSchedule.objects.filter(
                    employee_id=leave_request.employee_id.id
                )
                days = leave_request.requested_dates()

                interviews = []
                for i in interview:
                    if i.interview_date in days:
                        interviews.append(i)
                        save = False

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
                available_leave.save()
            if save:
                leave_request.created_by = request.user.employee_get
                leave_request.save()
                mail_thread = LeaveMailSendThread(
                    request, leave_request, type="request"
                )
                mail_thread.start()
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
                        redirect=f"/leave/request-view?id={leave_request.id}",
                    )
                form = LeaveRequestCreationForm()
                if referer_parts[-2] == "employee-view":
                    return HttpResponse("<script>window.location.reload();</script>")

            elif not confirm == "True":
                admin = True
                return render(
                    request,
                    "leave/user_leave/user_leave_confirm.html",
                    {
                        "employee": leave_request,
                        "interview": interviews,
                        "title": _("Leave Request Alert."),
                        "admin": admin,
                    },
                )
            leave_requests = LeaveRequest.objects.all()
            if len(leave_requests) == 1:
                return HttpResponse("<script>window.location.reload()</script>")

    return render(
        request,
        "leave/leave_request/leave_request_form.html",
        {"form": form, "pd": previous_data, "confirm": confirm},
    )


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
    queryset = LeaveRequestFilter(request.GET).qs.order_by("-id").distinct()
    multiple_approvals = filter_conditional_leave_request(request).distinct()
    queryset = (
        filtersubordinates(request, queryset, "leave.view_leaverequest")
        | multiple_approvals
    )
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    leave_request_filter = LeaveRequestFilter()
    excel_column = LeaveRequestExportForm()
    export_filter = LeaveRequestFilter()

    # Fetching leave requests
    leave_requests = queryset

    leave_requests_with_interview = []
    for leave_request in leave_requests:

        # Fetch interviews for the employee within the requested leave period
        interviews = InterviewSchedule.objects.filter(
            employee_id=leave_request.employee_id,
            interview_date__range=[leave_request.start_date, leave_request.end_date],
        )
        if interviews:
            # If interview exists then adding the leave request to the list
            leave_requests_with_interview.append(leave_request)

    requests = queryset.filter(status="requested").count()
    requests_ids = json.dumps(list(page_obj.object_list.values_list("id", flat=True)))
    approved_requests = queryset.filter(status="approved").count()
    rejected_requests = queryset.filter(status="cancelled").count()
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(LeaveRequest, data_dict)
    return render(
        request,
        "leave/leave_request/request_view.html",
        {
            "leave_requests": page_obj,
            "pd": previous_data,
            "form": leave_request_filter.form,
            "requests": requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "gp_fields": LeaveRequestReGroup.fields,
            "excel_column": excel_column,
            "export_filter": export_filter.form,
            "requests_ids": requests_ids,
            "current_date": date.today(),
            "filter_dict": data_dict,
            "leave_requests_with_interview": leave_requests_with_interview,
        },
    )


@login_required
@manager_can_enter("leave.view_leaverequest")
def leave_requests_export(request):
    return export_data(
        request=request,
        model=LeaveRequest,
        filter_class=LeaveRequestFilter,
        form_class=LeaveRequestExportForm,
        file_name="Leave_requests",
    )


@login_required
@hx_request_required
# @manager_can_enter("leave.view_leaverequest")
def leave_request_filter(request):
    """
    function used to filter leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave request view template
    """
    previous_data = request.GET.urlencode()
    queryset = LeaveRequestFilter(request.GET).qs.order_by("-id")

    # Fetching leave requests
    leave_requests = queryset

    leave_requests_with_interview = []
    for leave_request in leave_requests:

        # Fetch interviews for the employee within the requested leave period
        interviews = InterviewSchedule.objects.filter(
            employee_id=leave_request.employee_id,
            interview_date__range=[leave_request.start_date, leave_request.end_date],
        )
        if interviews:
            # If interview exists then adding the leave request to the list
            leave_requests_with_interview.append(leave_request)

    field = request.GET.get("field")
    queryset = filtersubordinates(request, queryset, "leave.view_leaverequest")
    leave_request_filter = LeaveRequestFilter(request.GET, queryset).qs
    page_number = request.GET.get("page")
    template = ("leave/leave_request/leave_requests.html",)
    if request.GET.get("sortby"):
        leave_request_filter = sortby(request, leave_request_filter, "sortby")

    if field != "" and field is not None:
        leave_request_filter = group_by_queryset(
            leave_request_filter, field, request.GET.get("page"), "page"
        )
        list_values = [entry["list"] for entry in leave_request_filter]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)

        requests_ids = json.dumps(list(id_list))
        template = "leave/leave_request/group_by.html"

    else:
        leave_request_filter = paginator_qry(
            leave_request_filter, request.GET.get("page")
        )
        requests_ids = json.dumps(
            [instance.id for instance in leave_request_filter.object_list]
        )

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
        template,
        {
            "leave_requests": leave_request_filter,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field": field,
            "dashboard": request.GET.get("dashboard"),
            "requests_ids": requests_ids,
            "current_date": date.today(),
            "leave_requests_with_interview": leave_requests_with_interview,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.change_leaverequest")
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
    leave_type_id = leave_request.leave_type_id
    confirm = request.GET.get("confirm")
    employee = leave_request.employee_id
    form = LeaveRequestUpdationForm(instance=leave_request)
    if employee:
        available_leaves = employee.available_leave.all()
        assigned_leave_types = LeaveType.objects.filter(
            id__in=available_leaves.values_list("leave_type_id", flat=True)
        )
        if leave_type_id not in assigned_leave_types.values_list("id", flat=True):
            assigned_leave_types = assigned_leave_types | LeaveType.objects.filter(
                id=leave_type_id.id
            )
        form.fields["leave_type_id"].queryset = assigned_leave_types
    form = choosesubordinates(request, form, "leave.add_leaverequest")
    if request.method == "POST":
        form = LeaveRequestUpdationForm(
            request.POST, request.FILES, instance=leave_request
        )
        form = choosesubordinates(request, form, "leave.add_leaverequest")
        if form.is_valid():
            leave_request = form.save(commit=False)
            save = True

            if not confirm == "True":
                interview = InterviewSchedule.objects.filter(
                    employee_id=leave_request.employee_id.id
                )
                days = leave_request.requested_dates()

                interviews = []
                for i in interview:
                    if i.interview_date in days:
                        interviews.append(i)
                        save = False
            if save:
                leave_request.save()
                messages.success(request, _("Leave request is updated successfully.."))
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
                        redirect=f"/leave/request-view?id={leave_request.id}",
                    )
                response = render(
                    request,
                    "leave/leave_request/request_update_form.html",
                    {"form": form, "id": id},
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )

            elif not confirm == "True":
                update_admin = True
                return render(
                    request,
                    "leave/user_leave/user_leave_confirm.html",
                    {
                        "employee": leave_request,
                        "interview": interviews,
                        "title": _("Leave Request Alert."),
                        "id": id,
                        "update_admin": update_admin,
                    },
                )
    return render(
        request,
        "leave/leave_request/request_update_form.html",
        {"form": form, "id": id, "confirm": confirm},
    )


@login_required
@hx_request_required
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
    previous_data = request.GET.urlencode()
    try:
        leave_request = LeaveRequest.objects.get(id=id)
        messages.success(request, _("Leave request deleted successfully.."))
        leave_request.delete()
    except (LeaveRequest.DoesNotExist, OverflowError, ValueError):
        messages.error(request, _("Leave request not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    hx_target = request.META.get("HTTP_HX_TARGET", None)
    if hx_target == "leaveRequest":
        leave_requests = LeaveRequest.objects.all()
        if leave_requests.exists():
            return redirect(f"/leave/request-filter?{previous_data}")
        else:
            return HttpResponse("<script>window.location.reload();</script>")
    return redirect(leave_request_view)


@login_required
@manager_can_enter("leave.change_leaverequest")
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
    if leave_request.status != "approved":
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
            if not leave_request.multiple_approvals():
                super(AvailableLeave, available_leave).save()
                leave_request.save()
            else:
                if request.user.is_superuser:
                    LeaveRequestConditionApproval.objects.filter(
                        leave_request_id=leave_request
                    ).update(is_approved=True)
                    super(AvailableLeave, available_leave).save()
                    leave_request.save()
                else:
                    conditional_requests = leave_request.multiple_approvals()
                    approver = [
                        manager
                        for manager in conditional_requests["managers"]
                        if manager.employee_user_id == request.user
                    ]
                    condition_approval = LeaveRequestConditionApproval.objects.filter(
                        manager_id=approver[0], leave_request_id=leave_request
                    ).first()
                    condition_approval.is_approved = True
                    condition_approval.save()
                    if approver[0] == conditional_requests["managers"][-1]:
                        super(AvailableLeave, available_leave).save()
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
                    redirect=f"/leave/user-request-view?id={leave_request.id}",
                )

            mail_thread = LeaveMailSendThread(request, leave_request, type="approve")
            mail_thread.start()
        else:
            messages.error(
                request,
                f"{employee_id} dont have enough leave days to approve the request..",
            )
    else:
        messages.error(request, _("Leave request already approved"))
    if emp_id is not None:
        employee_id = emp_id
        return redirect(f"/employee/employee-view/{employee_id}/")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@manager_can_enter("leave.change_leaverequest")
def leave_request_bulk_approve(request):
    if request.method == "POST":
        request_ids = request.POST.getlist("ids")
        for request_id in request_ids:
            try:
                leave_request = (
                    LeaveRequest.objects.get(id=int(request_id)) if request_id else None
                )
                if (
                    leave_request.status == "requested"
                    and leave_request.start_date >= datetime.today().date()
                ):
                    leave_request_approve(request, leave_request.id)
                else:
                    if leave_request.status == "approved":
                        messages.info(
                            request,
                            _("{} {} request already approved").format(
                                leave_request.employee_id, leave_request.leave_type_id
                            ),
                        )
                    elif leave_request.start_date < datetime.today().date():
                        messages.warning(
                            request,
                            _("{} {} request date exceeded").format(
                                leave_request.employee_id, leave_request.leave_type_id
                            ),
                        )
                    else:
                        messages.warning(
                            request,
                            _("{} {} can't approve.").format(
                                leave_request.employee_id, leave_request.leave_type_id
                            ),
                        )
            except (ValueError, OverflowError, LeaveRequest.DoesNotExist):
                messages.error(request, _("Leave request not found"))
                pass
    return HttpResponse("<script>window.location.reload();</script>")


@login_required
@manager_can_enter("leave.change_leaverequest")
def leave_request_cancel(request, id, emp_id=None):
    """
    function used to Reject leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id
    emp_id : employee id if the cancel operation comes from "/employee/employee-view/{employee_id}/" template.

    Returns:
    GET : If `emp_id` is provided, it returns to the "/employee/employee-view/{employee_id}/" template after cancel.
          Otherwise, it returns to the default leave request view template.

    """
    form = RejectForm()
    if request.method == "POST":
        form = RejectForm(request.POST)
        if form.is_valid():
            leave_request = LeaveRequest.objects.get(id=id)
            employee_id = leave_request.employee_id
            leave_type_id = leave_request.leave_type_id
            available_leave = AvailableLeave.objects.get(
                leave_type_id=leave_type_id, employee_id=employee_id
            )
            available_leave.available_days += leave_request.approved_available_days
            available_leave.carryforward_days += (
                leave_request.approved_carryforward_days
            )
            leave_request.approved_available_days = 0
            leave_request.approved_carryforward_days = 0
            leave_request.status = "rejected"
            if leave_request.multiple_approvals() and not request.user.is_superuser:
                conditional_requests = leave_request.multiple_approvals()
                approver = [
                    manager
                    for manager in conditional_requests["managers"]
                    if manager.employee_user_id == request.user
                ]
                condition_approval = LeaveRequestConditionApproval.objects.filter(
                    manager_id=approver[0], leave_request_id=leave_request
                ).first()
                condition_approval.is_approved = False
                condition_approval.is_rejected = True
                condition_approval.save()

            leave_request.reject_reason = form.cleaned_data["reason"]
            leave_request.save()
            available_leave.save()
            comment = LeaverequestComment()
            comment.request_id = leave_request
            comment.employee_id = request.user.employee_get
            comment.comment = leave_request.reject_reason
            comment.save()

            messages.success(request, _("Leave request rejected successfully.."))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_user_id,
                    verb="Your leave request has been rejected.",
                    verb_ar="تم رفض طلب الإجازة الخاص بك",
                    verb_de="Ihr Urlaubsantrag wurde abgelehnt",
                    verb_es="Tu solicitud de permiso ha sido rechazada",
                    verb_fr="Votre demande de congé a été rejetée",
                    icon="people-circle",
                    redirect=f"/leave/user-request-view?id={leave_request.id}",
                )

            mail_thread = LeaveMailSendThread(request, leave_request, type="reject")
            mail_thread.start()
            if emp_id is not None:
                employee_id = emp_id
                return redirect(f"/employee/employee-view/{employee_id}/")
            return HttpResponse("<script>location.reload();</script>")
    return render(
        request, "leave/leave_request/cancel_form.html", {"form": form, "id": id}
    )


@login_required
@hx_request_required
def user_leave_cancel(request, id):
    """
    function used to cancel approved leave request by employee.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET :  it returns to the default my leave request view template.

    """
    leave_request = LeaveRequest.objects.get(id=id)
    employee_id = leave_request.employee_id
    if employee_id.employee_user_id.id == request.user.id:
        current_date = date.today()
        if (
            leave_request.status == "approved"
            and leave_request.end_date >= current_date
        ):
            form = RejectForm()
            if request.method == "POST":
                form = RejectForm(request.POST)
                if form.is_valid():
                    leave_request.reject_reason = form.cleaned_data["reason"]
                    leave_request.status = "cancelled"
                    leave_request.save()
                    messages.success(
                        request, _("Leave request cancelled successfully..")
                    )

                    mail_thread = LeaveMailSendThread(
                        request, leave_request, type="cancel"
                    )
                    mail_thread.start()
                    return HttpResponse("<script>location.reload();</script>")
            return render(
                request,
                "leave/leave_request/user_cancel_form.html",
                {"form": form, "id": id},
            )
        messages.error(request, _("You can't cancel this leave request."))
        return HttpResponse("<script>location.reload();</script>")
    messages.error(request, _("You don't have the permission."))
    return HttpResponse("<script>location.reload();</script>")


@login_required
@hx_request_required
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
    context = {
        "leave_request": leave_request,
        "current_date": date.today(),
        "dashboard": request.GET.get("dashboard"),
    }
    requests_ids_json = request.GET.get("instances_ids")

    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, id)
        context["previous"] = previous_id
        context["next"] = next_id
        context["requests_ids"] = requests_ids_json
    return render(request, "leave/leave_request/one_request_view.html", context)


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
        if not leave_type.is_compensatory_leave:
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
                            redirect="/leave/user-request-view",
                        )
                else:
                    messages.info(
                        request, _("leave type is already assigned to the employee..")
                    )
        else:
            messages.info(
                request, _("Compensatory leave type cant assigned manually..")
            )
        response = render(
            request,
            "leave/leave_assign/leave_assign_one_form.html",
            {"form": form, "id": id},
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location.reload();</script>"
        )
    return render(
        request,
        "leave/leave_assign/leave_assign_one_form.html",
        {"form": form, "id": id},
    )


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
    page_obj = paginator_qry(queryset.order_by("-id"), page_number)
    assigned_leave_filter = AssignedLeaveFilter()
    assign_form = AssignLeaveForm()

    # default group by configuration
    data_dict = {"field": ["leave_type_id"]}

    # to check condition on the template
    setattr(request.GET, "field", True)

    page_obj = group_by_queryset(queryset.order_by("-id"), "leave_type_id", page_number)
    list_values = [entry["list"] for entry in page_obj]
    id_list = []
    for value in list_values:
        for instance in value.object_list:
            id_list.append(instance.id)
    available_leave_ids = json.dumps(list(id_list))

    return render(
        request,
        "leave/leave_assign/assign_view.html",
        {
            "available_leaves": page_obj,
            "f": assigned_leave_filter,
            "pd": previous_data,
            "filter_dict": data_dict,
            "gp_fields": LeaveAssignReGroup.fields,
            "assign_form": assign_form,
            "available_leave_ids": available_leave_ids,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.view_availableleave")
def available_leave_single_view(request, obj_id):
    previous_data = request.GET.urlencode()
    available_leave = AvailableLeave.objects.filter(id=obj_id).first()
    instance_ids_json = request.GET["instances_ids"]
    instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
    previous_instance, next_instance = closest_numbers(instance_ids, obj_id)
    content = {
        "available_leave": available_leave,
        "previous_instance": previous_instance,
        "next_instance": next_instance,
        "instance_ids_json": instance_ids_json,
        "pd": previous_data,
    }
    return render(
        request, "leave/leave_assign/single_assign_view.html", context=content
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
    assign_form = AssignLeaveForm()
    queryset = filtersubordinates(request, queryset, "leave.view_availableleave")
    assigned_leave_filter = AssignedLeaveFilter(request.GET, queryset).qs
    previous_data = request.GET.urlencode()
    field = request.GET.get("field")
    page_number = request.GET.get("page")
    template = ("leave/leave_assign/assigned_leave.html",)
    available_leaves = assigned_leave_filter.order_by("-id")
    if request.GET.get("sortby"):
        available_leaves = sortby(request, available_leaves, "sortby")
        available_leave_ids = json.dumps(
            [instance.id for instance in paginator_qry(available_leaves, None)]
        )
    if field != "" and field is not None:
        page_obj = group_by_queryset(available_leaves, field, page_number)
        list_values = [entry["list"] for entry in page_obj]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)
        available_leave_ids = json.dumps(list(id_list))
        template = "leave/leave_assign/group_by.html"
    else:
        available_leave_ids = json.dumps(
            [instance.id for instance in paginator_qry(available_leaves, None)]
        )
        page_obj = paginator_qry(available_leaves, page_number)

    data_dict = parse_qs(previous_data)
    get_key_instances(AvailableLeave, data_dict)
    return render(
        request,
        template,
        {
            "available_leaves": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field": field,
            "assign_form": assign_form,
            "available_leave_ids": available_leave_ids,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("leave.add_availableleave")
def leave_assign(request):
    """
    function used to assign multiple leave types to employees.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET: return multiple leave type assign form template
    POST: return leave type assigned view
    """
    form = AssignLeaveForm()
    form = choosesubordinates(request, form, "leave.add_availableleave")
    page_reload = AvailableLeave.objects.filter().count() == 0
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
                                request, _("Leave type assign is successful..")
                            )
                            with contextlib.suppress(Exception):
                                notify.send(
                                    request.user.employee_get,
                                    recipient=employee.employee_user_id,
                                    verb="New leave type is assigned to you",
                                    verb_ar="تم تعيين نوع إجازة جديد لك",
                                    verb_de="Dir wurde ein neuer Urlaubstyp zugewiesen",
                                    verb_es="Se te ha asignado un nuevo tipo de permiso",
                                    verb_fr="Un nouveau type de congé vous a été attribué",
                                    icon="people-circle",
                                    redirect="/leave/user-request-view",
                                )
                        else:
                            messages.info(
                                request,
                                _("Leave type is already assigned to the employee.."),
                            )
        if page_reload:
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request, "leave/leave_assign/leave_assign_form.html", {"assign_form": form}
    )


@login_required
@hx_request_required
@manager_can_enter("leave.change_availableleave")
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
    previous_data = request.GET.urlencode() or "field=leave_type_id"
    if request.method == "POST":
        form = AvailableLeaveUpdateForm(request.POST, instance=leave_assign)
        if form.is_valid():
            available_leave = form.save()
            messages.success(request, _("Available leaves updated successfully..."))
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
                    redirect="/leave/user-request-view",
                )
    return render(
        request,
        "leave/leave_assign/available_update_form.html",
        {"form": form, "id": id, "pd": previous_data},
    )


@login_required
@hx_request_required
@manager_can_enter("leave.delete_availableleave")
def leave_assign_delete(request, obj_id):
    """
    function used to delete assign leave type of an employee.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : available leave id

    Returns:
    GET : return leave type assigned view template
    """
    pd = request.GET.urlencode()
    try:
        AvailableLeave.objects.get(id=obj_id).delete()
        messages.success(request, _("Assigned leave is successfully deleted."))
    except AvailableLeave.DoesNotExist:
        messages.error(request, _("Assigned leave not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    if not request.GET.get("instances_ids"):
        if not AvailableLeave.objects.filter():
            return HttpResponse("<script>window.location.reload()</script>")
        return redirect(f"/leave/assign-filter?{pd}")
    else:
        instances_ids = request.GET.get("instances_ids")
        instances_list = json.loads(instances_ids)
        if obj_id in instances_list:
            instances_list.remove(obj_id)
        previous_instance, next_instance = closest_numbers(
            json.loads(instances_ids), obj_id
        )
        return redirect(
            f"/leave/available-leave-single-view/{next_instance}/?instances_ids={instances_list}"
        )


@require_http_methods(["POST"])
@permission_required("leave.delete_availableleave")
def leave_assign_bulk_delete(request):
    """
    This method is used to delete bulk of assigned leaves
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for assigned_leave_id in ids:
        try:
            assigned_leave = AvailableLeave.objects.get(id=assigned_leave_id)
            leave_type = assigned_leave.leave_type_id
            employee = assigned_leave.employee_id
            assigned_leave.delete()
            messages.success(
                request,
                _("{} assigned to {} deleted.".format(leave_type, employee)),
            )
        except Exception as e:
            messages.error(request, _("Assigned leave not found."))
    return JsonResponse({"message": "Success"})


def assign_leave_type_excel(_request):
    """
    Generate an empty Excel template for asisgn leave type to employee with predefined columns.

    Returns:
        HttpResponse: An HTTP response containing an empty Excel template with predefined columns.
    """
    try:
        columns = [
            "Employee Badge ID",
            "Leave Type",
        ]
        data_frame = pd.DataFrame(columns=columns)
        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = (
            'attachment; filename="assign_leave_type_excel.xlsx"'
        )
        data_frame.to_excel(response, index=False)
        return response
    except Exception as exception:
        return HttpResponse(exception)


@login_required
@manager_can_enter("leave.add_availableleave")
def assign_leave_type_import(request):
    """
    This function accepts a POST request containing an Excel file with assign leave type to employee data.
    It processes the data, checks for errors, and either assigns leave types to employees
    or generates an error report in the form of an Excel file.
    """
    error_data = {
        "Employee Badge ID": [],
        "Leave Type": [],
        "Error1": [],
        "Error2": [],
        "Error3": [],
        "Error4": [],
    }
    error_list = []
    file_name = "AssignLeaveError.xlsx"
    if request.method == "POST":
        file = request.FILES["assign_leave_type_import"]
        data_frame = pd.read_excel(file)
        assign_leave_dicts = data_frame.to_dict("records")
        for assign_leave in assign_leave_dicts:
            try:
                save = True
                assign_leave_type = assign_leave["Leave Type"]
                badge_id = assign_leave["Employee Badge ID"]
                employee = Employee.objects.filter(badge_id__iexact=badge_id).first()
                leave_type = LeaveType.objects.filter(
                    name__iexact=assign_leave_type
                ).first()
                if employee is None:
                    save = False
                    assign_leave["Error1"] = _("This badge id does not exist.")

                if leave_type is None:
                    save = False
                    assign_leave["Error2"] = _("This leave type does not exist.")
                if AvailableLeave.objects.filter(
                    leave_type_id=leave_type, employee_id=employee
                ).exists():
                    save = False
                    assign_leave["Error3"] = _(
                        "Leave type has already been assigned to the employee."
                    )
                if save:
                    AvailableLeave(
                        leave_type_id=leave_type,
                        employee_id=employee,
                        available_days=leave_type.total_days,
                    ).save()
                else:
                    error_list.append(assign_leave)
            except Exception as exception:
                assign_leave["Error4"] = f"{str(exception)}"
                error_list.append(assign_leave)
        if error_list:
            response = generate_error_report(error_list, error_data, file_name)
            return response
        return redirect(leave_assign_view)
    return redirect(leave_assign_view)


@login_required
def assigned_leaves_export(request):
    hx_request = request.META.get("HTTP_HX_REQUEST")
    if hx_request:
        export_filter = AssignedLeaveFilter()
        export_column = AvailableLeaveColumnExportForm()
        content = {
            "export_filter": export_filter,
            "export_column": export_column,
        }
        return render(
            request,
            "leave/leave_assign/assigned_leaves_export_form.html",
            context=content,
        )
    return export_data(
        request=request,
        model=AvailableLeave,
        filter_class=AssignedLeaveFilter,
        form_class=AvailableLeaveColumnExportForm,
        file_name="Assign_Leave",
    )


def get_job_positions(request):
    department_id = request.GET.get("department_id")
    job_positions = (
        JobPosition.objects.filter(department_id=department_id).values_list(
            "id", "job_position"
        )
        if department_id
        else []
    )
    return JsonResponse({"job_positions": dict(job_positions)})


@login_required
@hx_request_required
@permission_required("leave.add_restrictleave")
def restrict_creation(request):
    """
    function used to create restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return restricted days creation form template
    POST : return restricted days view template
    """

    query_string = request.GET.urlencode()
    if query_string.startswith("pd="):
        previous_data = unquote(query_string[len("pd=") :])
    else:
        previous_data = unquote(query_string)
    form = RestrictLeaveForm()

    if request.method == "POST":
        form = RestrictLeaveForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Restricted day created successfully.."))
            if RestrictLeave.objects.filter().count() == 1:
                return HttpResponse("<script>window.location.reload();</script>")
    return render(
        request,
        "leave/restrict/restrict_form.html",
        {"form": form, "pd": previous_data},
    )


@login_required
def restrict_view(request):
    """
    function used to view restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return restricted days view  template
    """
    queryset = RestrictLeave.objects.all()[::-1]
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    restrictday_filter = RestrictLeaveFilter()
    return render(
        request,
        "leave/restrict/view_restrict.html",
        {
            "restrictday": page_obj,
            "form": restrictday_filter.form,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
def restrict_filter(request):
    """
    function used to filter restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return restricted days view template
    """
    queryset = RestrictLeave.objects.all()
    previous_data = request.GET.urlencode()
    restrictday_filter = RestrictLeaveFilter(request.GET, queryset).qs
    if request.GET.get("sortby"):
        restrictday_filter = sortby(request, restrictday_filter, "sortby")
    page_number = request.GET.get("page")
    page_obj = paginator_qry(restrictday_filter[::-1], page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(RestrictLeave, data_dict)
    return render(
        request,
        "leave/restrict/restrict.html",
        {"restrictday": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


@login_required
@hx_request_required
@permission_required("leave.change_restrictleave")
def restrict_update(request, id):
    """
    function used to update restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : restricted days id

    Returns:
    GET : return restricted days update form template
    POST : return restricted days view template
    """
    query_string = request.GET.urlencode()
    if query_string.startswith("pd="):
        previous_data = unquote(query_string[len("pd=") :])
    else:
        previous_data = unquote(query_string)
    restrictday = RestrictLeave.objects.get(id=id)
    form = RestrictLeaveForm(instance=restrictday)
    if request.method == "POST":
        form = RestrictLeaveForm(request.POST, instance=restrictday)
        if form.is_valid():
            form.save()
            messages.success(request, _("Restricted day updated successfully.."))
    return render(
        request,
        "leave/restrict/restrict_update_form.html",
        {"form": form, "id": id, "pd": previous_data},
    )


@login_required
@hx_request_required
@permission_required("leave.delete_restrictleave")
def restrict_delete(request, id):
    """
    function used to delete restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : restricted days id

    Returns:
    GET : return restricted days view template
    """
    query_string = request.GET.urlencode()
    try:
        RestrictLeave.objects.get(id=id).delete()
        messages.success(request, _("Restricted day deleted successfully.."))
    except RestrictLeave.DoesNotExist:
        messages.error(request, _("Restricted day not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    if not RestrictLeave.objects.filter():
        return HttpResponse("<script>window.location.reload();</script>")
    return redirect(f"/leave/restrict-filter?{query_string}")


@login_required
@hx_request_required
@permission_required("leave.delete_restrictleave")
def restrict_days_bulk_delete(request):
    """
    function used to delete multiple restricted days.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return restricted days view template
    """
    pd = request.GET.urlencode()
    if request.method == "POST":
        restrict_day_ids = request.POST.getlist("ids")
        try:
            restrict_days = RestrictLeave.objects.filter(
                id__in=restrict_day_ids
            ).delete()
            count = len(restrict_day_ids)
            messages.success(
                request,
                _("{} Leave restricted days deleted successfully").format(count),
            )
        except (OverflowError, ValueError):
            messages.error(request, _("Restricted Days not found"))
        except:
            messages.error(request, _("Something went wrong"))
    return redirect(f"/leave/restrict-filter?{pd}")


@login_required
@permission_required("leave.add_restrictleave")
def restrict_day_select(request):
    page_number = request.GET.get("page")
    if page_number == "all":
        restrict_days = RestrictLeave.objects.all()
    restrict_day_ids = [str(day.id) for day in restrict_days]
    total_count = len(restrict_day_ids)
    context = {"restrict_day_ids": restrict_day_ids, "total_count": total_count}
    return JsonResponse(context)


@login_required
@permission_required("leave.add_restrictleave")
def restrict_day_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        restrictday_filter = RestrictLeaveFilter(
            filters, queryset=RestrictLeave.objects.all()
        )
        restrictday_filter = restrictday_filter.qs
        restrictday_ids = [str(restrictday.id) for restrictday in restrictday_filter]
        total_count = restrictday_filter.count()
        context = {"restrict_day_ids": restrictday_ids, "total_count": total_count}
        return JsonResponse(context)


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

    query_string = request.GET.urlencode()
    if query_string.startswith("pd="):
        previous_data = unquote(query_string[len("pd=") :])
    else:
        previous_data = unquote(query_string)
    form = HolidayForm()
    if request.method == "POST":
        form = HolidayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("New holiday created successfully.."))
            if Holiday.objects.filter().count() == 1:
                return HttpResponse("<script>window.location.reload();</script>")
    return render(
        request, "leave/holiday/holiday_form.html", {"form": form, "pd": previous_data}
    )


def holidays_excel_template(request):
    try:
        columns = [
            "Name of Holiday",
            "Start Date",
            "End Date",
            "Recurring",
        ]
        data_frame = pd.DataFrame(columns=columns)
        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = (
            'attachment; filename="assign_leave_type_excel.xlsx"'
        )
        data_frame.to_excel(response, index=False)
        return response
    except Exception as exception:
        return HttpResponse(exception)


def holidays_info_import(request):
    file_name = "HolidaysImportError.xlsx"
    error_list = []
    error_data = {
        "Name of Holiday": [],
        "Start Date": [],
        "End Date": [],
        "Recurring": [],
        "Error1": [],
        "Error2": [],
        "Error3": [],
        "Error4": [],
    }
    if request.method == "POST":
        file = request.FILES["holidays_import"]
        data_frame = pd.read_excel(file)
        holiday_dicts = data_frame.to_dict("records")
        for holiday in holiday_dicts:
            save = True
            try:
                name = holiday["Name of Holiday"]
                try:
                    start_date = pd.to_datetime(holiday["Start Date"]).date()
                except Exception as e:
                    save = False
                    holiday["Error1"] = _("Invalid start date format {}").format(
                        holiday["Start Date"]
                    )
                try:
                    end_date = pd.to_datetime(holiday["End Date"]).date()
                except Exception as e:
                    save = False
                    holiday["Error2"] = _("Invalid end date format {}").format(
                        holiday["End Date"]
                    )
                if holiday["Recurring"].lower() in ["yes", "no"]:
                    recurring = True if holiday["Recurring"].lower() == "yes" else False
                else:
                    save = False
                    holiday["Error3"] = _("Recurring must be {} or {}").format(
                        "yes", "no"
                    )
                if save:
                    holiday = Holiday(
                        name=name,
                        start_date=start_date,
                        end_date=end_date,
                        recurring=recurring,
                    )
                    holiday.save()
                else:
                    error_list.append(holiday)

            except Exception as e:
                holiday["Error4"] = f"{str(e)}"
                error_list.append(holiday)
        if error_list:
            response = generate_error_report(error_list, error_data, file_name)
        else:
            return JsonResponse()


@login_required
def holiday_info_export(request):
    if request.META.get("HTTP_HX_REQUEST"):
        export_filter = HolidayFilter()
        export_column = HolidaysColumnExportForm()
        content = {
            "export_filter": export_filter,
            "export_column": export_column,
        }
        return render(
            request, "leave/holiday/holiday_export_filter_form.html", context=content
        )
    return export_data(
        request=request,
        model=Holiday,
        filter_class=HolidayFilter,
        form_class=HolidaysColumnExportForm,
        file_name="Holidays_export",
    )


@login_required
def holiday_view(request):
    """
    function used to view holidays.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return holiday view  template
    """
    queryset = Holiday.objects.all()[::-1]
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    holiday_filter = HolidayFilter()

    return render(
        request,
        "leave/holiday/holiday_view.html",
        {
            "holidays": page_obj,
            "form": holiday_filter.form,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
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
    if request.GET.get("sortby"):
        holiday_filter = sortby(request, holiday_filter, "sortby")
    page_number = request.GET.get("page")
    page_obj = paginator_qry(holiday_filter[::-1], page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(Holiday, data_dict)
    return render(
        request,
        "leave/holiday/holiday.html",
        {"holidays": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


@login_required
@hx_request_required
@permission_required("leave.change_holiday")
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
    query_string = request.GET.urlencode()
    if query_string.startswith("pd="):
        previous_data = unquote(query_string[len("pd=") :])
    else:
        previous_data = unquote(query_string)
    holiday = Holiday.objects.get(id=id)
    form = HolidayForm(instance=holiday)
    if request.method == "POST":
        form = HolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            form.save()
            messages.success(request, _("Holiday updated successfully.."))
    return render(
        request,
        "leave/holiday/holiday_update_form.html",
        {"form": form, "id": id, "pd": previous_data},
    )


@login_required
@hx_request_required
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
    query_string = request.GET.urlencode()
    try:
        Holiday.objects.get(id=id).delete()
        messages.success(request, _("Holiday deleted successfully.."))
    except Holiday.DoesNotExist:
        messages.error(request, _("Holiday not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    if not Holiday.objects.filter():
        return HttpResponse("<script>window.location.reload();</script>")
    return redirect(f"/leave/holiday-filter?{query_string}")


@require_http_methods(["POST"])
@permission_required("leave.delete_holiday")
def bulk_holiday_delete(request):
    """
    This method is used to delete bulk of holidays
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    del_ids = []
    for holiday_id in ids:
        try:
            holiday = Holiday.objects.get(id=holiday_id)
            holiday.delete()
            del_ids.append(holiday_id)
        except Exception as e:
            messages.error(request, _("Holiday not found."))
    messages.success(
        request, _("{} Holidays have been successfully deleted.".format(len(del_ids)))
    )
    return JsonResponse({"message": "Success"})


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
            if CompanyLeave.objects.filter().count() == 1:
                return HttpResponse("<script>window.location.reload();</script>")
    return render(
        request, "leave/company_leave/company_leave_creation_form.html", {"form": form}
    )


@login_required
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
        "leave/company_leave/company_leave_view.html",
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
@permission_required("leave.change_companyleave")
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
            messages.success(request, _("Company leave updated successfully.."))
    return render(
        request,
        "leave/company_leave/company_leave_update_form.html",
        {"form": form, "id": id},
    )


@login_required
@hx_request_required
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
    query_string = request.GET.urlencode()
    try:
        CompanyLeave.objects.get(id=id).delete()
        messages.success(request, _("Company leave deleted successfully.."))
    except CompanyLeave.DoesNotExist:
        messages.error(request, _("Company leave not found."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    if not CompanyLeave.objects.filter():
        return HttpResponse("<script>window.location.reload();</script>")
    return redirect(f"/leave/company-leave-filter?{query_string}")


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
    previous_data = unquote(request.GET.urlencode())[len("pd=") :]
    employee = request.user.employee_get
    leave_type = LeaveType.objects.get(id=id)
    confirm = request.GET.get("confirm")
    form = UserLeaveRequestForm(
        initial={"employee_id": employee, "leave_type_id": leave_type}
    )
    if request.method == "POST":
        form = UserLeaveRequestForm(request.POST, request.FILES, employee=employee)
        start_date = datetime.strptime(request.POST.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(request.POST.get("end_date"), "%Y-%m-%d")
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
        ).exclude(status__in=["cancelled", "rejected"])
        if overlapping_requests.exists():
            form.add_error(
                None, _("There is already a leave request for this date range..")
            )
        elif requested_days <= available_total_leave:
            if form.is_valid():
                leave_request = form.save(commit=False)
                save = True
                leave_request.leave_type_id = leave_type
                leave_request.employee_id = employee

                if not confirm == "True":
                    interview = InterviewSchedule.objects.filter(
                        employee_id=leave_request.employee_id.id
                    )
                    days = leave_request.requested_dates()

                    interviews = []
                    for i in interview:
                        if i.interview_date in days:
                            interviews.append(i)
                            save = False

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
                    available_leave.save()
                if save:
                    leave_request.created_by = employee
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
                            redirect=f"/leave/request-view?id={leave_request.id}",
                        )
                    if len(
                        LeaveRequest.objects.filter(employee_id=employee)
                    ) == 1 or request.META.get("HTTP_REFERER").endswith(
                        "employee-profile/"
                    ):
                        return HttpResponse(
                            "<script>window.location.reload();</script>"
                        )

                elif not confirm == "True":
                    return render(
                        request,
                        "leave/user_leave/user_leave_confirm.html",
                        {
                            "employee": leave_request,
                            "interview": interviews,
                            "title": _("Leave Request Alert."),
                            "id": id,
                        },
                    )

            return render(
                request,
                "leave/user_leave/user_request_form.html",
                {
                    "form": form,
                    "id": id,
                    "leave_type": leave_type,
                    "pd": previous_data,
                    "confirm": confirm,
                },
            )
        else:
            form.add_error(
                None, _("You dont have enough leave days to make the request..")
            )
    form.fields["leave_type_id"].queryset = LeaveType.objects.filter(id=id)
    return render(
        request,
        "leave/user_leave/user_request_form.html",
        {
            "form": form,
            "id": id,
            "leave_type": leave_type,
            "pd": previous_data,
            "confirm": confirm,
        },
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
    previous_data = request.GET.urlencode()
    confirm = request.GET.get("confirm")
    leave_request = LeaveRequest.objects.get(id=id)
    try:
        if (
            request.user.employee_get == leave_request.employee_id
            and leave_request.status != "approved"
        ):
            form = UserLeaveRequestForm(
                employee=leave_request.employee_id, instance=leave_request
            )
            if request.method == "POST":
                form = UserLeaveRequestForm(
                    request.POST,
                    request.FILES,
                    instance=leave_request,
                    employee=leave_request.employee_id,
                )
                if form.is_valid():
                    leave_request = form.save(commit=False)
                    save = True
                    if not confirm == "True":
                        interview = InterviewSchedule.objects.filter(
                            employee_id=leave_request.employee_id.id
                        )
                        days = leave_request.requested_dates()

                        interviews = []
                        for i in interview:
                            if i.interview_date in days:
                                interviews.append(i)
                                save = False

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
                        if save:
                            leave_request.save()
                            messages.success(
                                request, _("Leave request updated successfully..")
                            )
                        elif not confirm == "True":
                            update = True
                            return render(
                                request,
                                "leave/user_leave/user_leave_confirm.html",
                                {
                                    "employee": leave_request,
                                    "interview": interviews,
                                    "title": _("Leave Request Alert."),
                                    "id": id,
                                    "update": update,
                                },
                            )
                    else:
                        form.add_error(
                            None,
                            _("You dont have enough leave days to make the request.."),
                        )
            return render(
                request,
                "leave/user_leave/user_request_update.html",
                {"form": form, "id": id, "pd": previous_data, "confirm": confirm},
            )
        else:
            messages.error(request, _("You can't update this leave request..."))
            return HttpResponse("<script>window.location.reload();</script>")
    except Exception as e:
        messages.error(request, _("User has no leave request.."))
    return render(
        request,
        "leave/user_leave/user_request_update.html",
        {"form": form, "id": id, "pd": previous_data, "confirm": confirm},
    )


@login_required
@hx_request_required
def user_request_delete(request, id):
    """
    function used to delete user leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave request id

    Returns:
    GET : return user leave request view template
    """
    previous_data = request.GET.urlencode()
    try:
        leave_request = LeaveRequest.objects.get(id=id)
        if request.user.employee_get == leave_request.employee_id:
            messages.success(request, _("Leave request deleted successfully.."))
            leave_request.delete()
    except LeaveRequest.DoesNotExist:
        messages.error(request, _("User has no leave request.."))
    except ProtectedError:
        messages.error(request, _("Related entries exists"))
    if not LeaveRequest.objects.filter(employee_id=request.user.employee_get):
        return HttpResponse("<script>window.location.reload();</script>")
    else:
        return redirect(f"/leave/user-request-filter?{previous_data}")


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
            template_name = "leave/user_leave/user_leave_empty_view.html"
        else:
            template_name = "leave/user_leave/user_leave_view.html"
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

        # Fetching leave requests
        leave_requests = queryset

        leave_requests_with_interview = []
        for leave_request in leave_requests:

            # Fetch interviews for the employee within the requested leave period
            interviews = InterviewSchedule.objects.filter(
                employee_id=leave_request.employee_id,
                interview_date__range=[
                    leave_request.start_date,
                    leave_request.end_date,
                ],
            )
            if interviews:
                # If interview exists then adding the leave request to the list
                leave_requests_with_interview.append(leave_request)

        user_request_filter = UserLeaveRequestFilter(request.GET, queryset=queryset)
        page_obj = paginator_qry(user_request_filter.qs.order_by("-id"), page_number)
        request_ids = json.dumps(
            list(page_obj.object_list.values_list("id", flat=True))
        )
        user_leave = AvailableLeave.objects.filter(employee_id=user.id).exclude(
            leave_type_id__is_compensatory_leave=True
        )
        if (
            LeaveGeneralSetting.objects.first()
            and LeaveGeneralSetting.objects.first().compensatory_leave
        ):
            user_leave = AvailableLeave.objects.filter(employee_id=user.id)
        current_date = date.today()
        return render(
            request,
            "leave/user_leave/user_request_view.html",
            {
                "leave_requests": page_obj,
                "form": user_request_filter.form,
                "pd": previous_data,
                "current_date": current_date,
                "gp_fields": MyLeaveRequestReGroup.fields,
                "request_ids": request_ids,
                "user_leaves": user_leave,
                "leave_requests_with_interview": leave_requests_with_interview,
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
        queryset = user.leaverequest_set.all().order_by("-id")
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        field = request.GET.get("field")

        # Fetching leave requests
        leave_requests = queryset

        leave_requests_with_interview = []
        for leave_request in leave_requests:

            # Fetch interviews for the employee within the requested leave period
            interviews = InterviewSchedule.objects.filter(
                employee_id=leave_request.employee_id,
                interview_date__range=[
                    leave_request.start_date,
                    leave_request.end_date,
                ],
            )
            if interviews:
                # If interview exists then adding the leave request to the list
                leave_requests_with_interview.append(leave_request)

        queryset = sortby(request, queryset, "sortby")
        user_request_filter = UserLeaveRequestFilter(request.GET, queryset).qs
        template = ("leave/user_leave/user_requests.html",)

        if field != "" and field is not None:
            user_request_filter = group_by_queryset(
                user_request_filter, field, request.GET.get("page"), "page"
            )
            list_values = [entry["list"] for entry in user_request_filter]
            id_list = []
            for value in list_values:
                for instance in value.object_list:
                    id_list.append(instance.id)

            requests_ids = json.dumps(list(id_list))
            template = "leave/user_leave/group_by.html"

        else:
            user_request_filter = paginator_qry(
                user_request_filter, request.GET.get("page")
            )
            requests_ids = json.dumps(
                [instance.id for instance in user_request_filter.object_list]
            )

        data_dict = parse_qs(previous_data)
        get_key_instances(LeaveRequest, data_dict)
        if "status" in data_dict:
            status_list = data_dict["status"]
            if len(status_list) > 1:
                data_dict["status"] = [status_list[-1]]

        user_leave = AvailableLeave.objects.filter(employee_id=user.id)

        context = {
            "leave_requests": user_request_filter,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field": field,
            "current_date": date.today(),
            "request_ids": requests_ids,
            "user_leaves": user_leave,
            "leave_requests_with_interview": leave_requests_with_interview,
        }
        return render(request, template, context=context)
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
        requests_ids_json = request.GET.get("instances_ids")
        if requests_ids_json:
            requests_ids = json.loads(requests_ids_json)
            previous_id, next_id = closest_numbers(requests_ids, id)
        return render(
            request,
            "leave/user_leave/user_request_one.html",
            {
                "leave_request": leave_request,
                "instances_ids": requests_ids_json,
                "previous": previous_id,
                "next": next_id,
            },
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
    leaves = []
    leave_requests = LeaveRequest.objects.filter(status="approved")
    requests_ids = []

    for leave_request in leave_requests:
        if today in leave_request.requested_dates():
            leaves.append(leave_request)
            requests_ids.append(leave_request.employee_id.id)

    return render(
        request, "leave/on_leave.html", {"leaves": leaves, "requests_ids": requests_ids}
    )


@login_required
def overall_leave(request):
    """
    function used to view overall leave in the company.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, data
    """

    labels = []
    data = []
    departments = Department.objects.all()
    leave_requests = LeaveRequestFilter(request.GET).qs
    for department in departments:
        count = leave_requests.filter(
            employee_id__employee_work_info__department_id=department
        ).count()
        if count:
            labels.append(department.department)
            data.append(count)
    return JsonResponse({"labels": labels, "data": data})


@login_required
@permission_required("leave.delete_leaverequest")
def dashboard(request):
    """
    function used to view Admin dashboard in the leave module.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Admin dasboard template.
    """
    requests_ids = []
    today = date.today()
    leave_requests = LeaveRequest.objects.filter(start_date__month=today.month)
    requested = LeaveRequest.objects.filter(start_date__gte=today, status="requested")
    approved = LeaveRequest.objects.filter(
        status="approved", start_date__month=today.month
    )
    rejected = LeaveRequest.objects.filter(
        status="rejected", start_date__month=today.month
    )
    holidays = Holiday.objects.filter(start_date__gte=today)
    next_holiday = (
        holidays.order_by("start_date").first() if holidays.exists() else None
    )
    holidays = holidays.filter(
        start_date__gte=today,
        start_date__month=today.month,
        start_date__year=today.year,
    ).order_by("start_date")[1:]

    leave_today = LeaveRequest.objects.filter(
        employee_id__is_active=True,
        status="approved",
        start_date__lte=today,
        end_date__gte=today,
    )

    for item in leave_today:
        requests_ids.append(item.id)

    context = {
        "leave_requests": leave_requests,
        "requested": requested,
        "approved": approved,
        "rejected": rejected,
        "next_holiday": next_holiday,
        "holidays": holidays,
        "leave_today_employees": leave_today,
        "dashboard": "dashboard",
        "today": today,
        "first_day": today.replace(day=1).strftime("%Y-%m-%d"),
        "last_day": date(
            today.year, today.month, calendar.monthrange(today.year, today.month)[1]
        ).strftime("%Y-%m-%d"),
        "requests_ids": requests_ids,
    }
    return render(request, "leave/dashboard.html", context)


@login_required
def employee_dashboard(request):
    """
    function used to view Employee dashboard in the leave module.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Employee dasboard template.
    """
    today = date.today()
    user = Employee.objects.get(employee_user_id=request.user)
    leave_requests = LeaveRequest.objects.filter(employee_id=user)
    requested = leave_requests.filter(status="requested")
    approved = leave_requests.filter(status="approved")
    rejected = leave_requests.filter(status="rejected")

    holidays = Holiday.objects.filter(start_date__gte=today)
    next_holiday = (
        holidays.order_by("start_date").first() if holidays.exists() else None
    )
    holidays = holidays.filter(
        start_date__gte=today,
        start_date__month=today.month,
        start_date__year=today.year,
    ).order_by("start_date")[1:]
    leave_requests = leave_requests.filter(
        start_date__month=today.month, start_date__year=today.year
    )
    requests_ids = [request.id for request in leave_requests]
    context = {
        "leave_requests": leave_requests,
        "requested": requested,
        "approved": approved,
        "rejected": rejected,
        "next_holiday": next_holiday,
        "holidays": holidays,
        "dashboard": "dashboard",
        "requests_ids": requests_ids,
    }
    return render(request, "leave/employee_dashboard.html", context)


@login_required
def dashboard_leave_request(request):
    """
    function used to view leave request table.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave requests table.
    """
    user = Employee.objects.get(employee_user_id=request.user)
    day = request.GET.get("date")
    if day:
        day = datetime.strptime(day, "%Y-%m")
        leave_requests = LeaveRequest.objects.filter(
            employee_id=user, start_date__month=day.month, start_date__year=day.year
        )
        requests_ids = [request.id for request in leave_requests]
    else:
        leave_requests = []
    context = {
        "leave_requests": leave_requests,
        "dashboard": "dashboard",
        "requests_ids": requests_ids,
    }
    return render(request, "leave/leave_request/dashboard_leave_requests.html", context)


@login_required
def available_leave_chart(request):
    """
    function used to generate available leave chart in employee dashboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, dataset, message.
    """
    user = Employee.objects.get(employee_user_id=request.user)
    available_leaves = AvailableLeave.objects.filter(employee_id=user).exclude(
        available_days=0
    )
    leave_count = []
    labels = []
    for leave in available_leaves:
        leave_count.append(leave.available_days + leave.carryforward_days)

        labels.append(leave.leave_type_id.name)
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
    """
    function used to generate employee leave chart in Admin dashboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, dataset, message.
    """

    day = date.today()
    if request.GET.get("date"):
        day = request.GET.get("date")
        day = datetime.strptime(day, "%Y-%m")

    leave_requests = LeaveRequest.objects.filter(
        employee_id__is_active=True, status="approved"
    )
    leave_requests = leave_requests.filter(
        start_date__month=day.month, start_date__year=day.year
    )

    leave_types = leave_requests.values_list("leave_type_id__name", flat=True)

    labels = []
    dataset = []
    for employee in leave_requests.filter(
        start_date__month=day.month, start_date__year=day.year
    ):
        labels.append(employee.employee_id)

    for leave_type in list(set(leave_types)):
        dataset.append(
            {
                "label": leave_type,
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
    """
    function used to generate department leave chart in Admin dashboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, dataset.
    """
    day = date.today()
    if request.GET.get("date"):
        day = request.GET.get("date")
        day = datetime.strptime(day, "%Y-%m")

    departments = Department.objects.all()
    department_counts = {dep.department: 0 for dep in departments}
    leave_request = LeaveRequest.objects.filter(status="approved")
    leave_request = leave_request.filter(
        start_date__month=day.month, start_date__year=day.year
    )
    leave_dates = []
    labels = []
    for leave in leave_request:
        for leave_date in leave.requested_dates():
            leave_dates.append(leave_date.strftime("%Y-%m-%d"))

        for dep in departments:
            if dep == leave.employee_id.employee_work_info.department_id:
                department_counts[dep.department] += leave.requested_days

    for department, count in department_counts.items():
        if count != 0:
            labels.append(department)
    values = list(department_counts.values())
    values = [value for value in values if value != 0]
    dataset = [
        {
            "label": _(""),
            "data": values,
        },
    ]
    response = {
        "labels": labels,
        "dataset": dataset,
        "message": _("No leave requests for this month."),
    }
    return JsonResponse(response)


@login_required
def leave_type_chart(request):
    """
    function used to generate leave type chart in Admin dashboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, dataset.
    """
    day = date.today()
    if request.GET.get("date"):
        day = request.GET.get("date")
        day = datetime.strptime(day, "%Y-%m")

    leave_types = LeaveType.objects.all()
    leave_type_count = {types.name: 0 for types in leave_types}
    leave_request = LeaveRequest.objects.filter(status="approved")
    leave_request = leave_request.filter(
        start_date__month=day.month, start_date__year=day.year
    )
    for leave in leave_request:
        for lev in leave_types:
            if lev == leave.leave_type_id:
                leave_type_count[lev.name] += leave.requested_days

    # labels = [leave_type.name for leave_type in leave_types]
    labels = []
    for leave_type, count in leave_type_count.items():
        if count != 0:
            labels.append(leave_type)
    values = list(leave_type_count.values())
    values = [value for value in values if value != 0]

    response = {
        "labels": labels,
        "dataset": [
            {
                "data": values,
            },
        ],
        "message": _("No leave requests for any leave type this month."),
    }
    return JsonResponse(response)


@login_required
def leave_over_period(request):
    """
    function used to generate leave over a week chart in Admin dashboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response of labels, dataset.
    """
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


@login_required
@hx_request_required
def leave_request_create(request):
    """
    function used to create leave request from calendar.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave request form template
    POST : return leave request view
    """
    previous_data = unquote(request.GET.urlencode())[len("pd=") :]
    emp = request.user.employee_get
    emp_id = emp.id
    confirm = request.GET.get("confirm")

    form = UserLeaveRequestCreationForm(employee=emp)
    if request.method == "POST":
        form = UserLeaveRequestCreationForm(request.POST, request.FILES, employee=emp)
        if int(form.data["employee_id"]) == int(emp_id):
            if form.is_valid():
                leave_request = form.save(commit=False)
                save = True

                if not confirm == "True":
                    interview = InterviewSchedule.objects.filter(
                        employee_id=leave_request.employee_id.id
                    )
                    days = leave_request.requested_dates()

                    interviews = []
                    for i in interview:
                        if i.interview_date in days:
                            interviews.append(i)
                            save = False

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
                    available_leave.save()
                if save:
                    leave_request.created_by = request.user.employee_get
                    leave_request.save()
                    messages.success(request, _("Leave request created successfully.."))
                    with contextlib.suppress(Exception):
                        notify.send(
                            request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"New leave request created for {leave_request.employee_id}.",
                            verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                            verb_de=f"Neuer Urlaubsantrag für {leave_request.employee_id} erstellt.",
                            verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                            verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                            icon="people-circle",
                            redirect=f"/leave/request-view?id={leave_request.id}",
                        )

                    mail_thread = LeaveMailSendThread(
                        request, leave_request, type="request"
                    )
                    mail_thread.start()
                    form = UserLeaveRequestCreationForm(employee=emp)
                    if len(LeaveRequest.objects.filter(employee_id=emp_id)) == 1:
                        return HttpResponse(
                            "<script>window.location.reload();</script>"
                        )
                elif not confirm == "True":
                    return render(
                        request,
                        "leave/user_leave/user_leave_confirm.html",
                        {
                            "employee": leave_request,
                            "interview": interviews,
                            "title": _("Leave Request Alert."),
                        },
                    )

            return render(
                request,
                "leave/user_leave/request_form.html",
                {"form": form, "pd": previous_data, "confirm": confirm},
            )
        else:
            messages.error(request, _("You don't have permission"))
            response = render(
                request, "leave/user_leave/request_form.html", {"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "leave/user_leave/request_form.html",
        {"form": form, "pd": previous_data, "confirm": confirm},
    )


@login_required
def leave_allocation_request_view(request):
    """
    function used to view leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave allocation request view template
    """
    employee = request.user.employee_get
    queryset = LeaveAllocationRequest.objects.all().order_by("-id")
    queryset = LeaveAllocationRequestFilter(request.GET, queryset).qs
    queryset = filtersubordinates(
        request, queryset, "leave.view_leaveallocationrequest"
    )
    page_number = request.GET.get("page")
    leave_allocation_requests = paginator_qry(queryset, page_number)
    requests_ids = json.dumps(
        list(leave_allocation_requests.object_list.values_list("id", flat=True))
    )
    my_leave_allocation_requests = LeaveAllocationRequest.objects.filter(
        employee_id=employee.id
    ).order_by("-id")
    my_leave_allocation_requests = LeaveAllocationRequestFilter(
        request.GET, my_leave_allocation_requests
    ).qs
    my_page_number = request.GET.get("m_page")
    my_leave_allocation_requests = paginator_qry(
        my_leave_allocation_requests, my_page_number
    )
    my_requests_ids = json.dumps(
        list(my_leave_allocation_requests.object_list.values_list("id", flat=True))
    )
    leave_allocation_request_filter = LeaveAllocationRequestFilter()
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    data_dict = get_key_instances(LeaveAllocationRequest, data_dict)
    context = {
        "leave_allocation_requests": leave_allocation_requests,
        "my_leave_allocation_requests": my_leave_allocation_requests,
        "pd": previous_data,
        "form": leave_allocation_request_filter.form,
        "filter_dict": data_dict,
        "gp_fields": LeaveAllocationRequestReGroup.fields,
        "requests_ids": requests_ids,
        "my_requests_ids": my_requests_ids,
    }
    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_request_view.html",
        context=context,
    )


@login_required
@hx_request_required
def leave_allocation_request_single_view(request, req_id):
    """
    function used to present the leave allocation request detailed view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    req_id : leave allocation request id

    Returns:
    return leave allocation request single view
    """
    my_request = False
    if request.GET.get("my_request") == "True":
        my_request = True
    requests_ids_json = request.GET.get("instances_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, req_id)
    leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
    context = {
        "leave_allocation_request": leave_allocation_request,
        "my_request": my_request,
        "instances_ids": requests_ids_json,
        "previous": previous_id,
        "next": next_id,
        "dashboard": request.GET.get("dashboard"),
    }
    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_request_single_view.html",
        context=context,
    )


@login_required
@hx_request_required
def leave_allocation_request_create(request):
    """
    function used to create leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave allocation request form template
    POST : return leave allocation request view
    """
    employee = request.user.employee_get
    form = LeaveAllocationRequestForm(initial={"employee_id": employee})
    form = choosesubordinates(request, form, "leave.add_leaveallocationrequest")
    form.fields["employee_id"].queryset = form.fields[
        "employee_id"
    ].queryset | Employee.objects.filter(employee_user_id=request.user)
    if request.method == "POST":
        form = LeaveAllocationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_allocation_request = form.save(commit=False)
            leave_allocation_request.skip_history = False
            leave_allocation_request.save()
            messages.success(request, _("New Leave allocation request is created"))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_allocation_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"New leave allocation request created for {leave_allocation_request.employee_id}.",
                    verb_ar=f"تم إنشاء طلب تخصيص إجازة جديد لـ {leave_allocation_request.employee_id}.",
                    verb_de=f"Neue Anfrage zur Urlaubszuweisung erstellt für {leave_allocation_request.employee_id}.",
                    verb_es=f"Nueva solicitud de asignación de permisos creada para {leave_allocation_request.employee_id}.",
                    verb_fr=f"Nouvelle demande d'allocation de congé créée pour {leave_allocation_request.employee_id}.",
                    icon="people-cicle",
                    redirect=f"/leave/leave-allocation-request-view?id={leave_allocation_request.id}",
                )
            response = render(
                request,
                "leave/leave_allocation_request/leave_allocation_request_create.html",
                {"form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8")
                + "<script>location. reload();</script>"
            )
    context = {"form": form}
    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_request_create.html",
        context=context,
    )


@login_required
@hx_request_required
def leave_allocation_request_filter(request):
    field = request.GET.get("field")
    employee = request.user.employee_get
    page_number = request.GET.get("page")
    my_page_number = request.GET.get("m_page")
    previous_data = request.GET.urlencode()
    template = "leave/leave_allocation_request/leave_allocation_request_list.html"

    # Filter leave allocation requests
    leave_allocation_requests_filtered = LeaveAllocationRequestFilter(
        request.GET
    ).qs.order_by("-id")
    my_leave_allocation_requests_filtered = LeaveAllocationRequest.objects.filter(
        employee_id=employee.id
    ).order_by("-id")
    my_leave_allocation_requests_filtered = LeaveAllocationRequestFilter(
        request.GET, my_leave_allocation_requests_filtered
    ).qs
    leave_allocation_requests_filtered = filtersubordinates(
        request, leave_allocation_requests_filtered, "leave.view_leaveallocationrequest"
    )

    # Sort leave allocation requests if requested
    if request.GET.get("sortby"):
        leave_allocation_requests_filtered = sortby(
            request, leave_allocation_requests_filtered, "sortby"
        )

    # Group leave allocation requests if field parameter is provided
    if field:
        leave_allocation_requests = group_by_queryset(
            leave_allocation_requests_filtered, field, page_number, "page"
        )
        my_leave_allocation_requests = group_by_queryset(
            my_leave_allocation_requests_filtered, field, my_page_number, "m_page"
        )

        # Convert IDs to JSON format for details view
        list_values = [entry["list"] for entry in leave_allocation_requests]
        id_list = [
            instance.id for value in list_values for instance in value.object_list
        ]
        requests_ids = json.dumps(list(id_list))

        list_values = [entry["list"] for entry in my_leave_allocation_requests]
        id_list = [
            instance.id for value in list_values for instance in value.object_list
        ]
        my_requests_ids = json.dumps(list(id_list))
        template = (
            "leave/leave_allocation_request/leave_allocation_request_group_by.html"
        )
    else:
        leave_allocation_requests = paginator_qry(
            leave_allocation_requests_filtered, page_number
        )
        my_leave_allocation_requests = paginator_qry(
            my_leave_allocation_requests_filtered, my_page_number
        )
        requests_ids = json.dumps(
            list(leave_allocation_requests.object_list.values_list("id", flat=True))
        )
        my_requests_ids = json.dumps(
            list(my_leave_allocation_requests.object_list.values_list("id", flat=True))
        )

    # Parse previous data and construct context for filter tag
    data_dict = parse_qs(previous_data)
    data_dict = get_key_instances(LeaveAllocationRequest, data_dict)
    data_dict.pop("m_page", None)

    context = {
        "leave_allocation_requests": leave_allocation_requests,
        "my_leave_allocation_requests": my_leave_allocation_requests,
        "pd": previous_data,
        "filter_dict": data_dict,
        "field": field,
        "requests_ids": requests_ids,
        "my_requests_ids": my_requests_ids,
    }
    return render(request, template, context=context)


@login_required
@hx_request_required
@leave_allocation_change_permission()
def leave_allocation_request_update(request, req_id):
    """
    function used to update leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    req_id : leave allocation request id

    Returns:
    GET : return leave allocation request update template
    POST : return leave allocation request view
    """
    leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
    form = LeaveAllocationRequestForm(instance=leave_allocation_request)
    form = choosesubordinates(request, form, "leave.add_leaveallocationrequest")
    form.fields["employee_id"].queryset = form.fields[
        "employee_id"
    ].queryset | Employee.objects.filter(employee_user_id=request.user)
    if leave_allocation_request.status != "approved":
        if request.method == "POST":
            form = LeaveAllocationRequestForm(
                request.POST, request.FILES, instance=leave_allocation_request
            )
            if form.is_valid():
                leave_allocation_request = form.save(commit=False)
                leave_allocation_request.skip_history = False
                leave_allocation_request.save()
                messages.success(
                    request, _("Leave allocation request is updated successfully.")
                )
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_allocation_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"Leave allocation request updated for {leave_allocation_request.employee_id}.",
                        verb_ar=f"تم تحديث طلب تخصيص الإجازة لـ {leave_allocation_request.employee_id}.",
                        verb_de=f"Urlaubszuteilungsanforderung aktualisiert für {leave_allocation_request.employee_id}.",
                        verb_es=f"Solicitud de asignación de licencia actualizada para {leave_allocation_request.employee_id}.",
                        verb_fr=f"Demande d'allocation de congé mise à jour pour {leave_allocation_request.employee_id}.",
                        icon="people-cicle",
                        redirect=f"/leave/leave-allocation-request-view?id={leave_allocation_request.id}",
                    )
                response = render(
                    request,
                    "leave/leave_allocation_request/leave_allocation_request_update.html",
                    {"form": form, "req_id": req_id},
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location. reload();</script>"
                )
        return render(
            request,
            "leave/leave_allocation_request/leave_allocation_request_update.html",
            {"form": form, "req_id": req_id},
        )
    else:
        messages.error(request, _("You can't update this request..."))
        return HttpResponse("<script>window.location.reload();</script>")


@login_required
@leave_allocation_reject_permission()
def leave_allocation_request_approve(request, req_id):
    """
    function used to approve a leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    req_id : leave allocation request id

    Returns:
    GET :It returns to the default leave allocation request view template.
    """
    leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
    if leave_allocation_request.status == "requested":
        employee = leave_allocation_request.employee_id
        if (
            employee.available_leave.all()
            .filter(leave_type_id=leave_allocation_request.leave_type_id)
            .exists()
        ):
            available_leave = (
                employee.available_leave.all()
                .filter(leave_type_id=leave_allocation_request.leave_type_id)
                .first()
            )
        else:
            available_leave = AvailableLeave(
                leave_type_id=leave_allocation_request.leave_type_id,
                employee_id=employee,
            )
        available_leave.available_days += leave_allocation_request.requested_days
        available_leave.save()
        leave_allocation_request.status = "approved"
        leave_allocation_request.save()
        messages.success(request, _("Leave allocation request approved successfully"))
        with contextlib.suppress(Exception):
            notify.send(
                request.user.employee_get,
                recipient=leave_allocation_request.employee_id.employee_user_id,
                verb="Your leave allocation request has been approved",
                verb_ar="تمت الموافقة على طلب تخصيص إجازتك",
                verb_de="Ihr Antrag auf Urlaubszuweisung wurde genehmigt",
                verb_es="Se ha aprobado su solicitud de asignación de vacaciones",
                verb_fr="Votre demande d'allocation de congé a été approuvée",
                icon="people-circle",
                redirect=f"/leave/leave-allocation-request-view?id={leave_allocation_request.id}",
            )
    else:
        messages.error(request, _("The leave allocation request can't be approved"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@hx_request_required
@leave_allocation_reject_permission()
def leave_allocation_request_reject(request, req_id):
    """
    function used to Reject leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave allocation request id

    Returns:
    GET : It returns to the default leave allocation request view template.

    """
    leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
    if (
        leave_allocation_request.status == "requested"
        or leave_allocation_request.status == "approved"
    ):
        form = LeaveAllocationRequestRejectForm()
        if request.method == "POST":
            form = LeaveAllocationRequestRejectForm(request.POST)
            if form.is_valid():
                leave_allocation_request.reject_reason = form.cleaned_data["reason"]
                if leave_allocation_request.status == "approved":
                    leave_type = leave_allocation_request.leave_type_id
                    requested_days = leave_allocation_request.requested_days
                    available_leave = AvailableLeave.objects.filter(
                        leave_type_id=leave_type,
                        employee_id=leave_allocation_request.employee_id,
                    ).first()
                    available_leave.available_days = max(
                        0, available_leave.available_days - requested_days
                    )

                    available_leave.save()
                leave_allocation_request.status = "rejected"
                leave_allocation_request.save()
                messages.success(
                    request, _("Leave allocation request rejected successfully")
                )
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_allocation_request.employee_id.employee_user_id,
                        verb="Your leave allocation request has been rejected",
                        verb_ar="تم رفض طلب تخصيص إجازتك",
                        verb_de="Ihr Antrag auf Urlaubszuweisung wurde abgelehnt",
                        verb_es="Se ha rechazado su solicitud de asignación de vacaciones",
                        verb_fr="Votre demande d'allocation de congé a été rejetée",
                        icon="people-circle",
                        redirect=f"/leave/leave-allocation-request-view?id={leave_allocation_request.id}",
                    )
                return HttpResponse("<script>location.reload();</script>")
        return render(
            request,
            "leave/leave_allocation_request/leave_allocation_request_reject_form.html",
            {"form": form, "req_id": req_id},
        )
    else:
        messages.error(request, _("The leave allocation request can't be rejected"))
        return HttpResponse("<script>location.reload();</script>")


@login_required
@hx_request_required
@leave_allocation_delete_permission()
def leave_allocation_request_delete(request, req_id):
    """
    function used to delete leave allocation request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : leave allocation request id

    Returns:
    GET : return leave allocation request view template
    """

    try:
        leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)

        if leave_allocation_request.status != "approved":
            leave_allocation_request.delete()
            messages.success(
                request, _("Leave allocation request deleted successfully..")
            )
        else:
            messages.error(request, _("Approved request can't be deleted."))
    except LeaveAllocationRequest.DoesNotExist:
        messages.error(request, _("Leave allocation request not found."))
    except OverflowError:
        messages.error(request, _("Leave allocation request not found."))

    except ProtectedError:
        messages.error(request, _("Related entries exist"))
    hx_target = request.META.get("HTTP_HX_TARGET")
    if hx_target and hx_target == "view-container":
        previous_data = request.GET.urlencode()
        leave_allocations = LeaveAllocationRequest.objects.all()
        if leave_allocations.exists():
            return redirect(f"/leave/leave-allocation-request-filter?{previous_data}")
        else:
            return HttpResponse("<script>location.reload();</script>")
    return redirect(leave_allocation_request_view)


@login_required
def assigned_leave_select(request):
    page_number = request.GET.get("page")

    if page_number == "all":
        if request.user.has_perm("leave.view_availableleave"):
            employees = AvailableLeave.objects.all()
        else:
            employees = AvailableLeave.objects.filter(
                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
            )

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def assigned_leave_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        if request.user.has_perm("leave.view_availableleave"):
            employee_filter = AssignedLeaveFilter(
                filters, queryset=AvailableLeave.objects.all()
            )
        else:
            employee_filter = AssignedLeaveFilter(
                filters,
                queryset=AvailableLeave.objects.filter(
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
def holiday_select(request):
    page_number = request.GET.get("page")

    if page_number == "all":
        employees = Holiday.objects.all()

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def holiday_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        employee_filter = HolidayFilter(filters, queryset=Holiday.objects.all())

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@require_http_methods(["POST"])
@login_required
@manager_can_enter("leave.delete_leaverequest")
def leave_request_bulk_delete(request):
    """
    This method is used to delete bulk of leaves requests
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for leave_request_id in ids:
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
            employee = leave_request.employee_id
            leave_request.delete()
            messages.success(
                request,
                _("{}'s leave request deleted.".format(employee)),
            )
        except Exception as e:
            messages.error(request, _("Leave request not found."))
    return JsonResponse({"message": "Success"})


@login_required
def leave_request_select(request):
    page_number = request.GET.get("page")

    if page_number == "all":
        if request.user.has_perm("leave.view_leaverequest"):
            employees = LeaveRequest.objects.all()
        else:
            employees = LeaveRequest.objects.filter(
                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
            )

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def leave_request_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}

    if page_number == "all":
        if request.user.has_perm("leave.view_leaverequest"):
            employee_filter = LeaveRequestFilter(
                filters, queryset=LeaveRequest.objects.all()
            )
        else:
            employee_filter = LeaveRequestFilter(
                filters,
                queryset=LeaveRequest.objects.filter(
                    employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                ),
            )

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@require_http_methods(["POST"])
@login_required
def user_request_bulk_delete(request):
    """
    This method is used to delete bulk of leaves requests
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for leave_request_id in ids:
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
            status = leave_request.status
            if leave_request.status == "requested":
                leave_request.delete()
                messages.success(
                    request,
                    _("Leave request deleted."),
                )
            else:
                messages.error(
                    request,
                    _("You cannot delete leave request with status {}.".format(status)),
                )
        except Exception as e:
            messages.error(request, _("Leave request not found."))
    return JsonResponse({"message": "Success"})


@login_required
def user_request_select(request):
    page_number = request.GET.get("page")
    user = request.user.employee_get

    if page_number == "all":
        employees = LeaveRequest.objects.filter(employee_id=user)

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
def user_request_select_filter(request):
    page_number = request.GET.get("page")
    filtered = request.GET.get("filter")
    filters = json.loads(filtered) if filtered else {}
    user = request.user.employee_get

    if page_number == "all":
        employee_filter = UserLeaveRequestFilter(
            filters, queryset=LeaveRequest.objects.filter(employee_id=user)
        )

        # Get the filtered queryset
        filtered_employees = employee_filter.qs

        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
def employee_leave_details(request):
    balance_count = ""
    if request.POST["employee_id"]:
        employee = request.POST["employee_id"]
    else:
        employee = ""
    date = request.POST.get("date", "")
    if request.POST["leave_type"] and request.POST["employee_id"]:
        leave_type_id = request.POST["leave_type"]
        leave_type = LeaveType.objects.filter(id=leave_type_id).first()
        balance = AvailableLeave.objects.filter(
            Q(leave_type_id=leave_type.id) & Q(employee_id=employee)
        )
        for i in balance:
            balance_count = i.available_days
        if date:
            try:
                balance_count += balance.first().forcasted_leaves()[date[:7]]
            except:
                pass

    return JsonResponse({"leave_count": balance_count, "employee": employee})


@login_required
@hx_request_required
@manager_can_enter("leave.change_availableleave")
def cut_available_leave(request, instance_id):
    """
    This method is used to create the penalties
    """
    previous_data = request.GET.urlencode()
    instance = LeaveRequest.objects.get(id=instance_id)
    form = PenaltyAccountForm(employee=instance.employee_id)
    available = AvailableLeave.objects.filter(employee_id=instance.employee_id)
    if request.method == "POST":
        form = PenaltyAccountForm(request.POST)
        if form.is_valid():
            penalty_instance = form.instance
            penalty = PenaltyAccount()
            # leave request id
            penalty.leave_request_id = instance
            penalty.deduct_from_carry_forward = (
                penalty_instance.deduct_from_carry_forward
            )
            penalty.employee_id = instance.employee_id
            penalty.leave_type_id = penalty_instance.leave_type_id
            penalty.minus_leaves = penalty_instance.minus_leaves
            penalty.penalty_amount = penalty_instance.penalty_amount
            penalty.save()
            form = PenaltyAccountForm()
            messages.success(request, "Penalty/Fine added")
    return render(
        request,
        "leave/leave_request/penalty/form.html",
        {
            "available": available,
            "form": form,
            "instance": instance,
            "pd": previous_data,
        },
    )


@login_required
@manager_can_enter("attendance.view_penalty")
def view_penalties(request):
    """
    This method is used to filter or view the penalties
    """
    records = PenaltyFilter(request.GET).qs
    return render(
        request, "leave/leave_request/penalty/penalty_view.html", {"records": records}
    )


@login_required
@hx_request_required
def create_leaverequest_comment(request, leave_id):
    """
    This method renders form and template to create Leave request comments
    """
    leave = LeaveRequest.objects.filter(id=leave_id).first()
    emp = request.user.employee_get
    form = LeaverequestcommentForm(
        initial={"employee_id": emp.id, "request_id": leave_id}
    )
    target = request.GET.get("target")
    url = "request-filter" if target == "leaveRequest" else "user-request-filter"
    previous_data = request.GET.urlencode()
    if request.method == "POST":
        form = LeaverequestcommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.request_id = leave
            form.save()
            comments = LeaverequestComment.objects.filter(request_id=leave_id).order_by(
                "-created_at"
            )
            no_comments = False
            if not comments.exists():
                no_comments = True
            form = LeaverequestcommentForm(
                initial={"employee_id": emp.id, "request_id": leave_id}
            )
            messages.success(request, _("Comment added successfully!"))
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=leave.employee_id
            )
            if work_info.exists():
                if (
                    leave.employee_id.employee_work_info.reporting_manager_id
                    is not None
                ):
                    if request.user.employee_get.id == leave.employee_id.id:
                        rec = (
                            leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        )
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{leave.employee_id}'s leave request has received a comment.",
                            verb_ar=f"تلقت طلب إجازة {leave.employee_id} تعليقًا.",
                            verb_de=f"{leave.employee_id}s Urlaubsantrag hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de permiso de {leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé de {leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                    elif (
                        request.user.employee_get.id
                        == leave.employee_id.employee_work_info.reporting_manager_id.id
                    ):
                        rec = leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your leave request has received a comment.",
                            verb_ar="تلقى طلب إجازتك تعليقًا.",
                            verb_de="Ihr Urlaubsantrag hat einen Kommentar erhalten.",
                            verb_es="Tu solicitud de permiso ha recibido un comentario.",
                            verb_fr="Votre demande de congé a reçu un commentaire.",
                            redirect=f"/leave/user-request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                    else:
                        rec = [
                            leave.employee_id.employee_user_id,
                            leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{leave.employee_id}'s leave request has received a comment.",
                            verb_ar=f"تلقت طلب إجازة {leave.employee_id} تعليقًا.",
                            verb_de=f"{leave.employee_id}s Urlaubsantrag hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de permiso de {leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé de {leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                else:
                    rec = leave.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your leave request has received a comment.",
                        verb_ar="تلقى طلب إجازتك تعليقًا.",
                        verb_de="Ihr Urlaubsantrag hat einen Kommentar erhalten.",
                        verb_es="Tu solicitud de permiso ha recibido un comentario.",
                        verb_fr="Votre demande de congé a reçu un commentaire.",
                        redirect=f"/leave/user-request-view?id={leave.id}",
                        icon="chatbox-ellipses",
                    )
            return render(
                request,
                "leave/leave_request/leave_comment.html",
                {
                    "comments": comments,
                    "no_comments": no_comments,
                    "request_id": leave_id,
                },
            )
    return render(
        request,
        "leave/leave_request/leave_comment.html",
        {
            "form": form,
            "request_id": leave_id,
            "pd": previous_data,
            "target": target,
            "url": url,
        },
    )


@login_required
@hx_request_required
def view_leaverequest_comment(request, leave_id):
    """
    This method is used to show Leave request comments
    """
    comments = LeaverequestComment.objects.filter(request_id=leave_id).order_by(
        "-created_at"
    )
    no_comments = False
    if not comments.exists():
        no_comments = True

    if request.FILES:
        files = request.FILES.getlist("files")
        comment_id = request.GET["comment_id"]
        comment = LeaverequestComment.objects.get(id=comment_id)
        attachments = []
        for file in files:
            file_instance = LeaverequestFile()
            file_instance.file = file
            file_instance.save()
            attachments.append(file_instance)
        comment.files.add(*attachments)

    return render(
        request,
        "leave/leave_request/leave_comment.html",
        {"comments": comments, "no_comments": no_comments, "request_id": leave_id},
    )


@login_required
def delete_comment_file(request):
    """
    Used to delete attachment
    """
    ids = request.GET.getlist("ids")
    LeaverequestFile.objects.filter(id__in=ids).delete()
    leave_id = request.GET["leave_id"]
    comments = CompensatoryLeaverequestComment.objects.all()
    if not request.user.has_perm("leave.delete_compensatoryleaverequestcomment"):
        comments = comments.filter(employee_id__employee_user_id=request.user)
    if request.GET.get("compensatory"):
        comments = comments.filter(request_id=leave_id).order_by("-created_at")
        template = "leave/compensatory_leave/compensatory_leave_comment.html"
    else:
        comments = comments.filter(request_id=leave_id).order_by("-created_at")
        template = "leave/leave_request/leave_comment.html"
    return render(
        request,
        template,
        {
            "comments": comments,
            "request_id": leave_id,
        },
    )


@login_required
@hx_request_required
def delete_leaverequest_comment(request, comment_id):
    """
    This method is used to delete Leave request comments
    """
    if request.GET.get("compensatory"):
        comment = CompensatoryLeaverequestComment.objects.filter(id=comment_id)
        if not request.user.has_perm("leave.delete_compensatoryleaverequestcomment"):
            comment = comment.filter(employee_id__employee_user_id=request.user)
        redirect_url = "view-compensatory-leave-comment"
    else:
        comment = LeaverequestComment.objects.filter(id=comment_id)
        if not request.user.has_perm("leave.delete_leaverequestcomment"):
            comment = comment.filter(employee_id__employee_user_id=request.user)
        redirect_url = "leave-request-view-comment"
    leave_id = comment.first().request_id.id
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return redirect(redirect_url, leave_id)


@login_required
@hx_request_required
def create_allocationrequest_comment(request, leave_id):
    """
    This method renders form and template to create Allocation request comments
    """
    previous_data = request.GET.urlencode()
    leave = LeaveAllocationRequest.objects.filter(id=leave_id).first()
    emp = request.user.employee_get
    form = LeaveallocationrequestcommentForm(
        initial={"employee_id": emp.id, "request_id": leave_id}
    )

    if request.method == "POST":
        form = LeaveallocationrequestcommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.request_id = leave
            form.save()
            comments = LeaveallocationrequestComment.objects.filter(
                request_id=leave_id
            ).order_by("-created_at")
            no_comments = False
            if not comments.exists():
                no_comments = True
            form = LeaveallocationrequestcommentForm(
                initial={"employee_id": emp.id, "request_id": leave_id}
            )
            messages.success(request, _("Comment added successfully!"))
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=leave.employee_id
            )
            if work_info.exists():
                if (
                    leave.employee_id.employee_work_info.reporting_manager_id
                    is not None
                ):
                    if request.user.employee_get.id == leave.employee_id.id:
                        rec = (
                            leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        )
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{leave.employee_id}'s leave allocation request has received a comment.",
                            verb_ar=f"تلقت طلب تخصيص الإجازة لـ {leave.employee_id} تعليقًا.",
                            verb_de=f"{leave.employee_id}s Anfrage zur Urlaubszuweisung hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de asignación de permisos de {leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande d'allocation de congé de {leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/leave-allocation-request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                    elif (
                        request.user.employee_get.id
                        == leave.employee_id.employee_work_info.reporting_manager_id.id
                    ):
                        rec = leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your leave allocation request has received a comment.",
                            verb_ar="تلقى طلب تخصيص الإجازة الخاص بك تعليقًا.",
                            verb_de="Ihr Antrag auf Urlaubszuweisung hat einen Kommentar erhalten.",
                            verb_es="Tu solicitud de asignación de permisos ha recibido un comentario.",
                            verb_fr="Votre demande d'allocation de congé a reçu un commentaire.",
                            redirect=f"/leave/leave-allocation-request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                    else:
                        rec = [
                            leave.employee_id.employee_user_id,
                            leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{leave.employee_id}'s leave allocation request has received a comment.",
                            verb_ar=f"تلقت طلب تخصيص الإجازة لـ {leave.employee_id} تعليقًا.",
                            verb_de=f"{leave.employee_id}s Anfrage zur Urlaubszuweisung hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de asignación de permisos de {leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande d'allocation de congé de {leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/leave-allocation-request-view?id={leave.id}",
                            icon="chatbox-ellipses",
                        )
                else:
                    rec = leave.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your leave allocation request has received a comment.",
                        verb_ar="تلقى طلب تخصيص الإجازة الخاص بك تعليقًا.",
                        verb_de="Ihr Antrag auf Urlaubszuweisung hat einen Kommentar erhalten.",
                        verb_es="Tu solicitud de asignación de permisos ha recibido un comentario.",
                        verb_fr="Votre demande d'allocation de congé a reçu un commentaire.",
                        redirect=f"/leave/leave-allocation-request-view?id={leave.id}",
                        icon="chatbox-ellipses",
                    )
            return render(
                request,
                "leave/leave_allocation_request/leave_allocation_comment.html",
                {
                    "comments": comments,
                    "no_comments": no_comments,
                    "request_id": leave_id,
                },
            )
    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_comment.html",
        {"form": form, "request_id": leave_id, "pd": previous_data},
    )


@login_required
@hx_request_required
def view_allocationrequest_comment(request, leave_id):
    """
    This method is used to show Allocation request comments
    """
    comments = LeaveallocationrequestComment.objects.filter(
        request_id=leave_id
    ).order_by("-created_at")
    no_comments = False
    if not comments.exists():
        no_comments = True

    if request.FILES:
        files = request.FILES.getlist("files")
        comment_id = request.GET["comment_id"]
        comment = LeaveallocationrequestComment.objects.get(id=comment_id)
        attachments = []
        for file in files:
            file_instance = LeaverequestFile()
            file_instance.file = file
            file_instance.save()
            attachments.append(file_instance)
        comment.files.add(*attachments)

    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_comment.html",
        {"comments": comments, "no_comments": no_comments, "request_id": leave_id},
    )


@login_required
@hx_request_required
def delete_allocationrequest_comment(request, comment_id):
    """
    This method is used to delete Allocation request comments
    """
    comment = LeaveallocationrequestComment.objects.filter(id=comment_id)
    if not request.user.has_perm("leave.delete_leaveallocationrequestcomment"):
        comment.filter(employee_id__employee_user_id=request.user)
    request_id = comment.first().request_id.id
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return redirect("allocation-request-view-comment", leave_id=request_id)


@login_required
def delete_allocation_comment_file(request):
    """
    Used to delete attachment
    """
    ids = request.GET.getlist("ids")
    if request.user.has_perm("leave.delete_leaverequestfile"):
        LeaverequestFile.objects.filter(id__in=ids).delete()
    else:
        LeaverequestFile.objects.filter(
            id__in=ids, employee_id__employee_user_id=request.user
        ).delete()

    leave_id = request.GET["leave_id"]
    comments = LeaveallocationrequestComment.objects.filter(
        request_id=leave_id
    ).order_by("-created_at")
    return render(
        request,
        "leave/leave_allocation_request/leave_allocation_comment.html",
        {
            "comments": comments,
            "request_id": leave_id,
        },
    )


@login_required
@hx_request_required
def view_clashes(request, leave_request_id):
    """
    This method is used to filter or view the leave clashes
    """
    record = get_object_or_404(LeaveRequest, id=leave_request_id)
    overlapping_requests = LeaveRequest.objects.filter(
        Q(
            employee_id__employee_work_info__department_id=record.employee_id.employee_work_info.department_id
        )
        | Q(
            employee_id__employee_work_info__job_position_id=record.employee_id.employee_work_info.job_position_id
        ),
        start_date__lte=record.end_date,
        end_date__gte=record.start_date,
    ).exclude(id=leave_request_id)

    clashed_due_to_department = overlapping_requests.filter(
        employee_id__employee_work_info__department_id=record.employee_id.employee_work_info.department_id
    )

    clashed_due_to_job_position = overlapping_requests.filter(
        employee_id__employee_work_info__job_position_id=record.employee_id.employee_work_info.job_position_id
    )

    leave_request_filter = LeaveRequestFilter(request.GET, overlapping_requests).qs
    leave_request_filter = paginator_qry(leave_request_filter, request.GET.get("page"))

    requests_ids = json.dumps(
        [instance.id for instance in leave_request_filter.object_list]
    )

    return render(
        request,
        "leave/leave_request/leave_clashes.html",
        {
            "records": overlapping_requests,
            "current_date": date.today(),
            "requests_ids": requests_ids,
            "clashed_due_to_department": clashed_due_to_department,
            "clashed_due_to_job_position": clashed_due_to_job_position,
        },
    )


@login_required
@permission_required("leave.view_leavegeneralsetting")
def compensatory_leave_settings_view(request):
    enabled_compensatory = (
        LeaveGeneralSetting.objects.exists()
        and LeaveGeneralSetting.objects.first().compensatory_leave
    )
    leave_type, create = LeaveType.objects.get_or_create(
        is_compensatory_leave=True,
        defaults={"name": "Compensatory Leave Type", "payment": "paid"},
    )
    context = {"enabled_compensatory": enabled_compensatory, "leave_type": leave_type}
    return render(request, "compensatory_settings.html", context)


@login_required
@permission_required("leave.add_leavegeneralsetting")
def enable_compensatory_leave(request):
    """
    This method is used to enable/disable the compensatory leave feature
    """
    compensatory_leave = LeaveGeneralSetting.objects.first()
    compensatory_leave = (
        compensatory_leave if compensatory_leave else LeaveGeneralSetting()
    )
    compensatory_leave.compensatory_leave = "compensatory_leave" in request.GET.keys()
    compensatory_leave.save()
    return HttpResponse(
        '<div class="oh-alert-container">\n\t<div class="oh-alert oh-alert--animated {tags}">\n\t\t{message}\n\t</div>\n</div>'.format(
            tags="success", message="Compensatory leave enabled"
        )
    )


@login_required
def get_leave_attendance_dates(request):
    """
    function used to return attendance dates that taken on leave days .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return attendance dates
    """
    if request.GET.get("employee_id"):
        employee = Employee.objects.get(id=request.GET.get("employee_id"))
        holiday_attendance = get_leave_day_attendance(employee)
        # Get a list of tuples containing (id, attendance_date)
        attendance_dates = list(holiday_attendance.values_list("id", "attendance_date"))
        form = CompensatoryLeaveForm()
        form.fields["attendance_id"].choices = attendance_dates
        attendance_id = render_to_string(
            "leave/compensatory_leave/attendance_id.html",
            {
                "form": form,
            },
        )
        return HttpResponse(f"{attendance_id}")


@login_required
@is_compensatory_leave_enabled()
def view_compensatory_leave(request):
    """
    function used to view compensatory leave requests.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return compensetory leave request view template
    """
    employee = request.user.employee_get
    queryset = CompensatoryLeaveRequest.objects.all().order_by("-id")
    queryset = CompensatoryLeaveRequestFilter(request.GET, queryset).qs
    queryset = filtersubordinates(
        request, queryset, "leave.view_compensatoryleaverequest"
    )
    page_number = request.GET.get("page")
    comp_leave_requests = paginator_qry(queryset, page_number)
    requests_ids = json.dumps(
        list(comp_leave_requests.object_list.values_list("id", flat=True))
    )
    my_comp_leave_requests = CompensatoryLeaveRequest.objects.filter(
        employee_id=employee.id
    ).order_by("-id")
    my_comp_leave_requests = CompensatoryLeaveRequestFilter(
        request.GET, my_comp_leave_requests
    ).qs
    my_page_number = request.GET.get("m_page")
    my_comp_leave_requests = paginator_qry(my_comp_leave_requests, my_page_number)
    my_requests_ids = json.dumps(
        list(my_comp_leave_requests.object_list.values_list("id", flat=True))
    )
    comp_leave_requests_filter = CompensatoryLeaveRequestFilter()
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    data_dict = get_key_instances(CompensatoryLeaveRequest, data_dict)
    context = {
        "my_comp_leave_requests": my_comp_leave_requests,
        "comp_leave_requests": comp_leave_requests,
        "pd": previous_data,
        "form": comp_leave_requests_filter.form,
        "filter_dict": data_dict,
        "gp_fields": LeaveAllocationRequestReGroup.fields,
        "requests_ids": requests_ids,
        "my_requests_ids": my_requests_ids,
    }
    return render(
        request, "leave/compensatory_leave/compensatory_leave_view.html", context
    )


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
def filter_compensatory_leave(request):
    """
    function used to view compensatory leave requests.
    """
    field = request.GET.get("field")
    employee = request.user.employee_get
    page_number = request.GET.get("page")
    my_page_number = request.GET.get("m_page")
    previous_data = request.GET.urlencode()
    template = "leave/compensatory_leave/compensatory_leave_req_list.html"

    # Filter compensatory leave requests
    comp_leave_requests_filtered = CompensatoryLeaveRequestFilter(
        request.GET
    ).qs.order_by("-id")
    my_comp_leave_requests_filtered = CompensatoryLeaveRequest.objects.filter(
        employee_id=employee.id
    ).order_by("-id")
    my_comp_leave_requests_filtered = CompensatoryLeaveRequestFilter(
        request.GET, my_comp_leave_requests_filtered
    ).qs
    comp_leave_requests_filtered = filtersubordinates(
        request, comp_leave_requests_filtered, "leave.view_leaveallocationrequest"
    )

    # Sort compensatory leave requests if requested
    if request.GET.get("sortby"):
        comp_leave_requests_filtered = sortby(
            request, comp_leave_requests_filtered, "sortby"
        )
        my_comp_leave_requests_filtered = sortby(
            request, my_comp_leave_requests_filtered, "sortby"
        )

    # Group compensatory leave requests if field parameter is provided
    if field:
        comp_leave_requests = group_by_queryset(
            comp_leave_requests_filtered, field, page_number, "page"
        )
        my_comp_leave_requests = group_by_queryset(
            my_comp_leave_requests_filtered, field, my_page_number, "m_page"
        )

        # Convert IDs to JSON format for details view
        list_values = [entry["list"] for entry in comp_leave_requests]
        id_list = [
            instance.id for value in list_values for instance in value.object_list
        ]
        requests_ids = json.dumps(list(id_list))

        list_values = [entry["list"] for entry in my_comp_leave_requests]
        id_list = [
            instance.id for value in list_values for instance in value.object_list
        ]
        my_requests_ids = json.dumps(list(id_list))
        template = (
            "leave/leave_allocation_request/leave_allocation_request_group_by.html"
        )
    else:
        comp_leave_requests = paginator_qry(comp_leave_requests_filtered, page_number)
        my_comp_leave_requests = paginator_qry(
            my_comp_leave_requests_filtered, my_page_number
        )
        requests_ids = json.dumps(
            list(comp_leave_requests.object_list.values_list("id", flat=True))
        )
        my_requests_ids = json.dumps(
            list(my_comp_leave_requests.object_list.values_list("id", flat=True))
        )

    # Parse previous data and construct context for filter tag
    data_dict = parse_qs(previous_data)
    data_dict = get_key_instances(CompensatoryLeaveRequest, data_dict)
    data_dict.pop("m_page", None)

    context = {
        "comp_leave_requests": comp_leave_requests,
        "my_comp_leave_requests": my_comp_leave_requests,
        "pd": previous_data,
        "filter_dict": data_dict,
        "field": field,
        "requests_ids": requests_ids,
        "my_requests_ids": my_requests_ids,
    }
    return render(request, template, context=context)


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
def create_compensatory_leave(request, comp_id=None):
    """
    function used to create or update compensatory leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return leave allocation request form template
    POST : return leave allocation request view
    """
    employee = request.user.employee_get
    template = "leave/compensatory_leave/comp_leave_form.html"
    instance = None
    if comp_id != None:
        instance = CompensatoryLeaveRequest.objects.get(id=comp_id)
    form = CompensatoryLeaveForm(instance=instance)
    if request.method == "POST":
        form = CompensatoryLeaveForm(request.POST, instance=instance)
        if form.is_valid():
            comp_req = form.save()
            comp_req.requested_days = attendance_days(
                comp_req.employee_id, comp_req.attendance_id.all()
            )
            comp_req.save()
            if comp_id != None:
                messages.success(request, _("Compensatory Leave updated."))
            else:
                messages.success(request, _("Compensatory Leave created."))
            return HttpResponse("<script>window.location.reload();</script>")

    context = {
        "employee": employee,
        "form": form,
    }
    return render(request, template, context)


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
@owner_can_enter(
    perm="leave.delete_compensatoryleaverequest",
    model=CompensatoryLeaveRequest,
    manager_access=True,
)
def delete_compensatory_leave(request, comp_id):
    """
    function used to delete compensatory leave request,
    and reload the list view of compensatory leave requests.
    """
    try:
        comp_leave_req = CompensatoryLeaveRequest.objects.get(id=comp_id).delete()
        messages.success(request, _("Compensatory leave request deleted."))

    except:
        messages.error(request, _("Sorry, something went wrong!"))
    com_leave_requests = CompensatoryLeaveRequest.objects.all()
    if com_leave_requests.exists():
        return redirect(filter_compensatory_leave)
    else:
        return HttpResponse("<script>location.reload();</script>")


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
@manager_can_enter(perm="leave.change_compensatoryleaverequest")
def approve_compensatory_leave(request, comp_id):
    """
    function used to approve compensatory leave request,
    and reload the list view of compensatory leave requests.
    """
    try:
        comp_leave_req = CompensatoryLeaveRequest.objects.get(id=comp_id)
        if comp_leave_req.status == "requested":
            comp_leave_req.status = "approved"
            comp_leave_req.assign_compensatory_leave_type()
            comp_leave_req.save()
            messages.success(request, _("Compensatory leave request approved."))
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=comp_leave_req.employee_id.employee_user_id,
                    verb="Your compensatory leave request has been rejected",
                    verb_ar="تمت الموافقة على طلب إجازة الاعتذار الخاص بك",
                    verb_de="Ihr Antrag auf Freizeitausgleich wurde genehmigt",
                    verb_es="Su solicitud de permiso compensatorio ha sido aprobada",
                    verb_fr="Votre demande de congé compensatoire a été approuvée",
                    redirect=f"/leave/view-compensatory-leave?id={comp_leave_req.id}",
                )
        else:
            messages.info(
                request,
                _("The compensatory leave request is not in the 'requested' status."),
            )
    except:
        messages.error(request, _("Sorry, something went wrong!"))
    if request.GET.get("individual"):
        return redirect(view_compensatory_leave)
    return redirect(filter_compensatory_leave)


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
@manager_can_enter(perm="leave.delete_compensatoryleaverequest")
def reject_compensatory_leave(request, comp_id):
    """
    function used to Reject compensatoey leave request.

    Parameters:
    request (HttpRequest): The HTTP request object.
    comp_id : compensatory leave request id

    Returns:
    GET : It returns to the default compensatory leave request view template.

    """
    comp_leave_req = CompensatoryLeaveRequest.objects.get(id=comp_id)
    if comp_leave_req.status == "requested" or comp_leave_req.status == "approved":
        form = CompensatoryLeaveRequestRejectForm()
        if request.method == "POST":
            form = CompensatoryLeaveRequestRejectForm(request.POST)
            if form.is_valid():
                comp_leave_req.reject_reason = form.cleaned_data["reason"]
                comp_leave_req.status = "rejected"
                comp_leave_req.exclude_compensatory_leave()
                comp_leave_req.save()
                messages.success(request, _("Compensatory Leave request rejected."))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=comp_leave_req.employee_id.employee_user_id,
                        verb="Your compensatory leave request has been rejected",
                        verb_ar="تم رفض طلبك للإجازة التعويضية",
                        verb_de="Ihr Antrag auf Freizeitausgleich wurde abgelehnt",
                        verb_es="Se ha rechazado su solicitud de permiso compensatorio",
                        verb_fr="Votre demande de congé compensatoire a été rejetée",
                        redirect=f"/leave/view-compensatory-leave?id={comp_leave_req.id}",
                    )
                return HttpResponse("<script>location.reload();</script>")
        return render(
            request,
            "leave/compensatory_leave/compensatory_leave_reject_form..html",
            {"form": form, "comp_id": comp_id},
        )
    else:
        messages.error(request, _("The leave allocation request can't be rejected"))
        return HttpResponse("<script>location.reload();</script>")


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
def compensatory_leave_individual_view(request, comp_leave_id):
    """
    function used to present the compensatory leave request detailed view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    comp_leave_id : compensatory leave request id

    Returns:
    return compensatory leave request single view
    """
    requests_ids_json = request.GET.get("instances_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, comp_leave_id)
    comp_leave_req = CompensatoryLeaveRequest.objects.get(id=comp_leave_id)
    context = {
        "comp_leave_req": comp_leave_req,
        "my_request": eval(request.GET.get("my_request")),
        "instances_ids": requests_ids_json,
        "previous": previous_id,
        "next": next_id,
    }
    return render(
        request,
        "leave/compensatory_leave/individual_view_compensatory.html",
        context=context,
    )


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
def view_compensatory_leave_comment(request, comp_leave_id):
    """
    This method is used to show Leave request comments
    """
    comments = CompensatoryLeaverequestComment.objects.filter(
        request_id=comp_leave_id
    ).order_by("-created_at")
    no_comments = False
    if not comments.exists():
        no_comments = True

    if request.FILES:
        files = request.FILES.getlist("files")
        comment_id = request.GET["comment_id"]
        comment = CompensatoryLeaverequestComment.objects.get(id=comment_id)
        attachments = []
        for file in files:
            file_instance = LeaverequestFile()
            file_instance.file = file
            file_instance.save()
            attachments.append(file_instance)
        comment.files.add(*attachments)

    return render(
        request,
        "leave/compensatory_leave/compensatory_leave_comment.html",
        {"comments": comments, "no_comments": no_comments, "request_id": comp_leave_id},
    )


@login_required
@is_compensatory_leave_enabled()
@hx_request_required
def create_compensatory_leave_comment(request, comp_leave_id):
    """
    This method renders form and template to create Compensatory leave comments
    """
    comp_leave = CompensatoryLeaveRequest.objects.filter(id=comp_leave_id).first()
    emp = request.user.employee_get
    form = CompensatoryLeaveRequestcommentForm(
        initial={"employee_id": emp.id, "request_id": comp_leave}
    )
    target = request.GET.get("target")
    url = "request-filter" if target == "leaveRequest" else "user-request-filter"
    previous_data = request.GET.urlencode()
    if request.method == "POST":
        form = CompensatoryLeaveRequestcommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.request_id = comp_leave
            form.save()
            comments = CompensatoryLeaverequestComment.objects.filter(
                request_id=comp_leave
            ).order_by("-created_at")
            no_comments = False
            if not comments.exists():
                no_comments = True
            form = CompensatoryLeaveRequestcommentForm(
                initial={"employee_id": emp.id, "request_id": comp_leave}
            )
            messages.success(request, _("Comment added successfully!"))
            work_info = EmployeeWorkInformation.objects.filter(
                employee_id=comp_leave.employee_id
            )
            if work_info.exists():
                if (
                    comp_leave.employee_id.employee_work_info.reporting_manager_id
                    is not None
                ):
                    if request.user.employee_get.id == comp_leave.employee_id.id:
                        rec = (
                            comp_leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        )
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{comp_leave.employee_id}'s Compensatory leave request has received a comment.",
                            verb_ar=f"تلقى طلب إجازة الاعتذار لـ {comp_leave.employee_id} تعليقًا.",
                            verb_de=f"Der Antrag auf Freizeitausgleich von {comp_leave.employee_id} hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de permiso compensatorio de {comp_leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé compensatoire de {comp_leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/view-compensatory-leave?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                    elif (
                        request.user.employee_get.id
                        == comp_leave.employee_id.employee_work_info.reporting_manager_id.id
                    ):
                        rec = comp_leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your compensatory leave request has received a comment.",
                            verb_ar="تلقى طلب إجازة العوض الخاص بك تعليقًا.",
                            verb_de="Ihr Antrag auf Freizeitausgleich hat einen Kommentar erhalten.",
                            verb_es="Su solicitud de permiso compensatorio ha recibido un comentario.",
                            verb_fr="Votre demande de congé compensatoire a reçu un commentaire.",
                            redirect=f"/leave/view-compensatory-leave?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                    else:
                        rec = [
                            comp_leave.employee_id.employee_user_id,
                            comp_leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{comp_leave.employee_id}'s compensatory leave request has received a comment.",
                            verb_ar=f"تلقى طلب إجازة التعويض لـ {comp_leave.employee_id} تعليقًا.",
                            verb_de=f"Der Antrag auf Freizeitausgleich von {comp_leave.employee_id} hat einen Kommentar erhalten.",
                            verb_es=f"El pedido de permiso compensatorio de {comp_leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé compensatoire de {comp_leave.employee_id} a reçu un commentaire.",
                            redirect=f"/leave/view-compensatory-leave?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                else:
                    rec = comp_leave.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your compensatory leave request has received a comment.",
                        verb_ar="تلقى طلب إجازة العوض الخاص بك تعليقًا.",
                        verb_de="Ihr Antrag auf Freizeitausgleich hat einen Kommentar erhalten.",
                        verb_es="Su solicitud de permiso compensatorio ha recibido un comentario.",
                        verb_fr="Votre demande de congé compensatoire a reçu un commentaire.",
                        redirect=f"/leave/view-compensatory-leave?id={comp_leave.id}",
                        icon="chatbox-ellipses",
                    )
            return render(
                request,
                "leave/compensatory_leave/compensatory_leave_comment.html",
                {
                    "comments": comments,
                    "no_comments": no_comments,
                    "request_id": comp_leave_id,
                },
            )
    return render(
        request,
        "leave/compensatory_leave/compensatory_leave_comment.html",
        {
            "form": form,
            "request_id": comp_leave_id,
            "pd": previous_data,
            "target": target,
            "url": url,
        },
    )
