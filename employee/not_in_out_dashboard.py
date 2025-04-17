"""
employee/context_processors.py

This module is used to write context processor methods
"""

import json
from datetime import date

from django import template
from django.apps import apps
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from base.backends import ConfiguredEmailBackend
from base.methods import export_data, generate_pdf
from base.models import HorillaMailTemplate
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla import settings
from horilla.decorators import login_required, manager_can_enter


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate query set
    """
    paginator = Paginator(qryset, 20)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@manager_can_enter("employee.view_employee")
def not_in_yet(request):
    """
    This context processor wil return the employees, if they not marked the attendance
    for the day
    """
    page_number = request.GET.get("page")
    previous_data = request.GET.urlencode()
    emps = (
        EmployeeFilter({"not_in_yet": date.today()})
        .qs.exclude(employee_work_info__isnull=True)
        .filter(is_active=True)
    )

    return render(
        request,
        "dashboard/not_in_yet.html",
        {
            "employees": paginator_qry(emps, page_number),
            "pd": previous_data,
        },
    )


@login_required
@manager_can_enter("employee.view_employee")
def not_out_yet(request):
    """
    This context processor wil return the employees, if they not marked the attendance
    for the day
    """
    emps = (
        EmployeeFilter({"not_out_yet": date.today()})
        .qs.exclude(employee_work_info__isnull=True)
        .filter(is_active=True)
    )
    return render(request, "dashboard/not_out_yet.html", {"employees": emps})


@login_required
@manager_can_enter("employee.change_employee")
def send_mail(request, emp_id=None):
    """
    This method used send mail to the employees
    """
    employee = None
    if emp_id:
        employee = Employee.objects.get(id=emp_id)
    employees = Employee.objects.all()

    templates = HorillaMailTemplate.objects.all()
    return render(
        request,
        "employee/send_mail.html",
        {"employee": employee, "templates": templates, "employees": employees},
    )


@login_required
@manager_can_enter("employee.change_employee")
def employee_data_export(request, emp_id=None):
    """
    This method used send mail to the employees
    """

    resolver_match = request.resolver_match
    if (
        resolver_match
        and resolver_match.url_name
        and resolver_match.url_name == "export-data-employee"
    ):
        employee = None
        if emp_id:
            employee = Employee.objects.get(id=emp_id)

        context = {"employee": employee}

        # IF LEAVE IS INSTALLED
        if apps.is_installed("leave"):
            from leave.filters import LeaveRequestFilter
            from leave.forms import LeaveRequestExportForm

            excel_column = LeaveRequestExportForm()
            export_filter = LeaveRequestFilter()
            context.update(
                {
                    "leave_excel_column": excel_column,
                    "leave_export_filter": export_filter.form,
                }
            )

        # IF ATTENDANCE IS INSTALLED
        if apps.is_installed("attendance"):
            from attendance.filters import AttendanceFilters
            from attendance.forms import AttendanceExportForm
            from attendance.models import Attendance

            excel_column = AttendanceExportForm()
            export_filter = AttendanceFilters()
            context.update(
                {
                    "attendance_excel_column": excel_column,
                    "attendance_export_filter": export_filter.form,
                }
            )

        # IF PAYROLL IS INSTALLED
        if apps.is_installed("payroll"):
            from payroll.filters import PayslipFilter
            from payroll.forms.component_forms import PayslipExportColumnForm

            context.update(
                {
                    "payroll_export_column": PayslipExportColumnForm(),
                    "payroll_export_filter": PayslipFilter(request.GET),
                }
            )

        return render(request, "employee/export_data_employee.html", context=context)
    return export_data(
        request=request,
        model=Attendance,
        filter_class=AttendanceFilters,
        form_class=AttendanceExportForm,
        file_name="Attendance_export",
    )


@login_required
def get_template(request, emp_id):
    """
    This method is used to return the mail template
    """
    body = HorillaMailTemplate.objects.get(id=emp_id).body
    instance_id = request.GET.get("instance_id")
    if instance_id:
        instance = Employee.objects.get(id=instance_id)
        template_bdy = template.Template(body)
        context = template.Context(
            {"instance": instance, "self": request.user.employee_get}
        )
        body = template_bdy.render(context)

    return JsonResponse({"body": body})


@login_required
@manager_can_enter(perm="recruitment.change_employee")
def send_mail_to_employee(request):
    """
    This method is used to send acknowledgement mail to the candidate
    """
    employee_id = request.POST["id"]
    subject = request.POST.get("subject")
    bdy = request.POST.get("body")

    employee_ids = request.POST.getlist("employees")
    employees = Employee.objects.filter(id__in=employee_ids)

    other_attachments = request.FILES.getlist("other_attachments")
    attachments = [
        (file.name, file.read(), file.content_type) for file in other_attachments
    ]

    if employee_id:
        employee_obj = Employee.objects.filter(id=employee_id)
    else:
        employee_obj = Employee.objects.none()
    employees = (employees | employee_obj).distinct()

    template_attachment_ids = request.POST.getlist("template_attachments")
    for employee in employees:
        bodys = list(
            HorillaMailTemplate.objects.filter(
                id__in=template_attachment_ids
            ).values_list("body", flat=True)
        )
        for html in bodys:
            # due to not having solid template we first need to pass the context
            template_bdy = template.Template(html)
            context = template.Context(
                {"instance": employee, "self": request.user.employee_get}
            )
            render_bdy = template_bdy.render(context)
            attachments.append(
                (
                    "Document",
                    generate_pdf(render_bdy, {}, path=False, title="Document").content,
                    "application/pdf",
                )
            )

        template_bdy = template.Template(bdy)
        context = template.Context(
            {"instance": employee, "self": request.user.employee_get}
        )
        render_bdy = template_bdy.render(context)
        send_to_mail = (
            employee.employee_work_info.email
            if employee.employee_work_info and employee.employee_work_info.email
            else employee.email
        )

        email = EmailMessage(
            subject=subject,
            body=render_bdy,
            to=[send_to_mail],
        )
        email.content_subtype = "html"

        email.attachments = attachments
        try:
            email.send()
            if employee.employee_work_info.email or employee.email:
                messages.success(request, f"Mail sent to {employee.get_full_name()}")
            else:
                messages.info(request, f"Email not set for {employee.get_full_name()}")
        except Exception as e:
            messages.error(request, "Something went wrong")
    return HttpResponse("<script>window.location.reload()</script>")
