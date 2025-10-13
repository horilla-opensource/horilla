"""
views.py

This module contains the view functions for handling HTTP requests and rendering
responses in your application.

Each view function corresponds to a specific URL route and performs the necessary
actions to handle the request, process data, and generate a response.

This module is part of the recruitment project and is intended to
provide the main entry points for interacting with the application's functionality.
"""

import ast
import calendar
import json
import operator
import os
import threading
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import F, ProtectedError
from django.db.models.query import QuerySet
from django.forms import DateInput, Select
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from accessibility.decorators import enter_if_accessible
from accessibility.methods import update_employee_accessibility_cache
from accessibility.middlewares import ACCESSIBILITY_CACHE_USER_KEYS
from accessibility.models import DefaultAccessibility
from base.forms import ModelForm
from base.methods import (
    choosesubordinates,
    filtersubordinates,
    filtersubordinatesemployeemodel,
    get_key_instances,
    get_pagination,
    sortby,
)
from base.models import (
    Company,
    Department,
    EmailLog,
    JobPosition,
    JobRole,
    RotatingShiftAssign,
    RotatingWorkTypeAssign,
    ShiftRequest,
    WorkTypeRequest,
)
from base.views import generate_error_report
from employee.filters import DocumentRequestFilter, EmployeeFilter, EmployeeReGroup
from employee.forms import (
    BonusPointAddForm,
    BonusPointRedeemForm,
    BulkUpdateFieldForm,
    EmployeeBankDetailsForm,
    EmployeeBankDetailsUpdateForm,
    EmployeeExportExcelForm,
    EmployeeForm,
    EmployeeGeneralSettingPrefixForm,
    EmployeeNoteForm,
    EmployeeTagForm,
    EmployeeWorkInformationForm,
    EmployeeWorkInformationUpdateForm,
    excel_columns,
)
from employee.methods.methods import (
    bulk_create_department_import,
    bulk_create_employee_import,
    bulk_create_employee_types,
    bulk_create_job_position_import,
    bulk_create_job_role_import,
    bulk_create_shifts,
    bulk_create_user_import,
    bulk_create_work_info_import,
    bulk_create_work_types,
    error_data_template,
    get_ordered_badge_ids,
    process_employee_records,
    set_initial_password,
    valid_import_file_headers,
)
from employee.models import (
    BonusPoint,
    Employee,
    EmployeeBankDetails,
    EmployeeGeneralSetting,
    EmployeeNote,
    EmployeeTag,
    EmployeeWorkInformation,
    NoteFiles,
)
from horilla.decorators import (
    hx_request_required,
    logger,
    login_required,
    manager_can_enter,
    owner_can_enter,
    permission_required,
)
from horilla.filters import HorillaPaginator
from horilla.group_by import group_by_queryset
from horilla.horilla_settings import HORILLA_DATE_FORMATS
from horilla.methods import get_horilla_model_class
from horilla_audit.models import AccountBlockUnblock, HistoryTrackingFields
from horilla_documents.forms import (
    DocumentForm,
    DocumentRejectForm,
    DocumentRequestForm,
    DocumentUpdateForm,
)
from horilla_documents.models import Document, DocumentRequest
from notifications.signals import notify


def return_none(a, b):
    return None


operator_mapping = {
    "equal": operator.eq,
    "notequal": operator.ne,
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
    "icontains": operator.contains,
    "range": return_none,
}
filter_mapping = {
    "work_type_id": {
        "filter": lambda employee, allowance: {
            "employee_id": employee,
            "work_type_id__id": allowance.work_type_id.id,
            "attendance_validated": True,
        }
    },
    "shift_id": {
        "filter": lambda employee, allowance,: {
            "employee_id": employee,
            "shift_id__id": allowance.shift_id.id,
            "attendance_validated": True,
        }
    },
    "overtime": {
        "filter": lambda employee, allowance: {
            "employee_id": employee,
            "attendance_overtime_approve": True,
            "attendance_validated": True,
        }
    },
    "attendance": {
        "filter": lambda employee, allowance: {
            "employee_id": employee,
            "attendance_validated": True,
        }
    },
}


def _check_reporting_manager(request, *args, **kwargs):
    if kwargs.get("obj_id"):
        obj_id = kwargs["obj_id"]
        emp = Employee.objects.get(id=obj_id)
        re_manager = None
        if emp.employee_work_info.reporting_manager_id != None:
            re_manager = emp.employee_work_info.reporting_manager_id
        employee = request.user.employee_get
        if re_manager != None:
            return re_manager == employee
        else:
            return False
    return request.user.employee_get.reporting_manager.exists()


@login_required
def get_language_code(request):
    """
    Retrieve the language code for the current request.

    This view function extracts the LANGUAGE_CODE from the request object and
    returns it as a JSON response. This function requires the user to be logged in.
    """
    language_code = request.LANGUAGE_CODE
    return JsonResponse({"language_code": language_code})


@login_required
def employee_profile(request):
    """
    This method is used to view own profile of employee.
    """
    employee = request.user.employee_get
    selected_company = request.session.get("selected_company")
    if selected_company != "all":
        company_id = getattr(
            getattr(getattr(employee, "employee_work_info", None), "company_id", None),
            "id",
            None,
        )

        if str(company_id) != str(selected_company):
            messages.error(request, "Employee is not working in the selected company.")
            return redirect("employee-view")

    today = datetime.today()
    now = timezone.now()
    return render(
        request,
        "employee/profile/profile_view.html",
        {
            "employee": employee,
            "current_date": today,
            "now": now,
        },
    )


@login_required
@enter_if_accessible(
    feature="profile_edit",
    perm="employee.change_employee",
)
def self_info_update(request):
    """
    This method is used to update own profile of an employee.
    """
    user = request.user
    employee = Employee.objects.filter(employee_user_id=user).first()
    badge_id = employee.badge_id
    bank_form = EmployeeBankDetailsForm(
        instance=EmployeeBankDetails.objects.filter(employee_id=employee).first()
    )
    form = EmployeeForm(instance=Employee.objects.filter(employee_user_id=user).first())
    if request.POST:
        if request.POST.get("employee_first_name") is not None:
            instance = Employee.objects.filter(employee_user_id=request.user).first()
            form = EmployeeForm(request.POST, instance=instance)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.employee_user_id = user
                if instance.badge_id is None:
                    instance.badge_id = badge_id
                instance.save()
                messages.success(request, _("Profile updated."))
        elif request.POST.get("any_other_code1") is not None:
            instance = EmployeeBankDetails.objects.filter(employee_id=employee).first()
            bank_form = EmployeeBankDetailsForm(request.POST, instance=instance)
            if bank_form.is_valid():
                instance = bank_form.save(commit=False)
                instance.employee_id = employee
                instance.save()
                messages.success(request, _("Bank details updated."))
    return render(
        request,
        "employee/profile/profile.html",
        {
            "form": form,
            "bank_form": bank_form,
        },
    )


def profile_edit_access(request, emp_id):
    feature = request.GET.get("feature", None)
    accessibility = DefaultAccessibility.objects.filter(feature=feature).first()
    if accessibility:
        employees = Employee.objects.filter(id=emp_id)

        if employee := employees.first():
            if employee in accessibility.employees.all():
                accessibility.employees.remove(employee)
            else:
                accessibility.employees.add(employee)

            user_cache_key = ACCESSIBILITY_CACHE_USER_KEYS.get(
                employees.first().employee_user_id.id, None
            )
            if user_cache_key:
                cache.delete(user_cache_key[-1])
                update_employee_accessibility_cache(user_cache_key[-1], employee)

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@enter_if_accessible(
    feature="employee_detailed_view",
    perm="employee.view_employee",
    method=_check_reporting_manager,
)
def employee_view_individual(request, obj_id, **kwargs):
    """
    This method is used to view profile of an employee.
    """
    try:
        employee = Employee.objects.get(id=obj_id)
    except ObjectDoesNotExist:
        try:
            employee = Employee.objects.entire().get(id=obj_id)
            company = getattr(
                getattr(employee, "employee_work_info", None), "company_id", None
            )
            company_id = getattr(company, "pk", None)
            if company_id != request.session["selected_company"]:
                messages.error(
                    request, "Employee is not working in the selected company."
                )
                return redirect("employee-view")
        except Exception as e:
            return render(request, "404.html", status=404)

    employee_leaves = (
        employee.available_leave.all() if apps.is_installed("leave") else None
    )
    enabled_block_unblock = (
        AccountBlockUnblock.objects.exists()
        and AccountBlockUnblock.objects.first().is_enabled
    )
    # Retrieve the filtered employees from the session
    filtered_employee_ids = request.session.get("filtered_employees", [])
    filtered_employees = Employee.objects.filter(id__in=filtered_employee_ids)

    request_ids_str = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                filtered_employees, request.GET.get("page")
            ).object_list
        ]
    )

    # Convert the string to an actual list of integers
    requests_ids = (
        ast.literal_eval(request_ids_str)
        if isinstance(request_ids_str, str)
        else request_ids_str
    )

    employee_id = employee.id
    previous_id = None
    next_id = None

    for index, req_id in enumerate(requests_ids):
        if req_id == employee_id:

            if index == len(requests_ids) - 1:
                next_id = None
            else:
                next_id = requests_ids[index + 1]
            if index == 0:
                previous_id = None
            else:
                previous_id = requests_ids[index - 1]
            break

    context = {
        "employee": employee,
        "previous": previous_id,
        "next": next_id,
        "requests_ids": requests_ids,
        "current_date": date.today(),
        "leave_request_ids": json.dumps([]),
        "enabled_block_unblock": enabled_block_unblock,
    }
    # if the requesting user opens own data
    if request.user.employee_get == employee:
        context["user_leaves"] = employee_leaves
    else:
        context["employee_leaves"] = employee_leaves

    return render(
        request,
        "employee/view/individual.html",
        context,
    )


@login_required
@hx_request_required
def about_tab(request, obj_id, **kwargs):
    """
    This method is used to view profile of an employee.
    """
    employee = Employee.objects.get(id=obj_id)
    contracts = employee.contract_set.all() if apps.is_installed("payroll") else None
    employee_leaves = (
        employee.available_leave.all() if apps.is_installed("leave") else None
    )
    return render(
        request,
        "tabs/personal_tab.html",
        {
            "employee": employee,
            "employee_leaves": employee_leaves,
            "contracts": contracts,
        },
    )


@login_required
@hx_request_required
@owner_can_enter("perms.employee.view_employee", Employee)
def shift_tab(request, emp_id):
    """
    This function is used to view shift tab of an employee in employee individual & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return shift-tab template
    """
    employee = Employee.objects.get(id=emp_id)
    work_type_requests = WorkTypeRequest.objects.filter(employee_id=emp_id)
    work_type_requests_ids = json.dumps(
        [instance.id for instance in work_type_requests]
    )
    rshift_assign = RotatingShiftAssign.objects.filter(employee_id=emp_id)
    rshift_assign_ids = json.dumps([instance.id for instance in rshift_assign])
    rwork_type_assign = RotatingWorkTypeAssign.objects.filter(employee_id=emp_id)
    rwork_type_assign_ids = json.dumps([instance.id for instance in rwork_type_assign])
    shift_requests = ShiftRequest.objects.filter(employee_id=emp_id)
    shift_requests_ids = json.dumps([instance.id for instance in shift_requests])

    context = {
        "work_data": work_type_requests,
        "work_type_requests_ids": work_type_requests_ids,
        "rshift_assign": rshift_assign,
        "rshift_assign_ids": rshift_assign_ids,
        "rwork_type_assign": rwork_type_assign,
        "rwork_type_assign_ids": rwork_type_assign_ids,
        "shift_data": shift_requests,
        "shift_requests_ids": shift_requests_ids,
        "emp_id": emp_id,
        "employee": employee,
    }
    return render(request, "tabs/shift-tab.html", context=context)


@login_required
@manager_can_enter("horilla_documents.view_documentrequest")
def document_request_view(request):
    """
    This function is used to view and filter document requests of employees.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    Render 'documents/document_requests.html' with documents and filters.
    """
    previous_data = request.GET.urlencode()
    filter_class = DocumentRequestFilter(request.GET or None)
    document_requests = DocumentRequest.objects.all()
    documents = Document.objects.filter(document_request_id__isnull=False)
    documents = filtersubordinates(
        request=request,
        perm="horilla_documents.view_documentrequest",
        queryset=documents,
    )

    if request.GET:
        filtered_docs = filter_class.qs
        filtered_docs = filtered_docs.filter(document_request_id__isnull=False)
        documents = filtered_docs

    documents = group_by_queryset(
        documents, "document_request_id", request.GET.get("page"), "page"
    )
    data_dict = parse_qs(previous_data)
    get_key_instances(Document, data_dict)
    context = {
        "document_requests": document_requests,
        "documents": documents,
        "f": filter_class,
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, "documents/document_requests.html", context=context)


@login_required
@hx_request_required
@manager_can_enter("horilla_documents.view_documentrequest")
def document_filter_view(request):
    """
    This method is used to filter employee.
    """
    document_requests = DocumentRequest.objects.all()
    previous_data = request.GET.urlencode()
    documents = DocumentRequestFilter(request.GET).qs
    documents = documents.exclude(document_request_id__isnull=True).order_by(
        "-document_request_id"
    )
    documents = group_by_queryset(
        documents, "document_request_id", request.GET.get("page"), "page"
    )
    # documents = paginator_qry(documents,request.GET.get("page"))
    data_dict = parse_qs(previous_data)
    get_key_instances(Document, data_dict)

    return render(
        request,
        "documents/requests.html",
        {
            "documents": documents,
            "f": EmployeeFilter(request.GET),
            "pd": previous_data,
            "filter_dict": data_dict,
            "document_requests": document_requests,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("horilla_documents.add_documentrequest")
def document_request_create(request):
    """
    This function is used to create document requests of an employee in employee requests view.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns: return document_request_create_form template
    """
    form = DocumentRequestForm()
    form = choosesubordinates(request, form, "horilla_documents.add_documentrequest")
    if request.method == "POST":
        form = DocumentRequestForm(request.POST)
        form = choosesubordinates(
            request, form, "horilla_documents.add_documentrequest"
        )
        if form.is_valid():
            form = form.save()
            messages.success(request, _("Document request created successfully"))
            employees = [user.employee_user_id for user in form.employee_id.all()]

            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb=f"{request.user.employee_get} requested a document.",
                verb_ar=f"طلب {request.user.employee_get} مستنداً.",
                verb_de=f"{request.user.employee_get} hat ein Dokument angefordert.",
                verb_es=f"{request.user.employee_get} solicitó un documento.",
                verb_fr=f"{request.user.employee_get} a demandé un document.",
                redirect=reverse("employee-profile"),
                icon="chatbox-ellipses",
            )
            return HttpResponse("<script>window.location.reload();</script>")

    context = {
        "form": form,
    }
    return render(
        request, "documents/document_request_create_form.html", context=context
    )


@login_required
@hx_request_required
@manager_can_enter("horilla_documents.change_documentrequest")
def document_request_update(request, id):
    """
    This function is used to update document requests of an employee in employee requests view.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns: return document_request_create_form template
    """
    document_request = get_object_or_404(DocumentRequest, id=id)
    documents = Document.objects.filter(document_request_id=document_request.id)
    form = DocumentRequestForm(instance=document_request)
    if request.method == "POST":
        form = DocumentRequestForm(request.POST, instance=document_request)
        if form.is_valid():
            doc_obj = form.save()
            doc_obj.employee_id.set(
                Employee.objects.filter(id__in=form.data.getlist("employee_id"))
            )
            documents.exclude(employee_id__in=doc_obj.employee_id.all()).delete()
            return HttpResponse("<script>window.location.reload();</script>")

    context = {
        "form": form,
        "document_request": document_request,
    }
    return render(
        request, "documents/document_request_create_form.html", context=context
    )


@login_required
@hx_request_required
@owner_can_enter("horilla_documents.view_document", Employee)
def document_tab(request, emp_id):
    """
    This function is used to view documents tab of an employee in employee individual
    & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return document_tab template
    """

    form = DocumentUpdateForm(request.POST, request.FILES)
    documents = Document.objects.filter(employee_id=emp_id)

    context = {
        "documents": documents,
        "form": form,
        "emp_id": emp_id,
    }
    return render(request, "tabs/document_tab.html", context=context)


@login_required
@hx_request_required
@owner_can_enter("horilla_documents.add_document", Employee)
def document_create(request, emp_id):
    """
    This function is used to create documents from employee individual & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee

    Returns: return document_tab template
    """
    employee_id = Employee.objects.get(id=emp_id)
    form = DocumentForm(initial={"employee_id": employee_id, "expiry_date": None})
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Document created successfully."))
            return HttpResponse("<script>window.location.reload();</script>")

    context = {
        "form": form,
        "emp_id": emp_id,
    }
    return render(request, "tabs/htmx/document_create_form.html", context=context)


@login_required
def update_document_title(request, id):
    """
    This function is used to create documents from employee individual & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns: return document_tab template
    """
    document = get_object_or_404(Document, id=id)
    name = request.POST.get("title")
    if request.method == "POST":
        document.title = name
        document.save()
        messages.success(request, _("Document title updated successfully"))
    else:
        messages.error(request, _("Invalid request"))
    return HttpResponse("")


@login_required
@hx_request_required
def document_delete(request, id):
    """
    Handle the deletion of a document, with permissions and error handling.

    This view function attempts to delete a document specified by its ID.
    If the user does not have the "delete_document" permission, it restricts
    deletion to documents owned by the user. It provides appropriate success
    or error messages based on the outcome. If the document is protected and
    cannot be deleted, it handles the exception and informs the user.
    """
    try:
        document = Document.objects.filter(id=id)
        if not request.user.has_perm("horilla_documents.delete_document"):
            document = document.filter(
                employee_id__employee_user_id=request.user
            ).exclude(document_request_id__isnull=False)
        if document:
            document_first = document.first()
            document.delete()
            messages.success(
                request,
                _(
                    f"Document request {document_first} for {document_first.employee_id} deleted successfully"
                ),
            )
            referrer = request.META.get("HTTP_REFERER", "")
            referrer = "/" + "/".join(referrer.split("/")[3:])
            if referrer.startswith("/employee/employee-view/") or referrer.endswith(
                "/employee/employee-profile/"
            ):
                existing_documents = Document.objects.filter(
                    employee_id=document_first.employee_id
                )
                if not existing_documents:
                    return HttpResponse(
                        f"""
                            <span hx-get='/employee/document-tab/{document_first.employee_id.id}?employee_view=true'
                            hx-target='#document_target' hx-trigger='load'></span>
                        """
                    )
            return HttpResponse("<script>$('#reloadMessagesButton').click();</script>")
        else:
            messages.error(request, _("Document not found"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this document."))
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@hx_request_required
def file_upload(request, id):
    """
    This function is used to upload documents of an employee in employee individual & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    Returns: return document_form template
    """

    document_item = Document.objects.get(id=id)
    form = DocumentUpdateForm(instance=document_item)
    if request.method == "POST":
        form = DocumentUpdateForm(request.POST, request.FILES, instance=document_item)
        if form.is_valid():
            form.save()
            messages.success(request, _("Document uploaded successfully"))
            try:
                notify.send(
                    request.user.employee_get,
                    recipient=request.user.employee_get.get_reporting_manager().employee_user_id,
                    verb=f"{request.user.employee_get} uploaded a document",
                    verb_ar=f"قام {request.user.employee_get} بتحميل مستند",
                    verb_de=f"{request.user.employee_get} hat ein Dokument hochgeladen",
                    verb_es=f"{request.user.employee_get} subió un documento",
                    verb_fr=f"{request.user.employee_get} a téléchargé un document",
                    redirect=reverse(
                        "employee-view-individual",
                        kwargs={"obj_id": request.user.employee_get.id},
                    ),
                    icon="chatbox-ellipses",
                )
            except:
                pass
            return HttpResponse("<script>window.location.reload();</script>")
        else:
            logger.error(f"Document upload form errors: {form.errors}")
    context = {"form": form, "document": document_item}
    return render(request, "tabs/htmx/document_form.html", context=context)


@login_required
@hx_request_required
def view_file(request, id):
    """
    This function used to view the uploaded document in the modal.
    Parameters:

    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    Returns: return view_file template
    """

    document_obj = Document.objects.filter(id=id).first()
    context = {
        "document": document_obj,
    }
    if document_obj.document:
        file_path = document_obj.document.path
        file_extension = os.path.splitext(file_path)[1][
            1:
        ].lower()  # Get the lowercase file extension

        content_type = get_content_type(file_extension)

        try:
            with open(file_path, "rb") as file:
                file_content = file.read()  # Decode the binary content for display
        except:
            file_content = None

        context["file_content"] = file_content
        context["file_extension"] = file_extension
        context["content_type"] = content_type

    return render(request, "tabs/htmx/view_file.html", context)


def get_content_type(file_extension):
    """
    This function retuns the content type of a file
    parameters:

    file_extension: The file extension of the file
    """

    content_types = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "jpg": "image/jpeg",
        "png": "image/png",
        "jpeg": "image/jpeg",
    }

    # Default to application/octet-stream if the file extension is not recognized
    return content_types.get(file_extension, "application/octet-stream")


@login_required
@hx_request_required
@manager_can_enter("horilla_documents.add_document")
def document_approve(request, id):
    """
    This function used to view the approve uploaded document.
    Parameters:

    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    Returns:
    """

    document_obj = get_object_or_404(Document, id=id)
    refresh_url = request.GET.get("refresh_url") or request.POST.get("refresh_url")
    hx_target = request.GET.get("hx_target") or request.POST.get("hx_target")
    hx_select = request.GET.get("hx_select") or request.POST.get("hx_select")
    hx_swap = request.GET.get("hx_swap") or request.POST.get("hx_swap")
    if document_obj.document:
        document_obj.status = "approved"
        document_obj.save()
        messages.success(request, _("Document request approved"))
    else:
        messages.error(request, _("No document uploaded"))
    # 918
    if refresh_url:
        attrs = []
        if hx_target:
            attrs.append(f'hx-target="{hx_target}"')
        if hx_select:
            attrs.append(f'hx-select="{hx_select}"')
        if hx_swap:
            attrs.append(f'hx-swap="{hx_swap}"')

        span = f"""
        <span
            hx-trigger="load"
            hx-get="{refresh_url}"
            {' '.join(attrs)}
            >
        </span>
        """
        return HttpResponse(span)

    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@hx_request_required
@manager_can_enter("horilla_documents.add_document")
def document_reject(request, id):
    """
    This function used to view the reject uploaded document.
    Parameters:

    request (HttpRequest): The HTTP request object.
    id (int): The id of the document.

    Returns:
    """
    document_obj = get_object_or_404(Document, id=id)
    form = DocumentRejectForm()
    if document_obj.document:
        if request.method == "POST":
            form = DocumentRejectForm(request.POST, instance=document_obj)
            if form.is_valid():
                test = form.save()
                document_obj.status = "rejected"
                document_obj.save()
                messages.error(request, _("Document request rejected"))

                return HttpResponse("<script>window.location.reload();</script>")
    else:
        messages.error(request, _("No document uploaded"))
        return HttpResponse("<script>window.location.reload();</script>")

    return render(
        request,
        "tabs/htmx/reject_form.html",
        {"form": form, "document_obj": document_obj},
    )


@login_required
@manager_can_enter("horilla_documents.add_document")
def document_bulk_approve(request):
    """
    This function is used to bulk-approve uploaded documents.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A 204 No Content response with HX-Refresh header.
    """
    if request.method == "POST":
        ids = request.POST.getlist("ids")

        # Documents with uploaded files
        approved_docs = Document.objects.filter(id__in=ids).exclude(document="")
        count_approved = approved_docs.update(status="approved")

        # Documents without uploaded files
        not_uploaded_count = len(ids) - approved_docs.count()

        if count_approved:
            messages.success(
                request, _(f"{count_approved} document request(s) approved")
            )

        if not_uploaded_count:
            messages.info(
                request, _(f"{not_uploaded_count} document(s) skipped (not uploaded)")
            )

    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@manager_can_enter("horilla_documents.add_document")
def document_bulk_reject(request):
    """
    Handle bulk rejection of documents.

    On GET request, display a form to enter the rejection reason for selected documents.
    On POST request, validate the rejection reason and update the status of documents
    (excluding those already rejected) to 'rejected' with the provided reason.
    """
    ids = (
        request.POST.getlist("ids")
        if request.method == "POST"
        else request.GET.getlist("ids")
    )
    form = DocumentRejectForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        reject_reason = form.cleaned_data["reject_reason"]
        updated_count = (
            Document.objects.filter(id__in=ids)
            .exclude(status="rejected")
            .update(status="rejected", reject_reason=reject_reason)
        )
        messages.success(
            request, _("{} Document request rejected").format(updated_count)
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    return render(
        request, "documents/document_reject_reason.html", {"ids": ids, "form": form}
    )


@login_required
@require_http_methods(["POST"])
def employee_profile_bank_details(request):
    """
    This method is used to fill self bank details
    """
    employee = request.user.employee_get
    instance = EmployeeBankDetails.objects.filter(employee_id=employee).first()
    form = EmployeeBankDetailsUpdateForm(request.POST, instance=instance)
    if form.is_valid():
        bank_info = form.save(commit=False)
        bank_info.employee_id = employee
        bank_info.save()
        messages.success(request, _("Bank details updated"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


@login_required
@permission_required("employee.view_profile")
def employee_profile_update(request):
    """
    This method is used update own profile of the requested employee
    """

    employee_user = request.user
    employee = Employee.objects.get(employee_user_id=employee_user)
    if employee_user.has_perm("employee.change_profile"):
        if request.method == "POST":
            form = EmployeeForm(request.POST, request.FILES, instance=employee)
            if form.is_valid():
                form.save()
                messages.success(request, _("Profile updated."))
    return redirect("/employee/employee-profile")


@login_required
@permission_required("delete_group")
@require_http_methods(["POST"])
def employee_user_group_assign_delete(_, obj_id):
    """
    This method is used to delete user group assign
    """
    user = User.objects.get(id=obj_id)
    user.groups.clear()
    return redirect("/employee/employee-user-group-assign-view")


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate query set
    """
    paginator = HorillaPaginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@enter_if_accessible(
    feature="employee_view",
    perm="employee.view_employee",
    method=_check_reporting_manager,
)
def employee_view(request):
    """
    This method is used to render template for view all employee
    """
    view_type = request.GET.get("view")
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    error_message = request.session.pop("error_message", None)

    queryset = Employee.objects.filter()
    filter_obj = EmployeeFilter(request.GET, queryset=queryset).qs
    if request.GET.get("is_active") != "False":
        filter_obj = filter_obj.filter(is_active=True)

    update_fields = BulkUpdateFieldForm()
    data_dict = parse_qs(previous_data)
    get_key_instances(Employee, data_dict)
    emp = Employee.objects.filter()

    # Store the employees in the session
    request.session["filtered_employees"] = [employee.id for employee in queryset]

    return render(
        request,
        "employee_personal_info/employee_view.html",
        {
            "data": paginator_qry(filter_obj, page_number),
            "pd": previous_data,
            "f": EmployeeFilter(),
            "update_fields_form": update_fields,
            "view_type": view_type,
            "filter_dict": data_dict,
            "emp": emp,
            "gp_fields": EmployeeReGroup.fields,
            "error_message": error_message,
        },
    )


@login_required
@permission_required("employee.change_employee")
def view_employee_bulk_update(request):
    if request.method == "POST":
        update_fields = request.POST.getlist("update_fields")
        bulk_employee_ids = request.POST.get("bulk_employee_ids")
        bulk_employee_ids_str = (
            json.dumps(bulk_employee_ids) if bulk_employee_ids else ""
        )
        if bulk_employee_ids_str:

            class EmployeeBulkUpdateForm(ModelForm):
                class Meta:
                    model = Employee
                    fields = []
                    widgets = {}
                    labels = {}
                    for field in update_fields:
                        try:
                            field_obj = Employee._meta.get_field(field)
                            if field_obj.name in ("country", "state"):
                                if not "country" in update_fields:
                                    fields.append("country")
                                    widgets["country"] = Select(
                                        attrs={"required": True}
                                    )
                                fields.append(field)
                                widgets[field] = Select(attrs={"required": True})
                            else:
                                fields.append(field)

                            if isinstance(field_obj, models.DateField):
                                widgets[field] = DateInput(
                                    attrs={
                                        "type": "date",
                                        "required": True,
                                        "data-pp": False,
                                    }
                                )
                        except:
                            continue

                def __init__(self, *args, **kwargs):
                    super(EmployeeBulkUpdateForm, self).__init__(*args, **kwargs)
                    for field_name, field in self.fields.items():
                        field.required = True

            class WorkInfoBulkUpdateForm(ModelForm):
                class Meta:
                    model = EmployeeWorkInformation
                    fields = []
                    widgets = {}
                    labels = {}
                    for field in update_fields:
                        try:
                            parts = str(field).split("__")
                            if parts[-1]:
                                if parts[0] == "employee_work_info":
                                    field_obj = EmployeeWorkInformation._meta.get_field(
                                        parts[-1]
                                    )

                                    if (
                                        parts[1] == "department_id"
                                        or parts[1] == "job_position_id"
                                        or parts[1] == "job_role_id"
                                    ):
                                        if (
                                            not "employee_work_info__department_id"
                                            in update_fields
                                        ):
                                            fields.append("department_id")
                                            widgets["department_id"] = Select(
                                                attrs={"required": True}
                                            )
                                        if (
                                            not "employee_work_info__job_position_id"
                                            in update_fields
                                        ):
                                            fields.append("job_position_id")
                                            widgets["job_position_id"] = Select(
                                                attrs={"required": True}
                                            )
                                        if (
                                            not "employee_work_info__job_role_id"
                                            in update_fields
                                        ):
                                            fields.append("job_role_id")
                                            widgets["job_role_id"] = Select(
                                                attrs={"required": True}
                                            )
                                        fields.append(parts[1])
                                        widgets[field] = Select(
                                            attrs={"required": True}
                                        )

                                    fields.append(parts[-1])

                                    # Remove inner lists
                                    fields = [
                                        item
                                        for item in fields
                                        if not isinstance(item, list)
                                    ]

                                    if isinstance(field_obj, models.DateField):
                                        widgets[parts[-1]] = DateInput(
                                            attrs={"type": "date"}
                                        )
                                    if parts[-1] in ("email", "mobile"):
                                        labels[parts[-1]] = (
                                            _("Work Email")
                                            if field_obj.name == "email"
                                            else _("Work Phone")
                                        )
                        except:
                            continue

                def __init__(self, *args, **kwargs):
                    super(WorkInfoBulkUpdateForm, self).__init__(*args, **kwargs)
                    if "department_id" in self.fields:
                        self.fields["department_id"].widget.attrs.update(
                            {
                                "onchange": "depChange($(this))",
                            }
                        )
                    if "job_position_id" in self.fields:
                        self.fields["job_position_id"].widget.attrs.update(
                            {
                                "onchange": "jobChange($(this))",
                            }
                        )
                    for field_name, field in self.fields.items():
                        field.required = True

            class BankInfoBulkUpdateForm(ModelForm):
                class Meta:
                    model = EmployeeBankDetails
                    fields = []
                    widgets = {}
                    labels = {}
                    for field in update_fields:
                        try:
                            parts = str(field).split("__")
                            if parts[-1]:
                                if parts[0] == "employee_bank_details":
                                    field_obj = EmployeeBankDetails._meta.get_field(
                                        parts[-1]
                                    )
                                    fields.append(parts[-1])
                                    if isinstance(field_obj, models.DateField):
                                        widgets[parts[-1]] = DateInput(
                                            attrs={"type": "date"}
                                        )

                                    if field_obj.name in ("country", "state"):
                                        if not "country" in update_fields:
                                            fields.append("country")
                                            widgets["country"] = Select(
                                                attrs={"required": True}
                                            )
                                        fields.append(parts[-1])
                                        widgets[parts[-1]] = Select(
                                            attrs={"required": True}
                                        )
                                        labels[parts[-1]] = (
                                            _("Bank Country")
                                            if field_obj.name == "country"
                                            else _("Bank State")
                                        )

                        except:
                            continue

                def __init__(self, *args, **kwargs):
                    super(BankInfoBulkUpdateForm, self).__init__(*args, **kwargs)
                    for field_name, field in self.fields.items():
                        field.required = True

            form = EmployeeBulkUpdateForm()
            form1 = WorkInfoBulkUpdateForm()
            form2 = BankInfoBulkUpdateForm()

            keys = form1.fields.keys()
            # Convert dict_keys object to a list
            keys_list = list(keys)

            fields_list = []
            for i in keys_list:
                i = "employee_work_info__" + i
                fields_list.append(i)

            for i in fields_list:
                if i not in update_fields:
                    update_fields.append(i)

            update_fields_str = json.dumps(update_fields)

            context = {
                "form": form,
                "form1": form1,
                "form2": form2,
                "update_fields": update_fields_str,
                "bulk_employee_ids": bulk_employee_ids_str,
            }
            return render(
                request,
                "employee_personal_info/bulk_update.html",
                context=context,
            )
        else:
            messages.warning(
                request, _("There are no employees selected for bulk update.")
            )
            return redirect(employee_view)


@login_required
@permission_required("employee.change_employee")
def save_employee_bulk_update(request):
    if request.method == "POST":
        update_fields_str = request.POST.get("update_fields", "")
        update_fields = json.loads(update_fields_str) if update_fields_str else []
        dict_value = request.__dict__["_post"]
        bulk_employee_ids_str = request.POST.get("bulk_employee_ids", "")
        bulk_employee_ids = (
            json.loads(bulk_employee_ids_str) if bulk_employee_ids_str else []
        )
        employee_list = ast.literal_eval(bulk_employee_ids)
        for id in employee_list:
            try:
                employee_instance = Employee.objects.get(id=int(id))
                employee_work_info, created = (
                    EmployeeWorkInformation.objects.get_or_create(
                        employee_id=employee_instance
                    )
                )
                employee_bank, created = EmployeeBankDetails.objects.get_or_create(
                    employee_id=employee_instance
                )
            except (ValueError, OverflowError):
                employee_list.remove(id)

        for field in update_fields:
            parts = str(field).split("__")
            if parts[-1]:
                if parts[0] == "employee_work_info":
                    employee_queryset = EmployeeWorkInformation.objects.filter(
                        employee_id__in=employee_list
                    )
                    value = dict_value.get(parts[-1])
                    employee_queryset.update(**{parts[-1]: value})
                elif parts[0] == "employee_bank_details":
                    for id in employee_list:

                        employee_queryset = EmployeeBankDetails.objects.filter(
                            employee_id__in=employee_list
                        )
                        value = dict_value.get(parts[-1])
                        employee_queryset.update(**{parts[-1]: value})
                else:
                    employee_queryset = Employee.objects.filter(id__in=employee_list)
                    value = dict_value.get(field)
                    employee_queryset.update(**{field: value})
        if len(employee_list) > 0:
            messages.success(
                request,
                _(
                    "{} employees information updated successfully".format(
                        len(employee_list)
                    )
                ),
            )
    return redirect("/employee/employee-view/?view=list")


@login_required
@permission_required("employee.change_employee")
def employee_account_block_unblock(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    if not employee:
        messages.info(request, _("Employee not found"))
        return redirect(employee_view)
    user = get_object_or_404(User, id=employee.employee_user_id.id)
    if not user:
        messages.info(request, _("Employee not found"))
        return redirect(employee_view)
    if not user.is_superuser:
        user.is_active = not user.is_active
        action_message = _("blocked") if not user.is_active else _("unblocked")
        user.save()
        messages.success(
            request,
            _("{employee}'s account {action_message} successfully!").format(
                employee=employee, action_message=action_message
            ),
        )
    else:
        messages.info(
            request,
            _("{employee} is a superuser and cannot be blocked.").format(
                employee=employee
            ),
        )
    return redirect(employee_view_individual, obj_id=emp_id)


@login_required
@permission_required("employee.add_employee")
def employee_view_new(request):
    """
    This method is used to render form to create a new employee.
    """
    form = EmployeeForm()
    work_form = EmployeeWorkInformationForm()
    bank_form = EmployeeBankDetailsForm()
    filter_obj = EmployeeFilter(queryset=Employee.objects.all())
    return render(
        request,
        "employee/create_form/form_view.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form, "f": filter_obj},
    )


@login_required
@manager_can_enter("employee.change_employee")
def employee_view_update(request, obj_id, **kwargs):
    """
    This method is used to render update form for employee.
    """
    selected_company_id = request.session["selected_company"]
    user = Employee.objects.filter(employee_user_id=request.user).first()
    work_info_history = HistoryTrackingFields.objects.filter(
        work_info_track=True
    ).exists()

    employee = Employee.objects.filter(id=obj_id).first()
    emp = Employee.objects.entire().filter(id=obj_id).first()
    if not employee and emp and hasattr(emp, "employee_work_info"):
        if (
            emp.employee_work_info
            and emp.employee_work_info.company_id
            and emp.employee_work_info.company_id_id != selected_company_id
        ):

            messages.error(
                request, _("Employee is not working in the selected company.")
            )
            return redirect(employee_view)

    if employee is None:
        employee = emp
        cmpny = Company.objects.get(id=selected_company_id)

        work = (
            EmployeeWorkInformation.objects.entire()
            .filter(employee_id=employee)
            .first()
        )

        if work and selected_company_id != "all":
            work.company_id = cmpny
            work.save()

        employee.save()

    if (
        user
        and user.reporting_manager.filter(employee_id=employee).exists()
        or request.user.has_perm("employee.change_employee")
    ):
        form = EmployeeForm(instance=employee)
        work_form = EmployeeWorkInformationForm(
            instance=EmployeeWorkInformation.objects.filter(
                employee_id=employee
            ).first()
        )
        bank_form = EmployeeBankDetailsForm(
            instance=EmployeeBankDetails.objects.filter(employee_id=employee).first()
        )
        if request.POST:
            if request.POST.get("form") == "personal":
                form = EmployeeForm(request.POST, instance=employee)
                if form.is_valid():
                    form.save()
                    messages.success(
                        request, _("Employee personal information updated.")
                    )
            elif request.POST.get("form") == "work":
                instance = EmployeeWorkInformation.objects.filter(
                    employee_id=employee
                ).first()
                work_form = EmployeeWorkInformationUpdateForm(
                    request.POST, instance=instance
                )
                if work_form.is_valid():
                    instance = work_form.save(commit=False)
                    instance.employee_id = employee
                    instance.save()
                    instance.tags.set(request.POST.getlist("tags"))
                    notify.send(
                        request.user.employee_get,
                        recipient=instance.employee_id.employee_user_id,
                        verb="Your work details has been updated.",
                        verb_ar="تم تحديث تفاصيل عملك.",
                        verb_de="Ihre Arbeitsdetails wurden aktualisiert.",
                        verb_es="Se han actualizado los detalles de su trabajo.",
                        verb_fr="Vos informations professionnelles ont été mises à jour.",
                        redirect=reverse("employee-profile"),
                        icon="briefcase",
                    )
                    messages.success(request, _("Employee work information updated."))
                work_form = EmployeeWorkInformationForm(
                    instance=EmployeeWorkInformation.objects.filter(
                        employee_id=employee
                    ).first()
                )
            elif request.POST.get("form") == "bank":
                instance = EmployeeBankDetails.objects.filter(
                    employee_id=employee
                ).first()
                bank_form = EmployeeBankDetailsUpdateForm(
                    request.POST, instance=instance
                )
                if bank_form.is_valid():
                    instance = bank_form.save(commit=False)
                    instance.employee_id = employee
                    instance.save()
                    messages.success(request, _("Employee bank details updated."))
        return render(
            request,
            "employee/update_form/form_view.html",
            {
                "obj_id": obj_id,
                "form": form,
                "work_form": work_form,
                "bank_form": bank_form,
                "work_info_history": work_info_history,
            },
        )
    return HttpResponseRedirect(
        request.META.get("HTTP_REFERER", "/employee/employee-view")
    )


@login_required
@require_http_methods(["POST"])
@permission_required("employee.change_employee")
def update_profile_image(request, obj_id):
    """
    This method is used to upload a profile image
    """
    try:
        employee = Employee.objects.get(id=obj_id)
        img = request.FILES["employee_profile"]
        employee.employee_profile = img
        employee.save()
        messages.success(request, _("Profile image updated."))
    except Exception:
        messages.error(request, _("No image chosen."))
    response = render(
        request,
        "employee/profile/profile_modal.html",
    )
    return HttpResponse(
        response.content.decode("utf-8") + "<script>location.reload();</script>"
    )


@login_required
@require_http_methods(["POST"])
def update_own_profile_image(request):
    """
    This method is used to update own profile image from profile view form
    """
    employee = request.user.employee_get
    img = request.FILES.get("employee_profile")
    employee.employee_profile = img
    employee.save()
    messages.success(request, _("Profile image updated."))
    response = render(
        request,
        "employee/profile/profile_modal.html",
    )
    return HttpResponse(
        response.content.decode("utf-8") + "<script>location.reload();</script>"
    )


@login_required
@require_http_methods(["DELETE"])
@permission_required("employee.change_employee")
def remove_profile_image(request, obj_id):
    """
    This method is used to remove uploaded image
    Args: obj_id : Employee model instance id
    """
    employee = Employee.objects.get(id=obj_id)
    if employee.employee_profile.name == "":
        messages.info(request, _("No profile image to remove."))
        response = render(
            request,
            "employee/profile/profile_modal.html",
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location.reload();</script>"
        )
    file_path = employee.employee_profile.path
    absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)
    os.remove(absolute_path)
    employee.employee_profile = None
    employee.save()
    messages.success(request, _("Profile image removed."))
    response = render(
        request,
        "employee/profile/profile_modal.html",
    )
    return HttpResponse(
        response.content.decode("utf-8") + "<script>location.reload();</script>"
    )


@login_required
@require_http_methods(["DELETE"])
def remove_own_profile_image(request):
    """
    This method is used to remove own profile image
    """
    employee = request.user.employee_get
    if employee.employee_profile.name == "":
        messages.info(request, _("No profile image to remove."))
        response = render(
            request,
            "employee/profile/profile_modal.html",
        )
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location.reload();</script>"
        )
    file_path = employee.employee_profile.path
    absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)
    os.remove(absolute_path)
    employee.employee_profile = None
    employee.save()

    messages.success(request, _("Profile image removed."))
    response = render(
        request,
        "employee/profile/profile_modal.html",
    )
    return HttpResponse(
        response.content.decode("utf-8") + "<script>location.reload();</script>"
    )


@login_required
@manager_can_enter("employee.change_employee")
@require_http_methods(["POST"])
def employee_create_update_personal_info(request, obj_id=None):
    """
    This method is used to update employee's personal info.
    """
    employee = Employee.objects.filter(id=obj_id).first()
    form = EmployeeForm(request.POST, instance=employee)
    if form.is_valid():
        form.save()
        if obj_id is None:
            messages.success(request, _("New Employee Added."))
            form = EmployeeForm(request.POST, instance=form.instance)
            work_form = EmployeeWorkInformationForm(
                instance=EmployeeWorkInformation.objects.filter(
                    employee_id=employee
                ).first()
            )
            bank_form = EmployeeBankDetailsForm(
                instance=EmployeeBankDetails.objects.filter(
                    employee_id=employee
                ).first()
            )
            return redirect(
                f"employee-view-update/{form.instance.id}/",
                data={"form": form, "work_form": work_form, "bank_form": bank_form},
            )
        return HttpResponse(
            """
                <div class="oh-alert-container">
                    <div class="oh-alert oh-alert--animated oh-alert--success">
                        Personal Info updated
                    </div>
                </div>

        """
        )
    if obj_id is None:
        return render(
            request,
            "employee/create_form/form_view.html",
            {
                "form": form,
            },
        )
    errors = "\n".join(
        [
            f"<li>{form.fields.get(field, field).label}: {', '.join(errors)}</li>"
            for field, errors in form.errors.items()
        ]
    )
    return HttpResponse(f'<ul class="alert alert-danger">{errors}</ul>')


@login_required
@manager_can_enter("employee.change_employeeworkinformation")
@require_http_methods(["POST"])
def employee_update_work_info(request, obj_id=None):
    """
    This method is used to update employee work info
    """
    employee = Employee.objects.filter(id=obj_id).first()
    form = EmployeeWorkInformationForm(
        request.POST,
        instance=EmployeeWorkInformation.objects.filter(employee_id=employee).first(),
    )
    form.fields["employee_id"].required = False
    form.employee_id = employee
    if form.is_valid() and employee is not None:
        work_info = form.save(commit=False)
        work_info.employee_id = employee
        work_info.save()
        return HttpResponse(
            """

                <div class="oh-alert-container">
                    <div class="oh-alert oh-alert--animated oh-alert--success">
                        Personal Info updated
                    </div>
                </div>

        """
        )
    errors = "\n".join(
        [
            f"<li>{form.fields.get(field, field).label}: {', '.join(errors)}</li>"
            for field, errors in form.errors.items()
        ]
    )
    return HttpResponse(f'<ul class="alert alert-danger">{errors}</ul>')


@login_required
@manager_can_enter("employee.change_employeebankdetails")
@require_http_methods(["POST"])
def employee_update_bank_details(request, obj_id=None):
    """
    This method is used to render form to create employee's bank information.
    """
    employee = Employee.objects.filter(id=obj_id).first()
    form = EmployeeBankDetailsForm(
        request.POST,
        instance=EmployeeBankDetails.objects.filter(employee_id=employee).first(),
    )
    if form.is_valid() and employee is not None:
        bank_info = form.save(commit=False)
        bank_info.employee_id = employee
        bank_info.save()
        return HttpResponse(
            """
            <div class="oh-alert-container">
                <div class="oh-alert oh-alert--animated oh-alert--success">
                    Bank details updated
                </div>
            </div>
        """
        )
    errors = "\n".join(
        [
            f"<li>{form.fields.get(field, field).label}: {', '.join(errors)}</li>"
            for field, errors in form.errors.items()
        ]
    )
    return HttpResponse(f'<ul class="alert alert-danger">{errors}</ul>')


@login_required
@hx_request_required
@enter_if_accessible(
    feature="employee_view",
    perm="employee.view_employee",
    method=_check_reporting_manager,
)
def employee_filter_view(request):
    """
    This method is used to filter employee.
    """
    previous_data = request.GET.urlencode()
    field = request.GET.get("field")
    queryset = Employee.objects.filter()
    selected_company = request.session.get("selected_company")
    employees = EmployeeFilter(request.GET, queryset=queryset).qs
    if request.GET.get("is_active") != "False":
        employees = employees.filter(is_active=True)
    if (
        request.GET.get("employee_work_info__company_id") == None
        and selected_company != "all"
    ):
        employees = employees.filter(employee_work_info__company_id=selected_company)
    page_number = request.GET.get("page")
    view = request.GET.get("view")
    data_dict = parse_qs(previous_data)
    get_key_instances(Employee, data_dict)
    template = "employee_personal_info/employee_card.html"
    if view == "list":
        template = "employee_personal_info/employee_list.html"
    if field != "" and field is not None:
        employees = group_by_queryset(employees, field, page_number, "page")
        template = "employee_personal_info/group_by.html"
    else:
        employees = sortby(request, employees, "orderby")
        employees = paginator_qry(employees, page_number)

        # Store the employees in the session
        request.session["filtered_employees"] = [employee.id for employee in employees]

    return render(
        request,
        template,
        {
            "data": employees,
            "f": EmployeeFilter(request.GET),
            "pd": previous_data,
            "field": field,
            "filter_dict": data_dict,
        },
    )


@login_required
@manager_can_enter("employee.view_employee")
@hx_request_required
def employee_card(request):
    """
    This method renders card template to view all employees.
    """
    previous_data = request.GET.urlencode()
    search = request.GET.get("search")
    if isinstance(search, type(None)):
        search = ""
    employees = filtersubordinatesemployeemodel(
        request, Employee.objects.all(), "employee.view_employee"
    )
    if request.GET.get("is_active") is None:
        filter_obj = EmployeeFilter(
            request.GET,
            queryset=employees.filter(
                employee_first_name__icontains=search, is_active=True
            ),
        )
    else:
        filter_obj = EmployeeFilter(
            request.GET,
            queryset=employees.filter(employee_first_name__icontains=search),
        )
    page_number = request.GET.get("page")
    employees = sortby(request, filter_obj.qs, "orderby")
    return render(
        request,
        "employee_personal_info/employee_card.html",
        {
            "data": paginator_qry(employees, page_number),
            "f": filter_obj,
            "pd": previous_data,
        },
    )


@login_required
@manager_can_enter("employee.view_employee")
@hx_request_required
def employee_list(request):
    """
    This method renders template to view all employees
    """
    previous_data = request.GET.urlencode()
    search = request.GET.get("search")
    if isinstance(search, type(None)):
        search = ""
    if request.GET.get("is_active") is None:
        filter_obj = EmployeeFilter(
            request.GET,
            queryset=Employee.objects.filter(
                employee_first_name__icontains=search, is_active=True
            ),
        )
    else:
        filter_obj = EmployeeFilter(
            request.GET,
            queryset=Employee.objects.filter(employee_first_name__icontains=search),
        )
    employees = filtersubordinatesemployeemodel(
        request, filter_obj.qs, "employee.view_employee"
    )
    employees = sortby(request, employees, "orderby")
    page_number = request.GET.get("page")
    return render(
        request,
        "employee_personal_info/employee_list.html",
        {
            "data": paginator_qry(employees, page_number),
            "f": filter_obj,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
@manager_can_enter("employee.view_employee")
def employee_update(request, obj_id):
    """
    This method is used to update employee if the form is valid
    args:
        obj_id : employee id
    """
    employee = Employee.objects.get(id=obj_id)
    form = EmployeeForm(instance=employee)
    work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
    bank_info = EmployeeBankDetails.objects.filter(employee_id=employee).first()
    work_form = EmployeeWorkInformationForm()
    bank_form = EmployeeBankDetailsUpdateForm()
    if work_info is not None:
        work_form = EmployeeWorkInformationForm(instance=work_info)
    if bank_info is not None:
        bank_form = EmployeeBankDetailsUpdateForm(instance=bank_info)
    if request.method == "POST":
        if request.user.has_perm("employee.change_employee"):
            form = EmployeeForm(request.POST, request.FILES, instance=employee)
            if form.is_valid():
                form.save()
                messages.success(request, _("Employee updated."))
    return render(
        request,
        "employee_personal_info/employee_update_form.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form},
    )


@login_required
@permission_required("employee.delete_employee")
@require_http_methods(["POST"])
def employee_delete(request, obj_id):
    """
    This method is used to delete employee
    args:
        id  : employee id
    """

    try:
        view = request.POST.get("view")
        employee = Employee.objects.get(id=obj_id)
        if apps.is_installed("payroll"):
            if employee.contract_set.all().exists():
                contracts = employee.contract_set.all()
                for contract in contracts:
                    if contract.contract_status != "active":
                        contract.delete()
        user = employee.employee_user_id
        try:
            user.delete()
        except AttributeError:
            employee.delete()
        messages.success(request, _("Employee deleted"))

    except Employee.DoesNotExist:
        messages.error(request, _("Employee not found."))
    except ProtectedError as e:
        model_verbose_names_set = set()
        for obj in e.protected_objects:
            model_verbose_names_set.add(__(obj._meta.verbose_name.capitalize()))
        model_names_str = ", - ".join(model_verbose_names_set)
        error_message = _("- {}.".format(model_names_str))
        error_message = str(error_message)
        request.session["error_message"] = error_message
        return redirect(employee_view)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", f"/view={view}"))


@login_required
@permission_required("employee.delete_employee")
def employee_bulk_delete(request):
    """
    This method is used to delete set of Employee instances
    """
    ids = json.loads(request.POST.get("ids", "[]"))
    if not ids:
        messages.error(request, _("No IDs provided."))
    deleted_count = 0
    employees = Employee.objects.filter(id__in=ids).select_related("employee_user_id")
    for employee in employees:
        try:
            if apps.is_installed("payroll"):
                if employee.contract_set.all().exists():
                    contracts = employee.contract_set.all()
                    for contract in contracts:
                        if contract.contract_status != "active":
                            contract.delete()
            user = employee.employee_user_id
            user.delete()
            deleted_count += 1
        except Employee.DoesNotExist:
            messages.error(request, _("Employee not found."))
        except ProtectedError:
            messages.error(
                request, _("You cannot delete %(employee)s.") % {"employee": employee}
            )
    if deleted_count > 0:
        messages.success(
            request,
            _("%(deleted_count)s employees deleted.")
            % {"deleted_count": deleted_count},
        )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required("employee.delete_employee")
@require_http_methods(["POST"])
def employee_bulk_archive(request):
    """
    This method is used to archive bulk of Employee instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = False
    if request.GET.get("is_active") == "True":
        is_active = True
    for employee_id in ids:
        employee = Employee.objects.get(id=employee_id)

        emp = Employee.objects.get(id=employee_id)
        if emp.employee_user_id.is_superuser and emp.is_active:
            count = 0
            employees = Employee.objects.filter(is_active=True)
            for super_emp in employees:
                if super_emp.employee_user_id.is_superuser:
                    count = count + 1
            if count == 1:
                messages.error(request, _("You can't archive the last superuser."))
                return HttpResponse("<script>$('#filterEmployee').click();</script>")

        employee.is_active = is_active
        employee.employee_user_id.is_active = is_active
        if employee.get_archive_condition() is False:
            employee.save()
            message = _("archived")
            if is_active:
                message = _("un-archived")
            messages.success(request, f"{employee} is {message}")
        else:
            messages.warning(request, _("Related data found for {}.").format(employee))
    return JsonResponse({"message": "Success"})


@login_required
@hx_request_required
@permission_required("employee.delete_employee")
def employee_archive(request, obj_id):
    """
    This method is used to archive employee instance
    Args:
            obj_id : Employee instance id
    """
    employee = Employee.objects.get(id=obj_id)
    employee.is_active = not employee.is_active
    employee.employee_user_id.is_active = not employee.is_active
    save = True
    message = "Employee un-archived"
    if not employee.is_active:

        emp = Employee.objects.get(id=obj_id)
        if emp.employee_user_id.is_superuser:
            count = 0
            employees = Employee.objects.filter(is_active=True)
            for super_emp in employees:
                if super_emp.employee_user_id.is_superuser:
                    count = count + 1
            if count == 1:
                messages.error(request, _("You can't archive the last superuser."))
                return HttpResponse("<script>$('#filterEmployee').click();</script>")

        result = employee.get_archive_condition()
        if result:
            save = False
        else:
            message = _("Employee archived")
    if save:
        employee.save()
        messages.success(request, message)
        key = "HTTP_HX_REQUEST"
        if key not in request.META.keys():
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        else:
            return HttpResponse("<script>$('#filterEmployee').click();</script>")
    else:
        return render(
            request,
            "related_models.html",
            {
                "employee": employee,
                "related_models": result.get("related_models"),
                "related_model_fields": result.get("related_model_fields"),
                "employee_choices": result.get("employee_choices"),
                "title": _("Can't Archive"),
            },
        )


@login_required
@permission_required("employee.change_employee")
def replace_employee(request, emp_id):
    title = request.GET.get("title")
    employee = Employee.objects.filter(id=emp_id).first()
    related_models = (
        employee.get_archive_condition().get("related_models", "") if employee else None
    )
    if related_models and employee:
        for models in related_models:
            field_name = models.get("field_name", "")
            if field_name:
                replace_emp_id = request.POST.get(field_name)
                replace_emp = Employee.objects.filter(id=replace_emp_id).first()
                if (
                    field_name == "reporting_manager_id"
                    and str(emp_id) != replace_emp_id
                ):
                    reporting_manager = EmployeeWorkInformation.objects.filter(
                        reporting_manager_id=emp_id
                    ).update(reporting_manager_id=replace_emp)
                elif (
                    apps.is_installed("recruitment")
                    and field_name == "recruitment_managers"
                    and str(emp_id) != replace_emp_id
                ):
                    Recruitment = get_horilla_model_class(
                        app_label="recruitment", model="recruitment"
                    )
                    recruitment_query = Recruitment.objects.filter(
                        recruitment_managers=emp_id
                    )
                    if recruitment_query:
                        for recruitment in recruitment_query:
                            recruitment.recruitment_managers.remove(emp_id)
                            recruitment.recruitment_managers.add(replace_emp)
                elif (
                    apps.is_installed("recruitment")
                    and field_name == "recruitment_stage_managers"
                    and str(emp_id) != replace_emp_id
                ):
                    Stage = get_horilla_model_class(
                        app_label="recruitment", model="stage"
                    )
                    recruitment_stage_query = Stage.objects.filter(
                        stage_managers=emp_id
                    )
                    if recruitment_stage_query:
                        for stage in recruitment_stage_query:
                            stage.stage_managers.remove(emp_id)
                            stage.stage_managers.add(replace_emp)
                elif (
                    apps.is_installed("onboarding")
                    and field_name == "onboarding_stage_manager"
                    and str(emp_id) != replace_emp_id
                ):
                    OnboardingStage = get_horilla_model_class(
                        app_label="onboarding", model="onboardingstage"
                    )
                    onboarding_stage_query = OnboardingStage.objects.filter(
                        employee_id=emp_id
                    )
                    if onboarding_stage_query:
                        for stage in onboarding_stage_query:
                            stage.employee_id.remove(emp_id)
                            stage.employee_id.add(replace_emp)
                elif (
                    apps.is_installed("onboarding")
                    and field_name == "onboarding_task_manager"
                    and str(emp_id) != replace_emp_id
                ):
                    OnboardingTask = get_horilla_model_class(
                        app_label="onboarding", model="onboardingtask"
                    )
                    onboarding_task_query = OnboardingTask.objects.filter(
                        employee_id=emp_id
                    )
                    if onboarding_task_query:
                        for task in onboarding_task_query:
                            task.employee_id.remove(emp_id)
                            task.employee_id.add(replace_emp)
                else:
                    pass
    related_models = employee.get_archive_condition()
    if title == "Change the Designations":
        messages.success(request, _("Designation changed."))
        return redirect("/offboarding/offboarding-pipeline")
    if related_models is False and title != "Change the Designations":
        employee.is_active = False
        employee.save()
        messages.success(request, _("{} archived successfully").format(employee))
    return redirect(employee_view)


@login_required
@permission_required("employee.view_employee")
def get_manager_in(request):
    """
    This method is used to get the manager in records model
    """
    employee_id = request.GET.get("employee_id")
    employee = Employee.objects.filter(id=employee_id).first()
    offboarding = request.GET.get("offboarding")
    if offboarding:
        title = _("Change the Designations")
    else:
        title = _("Can't Archive")
    employee.is_active = not employee.is_active
    employee.employee_user_id.is_active = not employee.is_active
    save = True
    message = "Employee un-archived"
    if not employee.is_active:
        result = employee.get_archive_condition()
        if result:
            save = False
        else:
            message = _("Employee archived")
    if save:
        employee.save()
        messages.success(request, message)
        key = "HTTP_HX_REQUEST"
        if key not in request.META.keys():
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        else:
            return HttpResponse("<script>window.location.reload()</script>")
    else:
        return render(
            request,
            "related_models.html",
            {
                "employee": employee,
                "related_models": result.get("related_models"),
                "related_model_fields": result.get("related_model_fields"),
                "employee_choices": result.get("employee_choices"),
                "title": title,
            },
        )


@login_required
@enter_if_accessible(
    feature="employee_view",
    perm="employee.view_employee",
    method=_check_reporting_manager,
)
def employee_search(request):
    """
    This method is used to search employee
    """
    search = request.GET["search"]
    view = request.GET["view"]
    previous_data = request.GET.urlencode()
    employees = EmployeeFilter(request.GET).qs
    if search == "":
        employees = employees.filter(is_active=True)
    page_number = request.GET.get("page")
    template = "employee_personal_info/employee_card.html"
    if view == "list":
        template = "employee_personal_info/employee_list.html"
    employees = filtersubordinatesemployeemodel(
        request, employees, "employee.view_employee"
    )
    employees = sortby(request, employees, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(Employee, data_dict)
    return render(
        request,
        template,
        {
            "data": paginator_qry(employees, page_number),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@manager_can_enter("employee.add_employeeworkinformation")
@require_http_methods(["POST"])
def employee_work_info_view_create(request, obj_id):
    """
    This method is used to create employee work information from employee single view template
    args:
        obj_id : employee instance id
    """

    employee = Employee.objects.get(id=obj_id)
    form = EmployeeForm(instance=employee)

    work_form = EmployeeWorkInformationUpdateForm(request.POST)

    bank_form = EmployeeBankDetailsUpdateForm()
    bank_form_instance = EmployeeBankDetails.objects.filter(
        employee_id=employee
    ).first()
    if bank_form_instance is not None:
        bank_form = EmployeeBankDetailsUpdateForm(
            instance=employee.employee_bank_details
        )

    if work_form.is_valid():
        work_info = work_form.save(commit=False)
        work_info.employee_id = employee
        work_info.save()
        messages.success(request, _("Created work information"))
    return render(
        request,
        "employee_personal_info/employee_update_form.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form},
    )


@login_required
@manager_can_enter("employee.change_employeeworkinformation")
@require_http_methods(["POST"])
def employee_work_info_view_update(request, obj_id):
    """
    This method is used to update employee work information from single view template
    args:
        obj_id  : employee work information id
    """

    work_information = EmployeeWorkInformation.objects.get(id=obj_id)
    form = EmployeeForm(instance=work_information.employee_id)
    bank_form = EmployeeBankDetailsUpdateForm(
        instance=work_information.employee_id.employee_bank_details
    )
    work_form = EmployeeWorkInformationUpdateForm(
        request.POST,
        instance=work_information,
    )
    if work_form.is_valid():
        work_form.save()
        messages.success(request, _("Work Information Updated Successfully"))
    return render(
        request,
        "employee_personal_info/employee_update_form.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form},
    )


@login_required
@manager_can_enter("employee.add_employeebankdetails")
@require_http_methods(["POST"])
def employee_bank_details_view_create(request, obj_id):
    """
    This method used to create bank details object from the view template
    args:
        obj_id : employee instance id
    """
    employee = Employee.objects.get(id=obj_id)
    form = EmployeeForm(instance=employee)
    bank_form = EmployeeBankDetailsUpdateForm(request.POST)
    work_form_instance = EmployeeWorkInformation.objects.filter(
        employee_id=employee
    ).first()
    work_form = EmployeeWorkInformationUpdateForm()
    if work_form_instance is not None:
        work_form = EmployeeWorkInformationUpdateForm(instance=work_form_instance)
    if bank_form.is_valid():
        bank_instance = bank_form.save(commit=False)
        bank_instance.employee_id = employee
        bank_instance.save()
        messages.success(request, _("Bank Details Created Successfully"))
    return render(
        request,
        "employee_personal_info/employee_update_form.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form},
    )


@login_required
@manager_can_enter("employee.change_employeebankdetails")
@require_http_methods(["POST"])
def employee_bank_details_view_update(request, obj_id):
    """
    This method is used to update employee bank details.
    """
    employee_bank_instance = EmployeeBankDetails.objects.get(id=obj_id)
    form = EmployeeForm(instance=employee_bank_instance.employee_id)
    work_form = EmployeeWorkInformationUpdateForm(
        instance=employee_bank_instance.employee_id.employee_work_info
    )
    bank_form = EmployeeBankDetailsUpdateForm(
        request.POST, instance=employee_bank_instance
    )
    if bank_form.is_valid():
        bank_instance = bank_form.save(commit=False)
        bank_instance.employee_id = employee_bank_instance.employee_id
        bank_instance.save()
        messages.success(request, _("Bank Details Updated Successfully"))
    return render(
        request,
        "employee_personal_info/employee_update_form.html",
        {"form": form, "work_form": work_form, "bank_form": bank_form},
    )


@login_required
@permission_required("employee.delete_employeeworkinformation")
@require_http_methods(["POST", "DELETE"])
def employee_work_information_delete(request, obj_id):
    """
    This method is used to delete employee work information
    args:
        obj_id : employee work information id
    """
    try:
        employee_work = EmployeeWorkInformation.objects.get(id=obj_id)
        employee_work.delete()
        messages.success(request, _("Employee work information deleted"))
    except EmployeeWorkInformation.DoesNotExist:
        messages.error(request, _("Employee work information not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this Employee work information"))

    return redirect("/employee/employee-work-information-view")


@login_required
@permission_required("employee.add_employee")
def employee_import(request):
    """
    This method is used to create employee and corresponding user.
    """
    if request.method == "POST":
        file = request.FILES["file"]
        # Read the Excel file into a Pandas DataFrame
        data_frame = pd.read_excel(file)
        # Convert the DataFrame to a list of dictionaries
        employee_dicts = data_frame.to_dict("records")
        # Create or update Employee objects from the list of dictionaries
        error_list = []
        for employee_dict in employee_dicts:
            try:
                phone = employee_dict["phone"]
                email = employee_dict["email"]
                employee_full_name = employee_dict["employee_full_name"]
                existing_user = User.objects.filter(username=email).first()
                if existing_user is None:
                    employee_first_name = employee_full_name
                    employee_last_name = ""
                    if " " in employee_full_name:
                        (
                            employee_first_name,
                            employee_last_name,
                        ) = employee_full_name.split(" ", 1)

                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=str(phone).strip(),
                        is_superuser=False,
                    )
                    employee = Employee()
                    employee.employee_user_id = user
                    employee.employee_first_name = employee_first_name
                    employee.employee_last_name = employee_last_name
                    employee.email = email
                    employee.phone = phone
                    employee.save()
            except Exception:
                error_list.append(employee_dict)
        return HttpResponse(
            """
    <div class='alert-success p-3 border-rounded'>
        Employee data has been imported successfully.
    </div>

    """
        )
    data_frame = pd.DataFrame(columns=["employee_full_name", "email", "phone"])
    # Export the DataFrame to an Excel file
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="employee_template.xlsx"'
    data_frame.to_excel(response, index=False)
    return response


@login_required
@permission_required("employee.add_employee")
def employee_export(_):
    """
    This method is used to export employee data to xlsx
    """
    # Get the list of field names for your model
    field_names = [f.name for f in Employee._meta.get_fields() if not f.auto_created]
    field_names.remove("employee_user_id")
    field_names.remove("employee_profile")
    field_names.remove("additional_info")
    field_names.remove("is_from_onboarding")
    field_names.remove("is_directly_converted")
    field_names.remove("is_active")

    # Get the existing employee data and convert it to a DataFrame
    employee_data = Employee.objects.values_list(*field_names)
    data_frame = pd.DataFrame(list(employee_data), columns=field_names)

    # Export the DataFrame to an Excel file

    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="employee_export.xlsx"'
    data_frame.to_excel(response, index=False)

    return response


def convert_nan(field, dicts):
    """
    This method is returns None or field value
    """
    field_value = dicts.get(field)
    try:
        float(field_value)
        return None
    except (ValueError, TypeError):
        return field_value


@login_required
@permission_required("employee.add_employee")
def work_info_import_file(request):
    """
    This method is used to return the excel file of import Employee instances
    """
    data_frame = pd.DataFrame(
        columns=[
            "Badge ID",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Gender",
            "Department",
            "Job Position",
            "Job Role",
            "Shift",
            "Work Type",
            "Reporting Manager",
            "Employee Type",
            "Location",
            "Date Joining",
            "Basic Salary",
            "Salary Hour",
            "Contract End Date",
            "Company",
        ]
    )

    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="work_info_template.xlsx"'
    data_frame.to_excel(response, index=False)
    return response


@login_required
@hx_request_required
@permission_required("employee.add_employee")
def work_info_import(request):
    if request.method == "GET":
        return render(request, "employee/employee_import.html")

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            error_message = _("No file uploaded.")
            return render(
                request,
                "employee/employee_import.html",
                {"error_message": error_message},
            )

        file_extension = file.name.split(".")[-1].lower()

        try:
            if file_extension == "csv":
                data_frame = pd.read_csv(file)
            elif file_extension in ["xls", "xlsx"]:
                data_frame = pd.read_excel(file)
            else:

                error_message = _(
                    "Unsupported file format. Please upload a CSV or Excel file."
                )
                return render(
                    request,
                    "employee/employee_import.html",
                    {"error_message": error_message},
                )

            valid, error_message = valid_import_file_headers(data_frame)
            if not valid:
                return render(
                    request,
                    "employee/employee_import.html",
                    {"error_message": error_message},
                )
            success_list, error_list, created_count = process_employee_records(
                data_frame
            )
            if success_list:
                try:
                    users = bulk_create_user_import(success_list)
                    employees = bulk_create_employee_import(success_list)
                    bulk_create_department_import(success_list)
                    bulk_create_job_position_import(success_list)
                    bulk_create_job_role_import(success_list)
                    bulk_create_work_types(success_list)
                    bulk_create_shifts(success_list)
                    bulk_create_employee_types(success_list)
                    bulk_create_work_info_import(success_list)
                    thread = threading.Thread(
                        target=set_initial_password, args=(employees,)
                    )
                    thread.start()

                except Exception as e:
                    messages.error(request, _("Error Occured {}").format(e))
                    logger.error(e)

            path_info = (
                generate_error_report(
                    error_list, error_data_template, "EmployeesImportError.xlsx"
                )
                if error_list
                else None
            )

            context = {
                "created_count": created_count,
                "total_count": created_count + len(error_list),
                "error_count": len(error_list),
                "model": _("Employees"),
                "path_info": path_info,
            }
            result = render_to_string("import_popup.html", context)
            result += """
                        <script>
                            $('#objectCreateModalTarget').css('max-width', '410px');
                        </script>
                    """
            return HttpResponse(result)
        except Exception as e:
            messages.error(
                request,
                _(
                    "Failed to read file. Please ensure it is a valid CSV or Excel file. : {}"
                ).format(e),
            )
            logger.error(f"File import error: {e}")
            error_message = f"File import error: {e}"
    return render(
        request, "employee/employee_import.html", {"error_message": error_message}
    )


@login_required
@manager_can_enter("employee.view_employee")
def work_info_export(request):
    """
    This method is used to export employee data to xlsx
    """
    if request.META.get("HTTP_HX_REQUEST"):
        context = {
            "export_filter": EmployeeFilter(),
            "export_form": EmployeeExportExcelForm(),
        }
        return render(request, "employee_export_filter.html", context)

    employees_data = {}
    selected_columns = []
    form = EmployeeExportExcelForm()
    field_overrides = {
        "employee_work_info__department_id": "employee_work_info__department_id__department",
        "employee_work_info__job_position_id": "employee_work_info__job_position_id__job_position",
        "employee_work_info__job_role_id": "employee_work_info__job_role_id__job_role",
        "employee_work_info__shift_id": "employee_work_info__shift_id__employee_shift",
        "employee_work_info__work_type_id": "employee_work_info__work_type_id__work_type",
        "employee_work_info__reporting_manager_id": "employee_work_info__reporting_manager_id__get_full_name",
        "employee_work_info__employee_type_id": "employee_work_info__employee_type_id__employee_type",
    }
    employees = EmployeeFilter(request.GET).qs
    employees = filtersubordinatesemployeemodel(
        request, employees, "employee.view_employee"
    )
    selected_fields = request.GET.getlist("selected_fields")
    if not selected_fields:
        selected_fields = form.fields["selected_fields"].initial
        ids = request.GET.get("ids")
        id_list = json.loads(ids)
        employees = Employee.objects.filter(id__in=id_list)

    prefetch_fields = list(set(f.split("__")[0] for f in selected_fields if "__" in f))
    if prefetch_fields:
        employees = employees.select_related(*prefetch_fields)

    for value, key in excel_columns:
        if value in selected_fields:
            selected_columns.append((value, key))

    date_format = "YYYY-MM-DD"
    user = request.user
    emp = getattr(user, "employee_get", None)
    if emp:
        info = EmployeeWorkInformation.objects.filter(employee_id=emp).first()
        if info:
            company = Company.objects.filter(company=info.company_id).first()
            if company and company.date_format:
                date_format = company.date_format

    employees_data = {column_name: [] for _, column_name in selected_columns}
    for employee in employees:
        for column_value, column_name in selected_columns:
            if column_value in field_overrides:
                column_value = field_overrides[column_value]

            nested_attrs = column_value.split("__")
            value = employee
            for attr in nested_attrs:
                value = getattr(value, attr, None)
                if value is None:
                    break

            # Call the value if it's employee_work_info__reporting_manager_id__get_full_name
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = ""

            data = str(value) if value is not None else ""

            if isinstance(value, date):
                try:
                    data = value.strftime(
                        HORILLA_DATE_FORMATS.get(date_format, "%Y-%m-%d")
                    )
                except Exception:
                    data = str(value)

            if data == "True":
                data = _("Yes")
            elif data == "False":
                data = _("No")

            employees_data[column_name].append(data)
    data_frame = pd.DataFrame(data=employees_data)
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="employee_export.xlsx"'
    data_frame.to_excel(response, index=False)

    return response


def birthday():
    """
    This method is used to find upcoming birthday and returns the queryset
    """
    today = datetime.now().date()
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    employees = Employee.objects.filter(
        is_active=True,
        dob__day__gte=today.day,
        dob__month=today.month,
        dob__day__lte=last_day_of_month,
    ).order_by(F("dob__day").asc(nulls_last=True))

    for employee in employees:
        employee.days_until_birthday = employee.dob.day - today.day
    return employees


@login_required
@enter_if_accessible(feature="birthday_view", perm="employee.view_employee")
def get_employees_birthday(request):
    """
    Render all upcoming birthday employee details for the dashboard.
    """
    employees = birthday()
    default_avatar_url = "https://ui-avatars.com/api/?background=random&name="
    birthdays = [
        {
            "profile": (
                emp.get_avatar()
                if hasattr(emp, "get_avatar")
                else f"{default_avatar_url}{emp.employee_first_name}+{emp.employee_last_name}"
            ),
            "name": f"{emp.employee_first_name} {emp.employee_last_name}",
            "dob": emp.dob.strftime("%d %b"),
            "daysUntilBirthday": (
                _("Today")
                if emp.days_until_birthday == 0
                else (
                    _("Tomorrow")
                    if emp.days_until_birthday == 1
                    else f"In {emp.days_until_birthday} Days"
                )
            ),
            "department": (
                emp.get_department().department if emp.get_department() else ""
            ),
            "job_position": (
                emp.get_job_position().job_position if emp.get_job_position() else ""
            ),
        }
        for emp in employees
    ]
    return render(
        request, "dashboard/birthdays_container.html", {"birthdays": birthdays}
    )


@login_required
@manager_can_enter("employee.view_employee")
def dashboard(request):
    """
    This method is used to render individual dashboard for employee module
    """
    upcoming_birthdays = birthday()
    employees = Employee.objects.all()
    employees = filtersubordinates(request, employees, "employee.view_employee")
    active_employees = employees.filter(is_active=True)
    inactive_employees = employees.filter(is_active=False)
    active_ratio = 0
    inactive_ratio = 0
    if employees.exists():
        active_ratio = f"{(len(active_employees) / len(employees)) * 100:.1f}"
        inactive_ratio = f"{(len(inactive_employees) / len(employees)) * 100:.1f}"

    return render(
        request,
        "employee/dashboard/dashboard_employee.html",
        {
            "birthdays": upcoming_birthdays,
            "active_employees": len(active_employees),
            "inactive_employees": len(inactive_employees),
            "total_employees": len(employees),
            "active_ratio": active_ratio,
            "inactive_ratio": inactive_ratio,
        },
    )


@login_required
def total_employees_count(request):
    employees = Employee.objects.all().count()
    return HttpResponse(employees)


@login_required
def joining_today_count(request):
    newbies_today = 0
    if apps.is_installed("recruitment"):
        Candidate = get_horilla_model_class(app_label="recruitment", model="candidate")
        newbies_today = Candidate.objects.filter(
            joining_date__range=[date.today(), date.today() + timedelta(days=1)],
            is_active=True,
        ).count()
    return HttpResponse(newbies_today)


@login_required
def joining_week_count(request):
    newbies_week = 0
    if apps.is_installed("recruitment"):
        Candidate = get_horilla_model_class(app_label="recruitment", model="candidate")
        newbies_week = Candidate.objects.filter(
            joining_date__range=[
                date.today() - timedelta(days=date.today().weekday()),
                date.today() + timedelta(days=6 - date.today().weekday()),
            ],
            is_active=True,
            hired=True,
        ).count()
    return HttpResponse(newbies_week)


@login_required
def dashboard_employee(request):
    """
    Active and in-active employee dashboard
    """
    labels = [
        _("Active"),
        _("In-Active"),
    ]
    employees = Employee.objects.filter()
    response = {
        "dataSet": [
            {
                "label": _("Employees"),
                "data": [
                    len(employees.filter(is_active=True)),
                    len(employees.filter(is_active=False)),
                ],
            },
        ],
        "labels": labels,
    }
    return JsonResponse(response)


@login_required
def dashboard_employee_gender(request):
    """
    This method is used to filter out gender vise employees
    """
    labels = [_("Male"), _("Female"), _("Other")]
    employees = Employee.objects.filter(is_active=True)

    response = {
        "dataSet": [
            {
                "label": _("Employees"),
                "data": [
                    len(employees.filter(gender="male")),
                    len(employees.filter(gender="female")),
                    len(employees.filter(gender="other")),
                ],
            },
        ],
        "labels": labels,
    }
    return JsonResponse(response)


@login_required
def dashboard_employee_department(request):
    """
    This method is used to find the count of employees corresponding to the departments
    """
    labels = []
    count = []
    departments = Department.objects.all()
    for dept in departments:
        if len(
            Employee.objects.filter(
                employee_work_info__department_id__department=dept, is_active=True
            )
        ):
            labels.append(dept.department)
            count.append(
                len(
                    Employee.objects.filter(
                        employee_work_info__department_id__department=dept,
                        is_active=True,
                    )
                )
            )
    response = {
        "dataSet": [{"label": "Department", "data": count}],
        "labels": labels,
        "message": _("No Data Found..."),
    }
    return JsonResponse(response)


@login_required
def widget_filter(request):
    """
    This method is used to return all the ids of the employees
    """
    ids = EmployeeFilter(request.GET).qs.values_list("id", flat=True)
    return JsonResponse({"ids": list(ids)})


@login_required
def employee_select(request):
    """
    This method is used to return all the id of the employees to select the employee row
    """
    page_number = request.GET.get("page")
    employees = Employee.objects.filter()
    if page_number == "all":
        employees = Employee.objects.filter(is_active=True)

    employee_ids = [str(emp.id) for emp in employees]
    total_count = employees.count()

    context = {"employee_ids": employee_ids, "total_count": total_count}

    return JsonResponse(context, safe=False)


@login_required
@manager_can_enter("employee.view_employee")
def employee_select_filter(request):
    """
    This method is used to return all the ids of the filtered employees
    """
    page_number = request.GET.get("page")
    if page_number == "all":
        employee_filter = EmployeeFilter(
            request.GET, queryset=Employee.objects.filter()
        )

        filtered_employees = filtersubordinatesemployeemodel(
            request=request, queryset=employee_filter.qs, perm="employee.view_employee"
        )
        employee_ids = [str(emp.id) for emp in filtered_employees]
        total_count = filtered_employees.count()

        context = {"employee_ids": employee_ids, "total_count": total_count}

        return JsonResponse(context)


@login_required
@hx_request_required
@manager_can_enter(perm="employee.view_employeenote")
def note_tab(request, emp_id):
    """
    This function is used to view note tab of an employee in employee individual
    & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return note-tab template

    """
    employee_obj = Employee.objects.get(id=emp_id)
    notes = EmployeeNote.objects.filter(employee_id=emp_id).order_by("-id")

    return render(
        request,
        "tabs/note_tab.html",
        {"employee": employee_obj, "notes": notes},
    )


@login_required
@hx_request_required
@manager_can_enter(perm="employee.add_employeenote")
def add_note(request, emp_id=None):
    """
    This method renders template component to add candidate remark
    """

    form = EmployeeNoteForm(initial={"employee_id": emp_id})
    if request.method == "POST":
        form = EmployeeNoteForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            note, attachment_ids = form.save(commit=False)
            employee = Employee.objects.get(id=emp_id)
            note.employee_id = employee
            note.updated_by = request.user.employee_get
            note.save()
            note.note_files.set(attachment_ids)
            messages.success(request, _("Note added successfully.."))
            return redirect(f"/employee/note-tab/{emp_id}")

    employee_obj = Employee.objects.get(id=emp_id)
    return render(
        request,
        "tabs/add_note.html",
        {
            "employee": employee_obj,
            "form": form,
        },
    )


@login_required
@manager_can_enter(perm="employee.change_employeenote")
def employee_note_update(request, note_id):
    """
    This method is used to update the note
    Args:
        id : stage note instance id
    """

    note = EmployeeNote.objects.get(id=note_id)

    form = EmployeeNoteForm(instance=note)
    if request.POST:
        form = EmployeeNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, _("Note updated successfully..."))
            response = render(
                request,
                "tabs/update_note.html",
                {"form": form},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "tabs/update_note.html",
        {
            "form": form,
        },
    )


@login_required
@manager_can_enter(perm="employee.delete_employeenote")
def employee_note_delete(request, note_id):
    """
    This method is used to delete the note
    Args:
        id : stage note instance id
    """

    note = EmployeeNote.objects.get(id=note_id)
    note.delete()
    messages.success(request, _("Note deleted successfully."))
    return HttpResponse()


@login_required
@hx_request_required
@manager_can_enter(perm="employee.add_notefiles")
def add_more_employee_files(request, note_id):
    """
    This method is used to Add more files to the Employee note.
    Args:
        id : stage note instance id
    """
    note = EmployeeNote.objects.get(id=note_id)
    employee_id = note.employee_id.id
    if request.method == "POST":
        files = request.FILES.getlist("files")
        files_ids = []
        for file in files:
            instance = NoteFiles.objects.create(files=file)
            files_ids.append(instance.id)

            note.note_files.add(instance.id)
    return redirect(f"/employee/note-tab/{employee_id}")


@login_required
@hx_request_required
@manager_can_enter(perm="employee.delete_notefiles")
def delete_employee_note_file(request, note_file_id):
    """
    This method is used to delete the stage note file
    Args:
        id : stage file instance id
    """
    file = NoteFiles.objects.get(id=note_file_id)
    file.delete()
    return HttpResponse()


@login_required
@hx_request_required
@owner_can_enter("employee.view_bonuspoint", Employee)
def bonus_points_tab(request, emp_id):
    """
    This function is used to view Bonus Points tab of an employee in employee individual
    & profile view.

    Parameters:
    request (HttpRequest): The HTTP request object.
    emp_id (int): The id of the employee.

    Returns: return bonus_points template

    """
    employee_obj = Employee.objects.get(id=emp_id)
    try:
        points = BonusPoint.objects.get(employee_id=emp_id)
        if apps.is_installed("payroll"):
            Reimbursement = get_horilla_model_class(
                app_label="payroll", model="reimbursement"
            )
            requested_bonus_points = Reimbursement.objects.filter(
                employee_id=emp_id, type="bonus_encashment", status="requested"
            )
        else:
            requested_bonus_points = QuerySet().none()
        trackings = points.tracking()
        activity_list = []
        for history in trackings:
            activity_list.append(
                {
                    "type": history["type"],
                    "date": history["pair"][0].history_date,
                    "points": history["pair"][0].points - history["pair"][1].points,
                    "user": getattr(
                        User.objects.filter(
                            id=history["pair"][0].history_user_id
                        ).first(),
                        "employee_get",
                        None,
                    ),
                    "reason": history["pair"][0].reason,
                }
            )
        for requested in requested_bonus_points:
            activity_list.append(
                {
                    "type": "requested",
                    "date": requested.created_at,
                    "points": requested.bonus_to_encash,
                    "user": employee_obj.employee_user_id,
                    "reason": "Redeemed points",
                }
            )
        activity_list = sorted(activity_list, key=lambda x: x["date"], reverse=True)
        context = {
            "employee": employee_obj,
            "points": points,
            "activity_list": activity_list,
        }
    except ObjectDoesNotExist:
        context = {
            "employee": employee_obj,
            "points": None,
            "activity_list": [],
        }
    return render(
        request,
        "tabs/bonus_points.html",
        context,
    )


@login_required
@manager_can_enter(perm="employee.add_bonuspoint")
def add_bonus_points(request, emp_id):
    """
    This function is used to add bonus points to an employee

    Args:
        request (HttpRequest): The HTTP request object.
        emp_id (int): The id of the employee.

    Returns: returns add_points form
    """

    bonus_point = BonusPoint.objects.get(employee_id=emp_id)
    form = BonusPointAddForm()
    if request.method == "POST":
        form = BonusPointAddForm(
            request.POST,
            request.FILES,
        )
        if form.is_valid():
            form.save(commit=False)
            bonus_point.points += form.cleaned_data["points"]
            bonus_point.reason = form.cleaned_data["reason"]
            bonus_point.save()
            messages.success(
                request,
                _("Added {} points to the bonus account").format(
                    form.cleaned_data["points"]
                ),
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return render(
        request,
        "tabs/forms/add_points.html",
        {
            "form": form,
            "emp_id": emp_id,
        },
    )


@login_required
@owner_can_enter("employee.view_bonuspoint", Employee)
def redeem_points(request, emp_id):
    """
    This function is used to redeem bonus points for an employee

    Args:
        request (HttpRequest): The HTTP request object.
        emp_id (int): The id of the employee.

    Returns: returns redeem_points_form form
    """
    employee = Employee.objects.get(id=emp_id)
    avialable_points = 0
    if BonusPoint.objects.filter(employee_id=employee).exists():
        avialable_points = (
            BonusPoint.objects.filter(employee_id=employee).first().points
        )
    form = BonusPointRedeemForm(initial={"points": avialable_points})
    form.instance.employee_id = employee

    amount_for_bonus_point = 0
    if apps.is_installed("payroll"):
        EncashmentGeneralSettings = get_horilla_model_class(
            app_label="payroll", model="encashmentgeneralsettings"
        )
        amount_for_bonus_point = (
            EncashmentGeneralSettings.objects.first().bonus_amount
            if EncashmentGeneralSettings.objects.first()
            else 1
        )
    if request.method == "POST":
        form = BonusPointRedeemForm(request.POST)
        form.instance.employee_id = employee
        if form.is_valid():
            form.save(commit=False)
            points = form.cleaned_data["points"]
            amount = amount_for_bonus_point * points
            if apps.is_installed("payroll"):
                Reimbursement = get_horilla_model_class(
                    app_label="payroll", model="reimbursement"
                )
                Reimbursement.objects.create(
                    title=f"Bonus point Redeem for {employee}",
                    type="bonus_encashment",
                    employee_id=employee,
                    bonus_to_encash=points,
                    amount=amount,
                    description=f"{employee} want to redeem {points} points",
                    allowance_on=date.today(),
                )
            return HttpResponse("<script>window.location.reload();</script>")
    return render(
        request,
        "tabs/forms/redeem_points_form.html",
        {
            "form": form,
            "employee": employee,
        },
    )


@login_required
def organisation_chart(request):
    """
    This method is used to view oganisation chart
    """
    selected_company = request.session.get("selected_company")
    if (
        request.GET.get("employee_work_info__company_id") == None
        and selected_company != "all"
    ):
        reporting_managers = Employee.objects.filter(
            is_active=True,
            reporting_manager__isnull=False,
            employee_work_info__company_id=selected_company,
        ).distinct()
    else:
        reporting_managers = Employee.objects.filter(
            is_active=True,
            reporting_manager__isnull=False,
        ).distinct()

    # Iterate through the queryset and add reporting manager id and name to the dictionary
    result_dict = {item.id: item.get_full_name() for item in reporting_managers}

    entered_req_managers = []

    # Helper function to recursively create the hierarchy structure
    def create_hierarchy(manager):
        """
        Hierarchy generator method
        """
        nodes = []
        # check the manager is a reporting manager if yes, store it into entered_req_managers
        if manager.id in result_dict.keys():
            entered_req_managers.append(manager)
        # filter the subordinates
        subordinates = Employee.objects.filter(
            is_active=True, employee_work_info__reporting_manager_id=manager
        ).exclude(id=manager.id)

        # itrating through subordinates
        for employee in subordinates:
            if employee in entered_req_managers:
                continue
            # check the employee is a reporting manager if yes,remove className store
            # it into entered_req_managers
            if employee.id in result_dict.keys():
                nodes.append(
                    {
                        "name": employee.get_full_name(),
                        "title": getattr(
                            employee.get_job_position(), "job_position", _("Not set")
                        ),
                        "children": create_hierarchy(employee),
                    }
                )
                entered_req_managers.append(employee)

            else:
                nodes.append(
                    {
                        "name": employee.get_full_name(),
                        "title": getattr(
                            employee.get_job_position(), "job_position", _("Not set")
                        ),
                        "className": "middle-level",
                        "children": create_hierarchy(employee),
                    }
                )
        return nodes

    selected_company = request.session.get("selected_company")
    if (
        request.GET.get("employee_work_info__company_id") == None
        and selected_company != "all"
    ):
        reporting_managers = Employee.objects.filter(
            is_active=True,
            reporting_manager__isnull=False,
            employee_work_info__company_id=selected_company,
        ).distinct()
    else:
        reporting_managers = Employee.objects.filter(
            is_active=True, reporting_manager__isnull=False
        ).distinct()

    manager = request.user.employee_get

    if len(reporting_managers) == 0:
        new_dict = {}
    else:
        new_dict = {reporting_managers[0].id: _("My view"), **result_dict}
    # POST method is used to change the reporting manager
    if request.method == "POST":
        if request.POST.get("manager_id"):
            manager_id = int(request.POST.get("manager_id"))
            manager = Employee.objects.get(id=manager_id)
        node = {
            "name": manager.get_full_name(),
            "title": getattr(manager.get_job_position(), "job_position", _("Not set")),
            "children": create_hierarchy(manager),
        }
        context = {"act_datasource": node}
        return render(request, "organisation_chart/chart.html", context=context)

    node = {
        "name": manager.get_full_name(),
        "title": getattr(manager.get_job_position(), "job_position", _("Not set")),
        "children": create_hierarchy(manager),
    }

    context = {
        "act_datasource": node,
        "reporting_manager_dict": new_dict,
        "act_manager_id": manager.id,
    }
    return render(request, "organisation_chart/org_chart.html", context=context)


@login_required
@permission_required("payroll.add_encashmentgeneralsettings")
def encashment_condition_create(request):
    """
    Handle the creation and updating of encashment general settings.
    """
    if apps.is_installed("payroll"):
        from payroll.forms.forms import EncashmentGeneralSettingsForm

        EncashmentGeneralSettings = get_horilla_model_class(
            app_label="payroll", model="encashmentgeneralsettings"
        )
        instance = (
            EncashmentGeneralSettings.objects.first()
            if apps.is_installed("payroll")
            else QuerySet().none()
        )

        if request.method == "POST":
            encashment_form = EncashmentGeneralSettingsForm(
                request.POST, instance=instance
            )
            if encashment_form.is_valid():
                encashment_form.save()
                messages.success(request, _("Settings updated."))
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        else:
            encashment_form = EncashmentGeneralSettingsForm(instance=instance)

        return render(
            request,
            "settings/encashment_settings.html",
            {"encashment_form": encashment_form},
        )

    messages.warning(request, _("Payroll app not installed"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("employee.add_employeegeneralsetting")
def initial_prefix(request):
    """
    This method is used to set the initial prefix using a form.
    """
    instance = EmployeeGeneralSetting.objects.first()  # Get the first instance or None
    if not instance:
        instance = EmployeeGeneralSetting()  # Create a new instance if none exists

    if request.method == "POST":
        form = EmployeeGeneralSettingPrefixForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Initial prefix updated successfully.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        else:
            messages.error(request, "There was an error updating the prefix.")
    else:
        form = EmployeeGeneralSettingPrefixForm(instance=instance)

    return render(request, "settings/settings.html", {"prefix_form": form})


@login_required
@manager_can_enter("employee.view_employee")
def first_last_badge(request):
    """
    This method is used to return the first last badge ids in grouped and ordere
    """
    badge_ids = get_ordered_badge_ids()

    return render(
        request,
        "employee_personal_info/first_last_badge.html",
        {"badge_ids": badge_ids},
    )


@login_required
@hx_request_required
@manager_can_enter("employee.view_employee")
def employee_get_mail_log(request):
    """
    This method is used to track mails sent along with the status
    """
    employee_id = request.GET["emp_id"]
    employee = Employee.objects.get(id=employee_id)
    tracked_mails = EmailLog.objects.filter(to__icontains=employee.email)
    try:
        if employee.employee_work_info and employee.employee_work_info.email:
            tracked_mails = tracked_mails | EmailLog.objects.filter(
                to__icontains=employee.employee_work_info.email
            )
        tracked_mails = tracked_mails.order_by("-created_at")

        return render(request, "tabs/mail_log.html", {"tracked_mails": tracked_mails})
    except ObjectDoesNotExist:
        return render(request, "tabs/mail_log.html", {"tracked_mails": []})


@login_required
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
def get_job_roles(request):
    """
    Retrieve job roles associated with a specific job position.

    This view function extracts the job_id from the GET request, queries the
    JobRole model for job roles that match the provided job_position_id, and
    returns the results as a JSON response.
    """
    job_id = request.GET.get("job_id")
    job_roles = JobRole.objects.filter(job_position_id=job_id).values_list(
        "id", "job_role"
    )
    return JsonResponse({"job_roles": dict(job_roles)})


@login_required
@permission_required("employee.view_employeetag")
def employee_tag_view(request):
    """
    This method is used to Employee tags
    """
    employeetags = EmployeeTag.objects.all()
    return render(
        request,
        "base/tags/employee_tags.html",
        {"employeetags": employeetags},
    )


@login_required
@hx_request_required
@permission_required("employee.add_employeetag")
def employee_tag_create(request):
    """
    This method renders form and template to create Ticket type
    """
    form = EmployeeTagForm()
    if request.method == "POST":
        form = EmployeeTagForm(request.POST)
        if form.is_valid():
            form.save()
            form = EmployeeTagForm()
            messages.success(request, _("Tag has been created successfully!"))
    return render(
        request,
        "base/employee_tag/employee_tag_form.html",
        {
            "form": form,
        },
    )


@login_required
@hx_request_required
@permission_required("employee.add_employeetag")
def employee_tag_update(request, tag_id):
    """
    This method renders form and template to create Ticket type
    """
    tag = EmployeeTag.objects.get(id=tag_id)
    form = EmployeeTagForm(instance=tag)
    if request.method == "POST":
        form = EmployeeTagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            form = EmployeeTagForm()
            messages.success(request, _("Tag has been updated successfully!"))
            return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "base/employee_tag/employee_tag_form.html",
        {"form": form, "tag_id": tag_id},
    )
