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


# @login_required
# def payslip_export(request):
#     """
#     This view exports payslip data based on selected fields and filters,
#     and generates an Excel file for download.
#     """
#     choices_mapping = {
#         "draft": _("Draft"),
#         "review_ongoing": _("Review Ongoing"),
#         "confirmed": _("Confirmed"),
#         "paid": _("Paid"),
#     }
#     selected_columns = []
#     payslips_data = {}
#     payslips = PayslipFilter(request.GET).qs
#     today_date = date.today().strftime("%Y-%m-%d")
#     file_name = f"Payslip_excel_{today_date}.xlsx"
#     selected_fields = request.GET.getlist("selected_fields")
#     form = forms.PayslipExportColumnForm()

#     if not selected_fields:
#         selected_fields = form.fields["selected_fields"].initial
#         ids = request.GET.get("ids")
#         id_list = json.loads(ids)
#         payslips = Payslip.objects.filter(id__in=id_list)

#     for field in forms.excel_columns:
#         value = field[0]
#         key = field[1]
#         if value in selected_fields:
#             selected_columns.append((value, key))

#     for column_value, column_name in selected_columns:
#         nested_attributes = column_value.split("__")
#         payslips_data[column_name] = []
#         for payslip in payslips:
#             value = payslip
#             for attr in nested_attributes:
#                 value = getattr(value, attr, None)
#                 if value is None:
#                     break
#             data = str(value) if value is not None else ""
#             if column_name == "Status":
#                 data = choices_mapping.get(value, "")

#             if type(value) == date:
#                 user = request.user
#                 employee = user.employee_get

#                 # Taking the company_name of the user
#                 info = EmployeeWorkInformation.objects.filter(employee_id=employee)
#                 if info.exists():
#                     for i in info:
#                         employee_company = i.company_id
#                     company_name = Company.objects.filter(company=employee_company)
#                     emp_company = company_name.first()

#                     # Access the date_format attribute directly
#                     date_format = (
#                         emp_company.date_format if emp_company else "MMM. D, YYYY"
#                     )
#                 else:
#                     date_format = "MMM. D, YYYY"

#                 # Convert the string to a datetime.date object
#                 start_date = datetime.strptime(str(value), "%Y-%m-%d").date()

#                 # Print the formatted date for each format
#                 for format_name, format_string in HORILLA_DATE_FORMATS.items():
#                     if format_name == date_format:
#                         data = start_date.strftime(format_string)
#             else:
#                 data = str(value) if value is not None else ""
#             payslips_data[column_name].append(data)

#     data_frame = pd.DataFrame(data=payslips_data)
#     response = HttpResponse(
#         content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )
#     response["Content-Disposition"] = f'attachment; filename="{file_name}"'

#     writer = pd.ExcelWriter(response, engine="xlsxwriter")
#     data_frame.style.map(lambda x: "text-align: center").to_excel(
#         writer, index=False, sheet_name="Sheet1"
#     )
#     worksheet = writer.sheets["Sheet1"]
#     worksheet.set_column("A:Z", 20)
#     writer.close()
#     return response


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
    email_backend = ConfiguredEmailBackend()
    host = email_backend.dynamic_from_email_with_display_name

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
            subject,
            render_bdy,
            host,
            [send_to_mail],
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
