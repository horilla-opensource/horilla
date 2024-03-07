"""
employee/context_processors.py

This module is used to write context processor methods
"""

from datetime import date
from django import template
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.mail import EmailMessage
from base.methods import generate_pdf
from employee.models import Employee
from horilla.decorators import manager_can_enter, login_required
from horilla import settings
from employee.filters import EmployeeFilter
from recruitment.models import RecruitmentMailTemplate
from django.core.paginator import Paginator
from base.backends import ConfiguredEmailBackend


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
def send_mail(request, emp_id):
    """
    This method used send mail to the employees
    """
    employeee = Employee.objects.get(id=emp_id)
    templates = RecruitmentMailTemplate.objects.all()
    return render(
        request,
        "employee/send_mail.html",
        {"employee": employeee, "templates": templates},
    )


@login_required
def get_template(request, emp_id):
    """
    This method is used to return the mail template
    """
    body = RecruitmentMailTemplate.objects.get(id=emp_id).body
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
    other_attachments = request.FILES.getlist("other_attachments")
    attachments = [
        (file.name, file.read(), file.content_type) for file in other_attachments
    ]
    email_backend = ConfiguredEmailBackend()
    host = email_backend.dynamic_username
    employee = Employee.objects.get(id=employee_id)
    template_attachment_ids = request.POST.getlist("template_attachments")
    bodys = list(
        RecruitmentMailTemplate.objects.filter(
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

    email = EmailMessage(
        subject,
        render_bdy,
        host,
        [employee.employee_work_info.email],
    )
    email.content_subtype = "html"

    email.attachments = attachments
    try:
        email.send()
        if employee.employee_work_info.email:
            messages.success(request, f"Mail sent to {employee.get_full_name()}")
        else:
            messages.info(request, f"Email not set for {employee.get_full_name()}")
    except Exception as e:
        messages.error(request, "Something went wrong")
    return HttpResponse("<script>window.location.reload()</script>")
