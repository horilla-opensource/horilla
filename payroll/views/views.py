"""
views.py

This module is used to define the method for the path in the urls
"""
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from horilla.decorators import login_required, permission_required
from employee.models import Employee, EmployeeWorkInformation
from payroll.models.models import Payslip, WorkRecord
from payroll.models.models import Contract
from payroll.forms.forms import ContractForm, WorkRecordForm
from payroll.models.tax_models import PayrollSettings
from payroll.forms.component_forms import PayrollSettingsForm
from payroll.filters import ContractFilter
from payroll.methods.methods import paginator_qry

# Create your views here.


@login_required
@permission_required("payroll.view_dashboard")
def dashboard(request):
    """
    Dashboard render views
    """
    return render(request, "payroll/dashboard.html")


@login_required
@permission_required("payroll.add_contract")
def contract_create(request):
    """
    Contract create view
    """
    form = ContractForm()
    if request.method == "POST":
        form = ContractForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Contract Created"))
            return redirect(contract_view)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.change_contract")
def contract_update(request, contract_id):
    """
    Update an existing contract.

    Args:
        request: The HTTP request object.
        contract_id: The ID of the contract to update.

    Returns:
        If the request method is POST and the form is valid, redirects to the contract view.
        Otherwise, renders the contract update form.

    """
    contract = Contract.objects.get(id=contract_id)
    contract_form = ContractForm(instance=contract)
    if request.method == "POST":
        contract_form = ContractForm(request.POST, request.FILES, instance=contract)
        if contract_form.is_valid():
            contract_form.save()
            messages.success(request, _("Contract updated"))
            return redirect(contract_view)
    return render(
        request,
        "payroll/common/form.html",
        {
            "form": contract_form,
        },
    )


@login_required
@permission_required("payroll.delete_contract")
def contract_delete(request, contract_id):
    """
    Delete a contract.

    Args:
        contract_id: The ID of the contract to delete.

    Returns:
        Redirects to the contract view after successfully deleting the contract.

    """
    Contract.objects.get(id=contract_id).delete()
    messages.success(request, _("Contract deleted"))
    return redirect(contract_view)


@login_required
@permission_required("payroll.view_contract")
def contract_view(request):
    """
    Contract view method
    """

    contracts = Contract.objects.all()
    contracts = paginator_qry(contracts, request.GET.get("page"))
    filter_form = ContractFilter(request.GET)
    context = {"contracts": contracts, "f": filter_form}

    return render(request, "payroll/contract/contract_view.html", context)


@login_required
@permission_required("payroll.view_contract")
def view_single_contract(request, contract_id):
    """
    Renders a single contract view page.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - contract_id (int): The ID of the contract to view.

    Returns:
        The rendered contract single view page.

    """
    contract = Contract.objects.get(id=contract_id)
    context = {"contract": contract}
    return render(request, "payroll/contract/contract_single_view.html", context)


@login_required
@permission_required("payroll.view_contract")
def contract_filter(request):
    """
    Filter contracts based on the provided query parameters.

    Args:
        request: The HTTP request object containing the query parameters.

    Returns:
        Renders the contract list template with the filtered contracts.

    """
    query_string = request.environ["QUERY_STRING"]
    contracts_filter = ContractFilter(request.GET)
    template = "payroll/contract/contract_list.html"
    contracts = contracts_filter.qs
    contracts = paginator_qry(contracts, request.GET.get("page"))
    return render(request, template, {"contracts": contracts, "pd": query_string})


@login_required
@permission_required("payroll.view_workrecord")
def work_record_create(request):
    """
    Work record create view
    """
    form = WorkRecordForm()

    context = {"form": form}
    if request.POST:
        form = WorkRecordForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            context["form"] = form
    return render(request, "payroll/work_record/work_record_create.html", context)


@login_required
@permission_required("payroll.view_workrecord")
def work_record_view(request):
    """
    Work record view method
    """
    contracts = WorkRecord.objects.all()
    context = {"contracts": contracts}
    return render(request, "payroll/work_record/work_record_view.html", context)


@login_required
@permission_required("payroll.workrecord")
def work_record_employee_view(request):
    """
    Work record by employee view method
    """
    current_month_start_date = datetime.now().replace(day=1)
    next_month_start_date = current_month_start_date + timedelta(days=31)
    current_month_records = WorkRecord.objects.filter(
        start_datetime__gte=current_month_start_date,
        start_datetime__lt=next_month_start_date,
    ).order_by("start_datetime")
    current_date = timezone.now().date()
    current_month = current_date.strftime("%B")
    start_of_month = current_date.replace(day=1)
    employees = Employee.objects.all()

    current_month_dates_list = [
        datetime.now().replace(day=day).date() for day in range(1, 32)
    ]

    context = {
        "days": range(1, 32),
        "employees": employees,
        "current_date": current_date,
        "current_month": current_month,
        "start_of_month": start_of_month,
        "current_month_dates_list": current_month_dates_list,
        "work_records": current_month_records,
    }

    return render(
        request, "payroll/work_record/work_record_employees_view.html", context
    )


@login_required
@permission_required("payroll.view_settings")
def settings(request):
    """
    This method is used to render settings template
    """
    instance = PayrollSettings.objects.first()
    form = PayrollSettingsForm(instance=instance)
    if request.method == "POST":
        form = PayrollSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Payroll settings updated."))
    return render(request, "payroll/settings/payroll_settings.html", {"form": form})


@login_required
@permission_required("payroll.change_payslip")
def update_payslip_status(request):
    """
    This method is used to update the payslip confirmation status
    """
    pay_data = json.loads(request.GET["data"])
    emp_id = pay_data["employee"]
    employee = Employee.objects.get(id=emp_id)
    start_date = pay_data["start_date"]
    end_date = pay_data["end_date"]
    status = pay_data["status"]
    contract_wage = pay_data["contract_wage"]
    basic_pay = pay_data["basic_pay"]
    gross_pay = pay_data["gross_pay"]
    deduction = pay_data["total_deductions"]
    net_pay = pay_data["net_pay"]

    filtered_instance = Payslip.objects.filter(
        employee_id=employee,
        start_date=start_date,
        end_date=end_date,
    ).first()
    instance = filtered_instance if filtered_instance is not None else Payslip()
    instance.employee_id = employee
    instance.start_date = start_date
    instance.end_date = end_date
    instance.status = status
    instance.basic_pay = basic_pay
    instance.contract_wage = contract_wage
    instance.gross_pay = gross_pay
    instance.deduction = deduction
    instance.net_pay = net_pay
    instance.pay_head_data = pay_data
    instance.save()
    return JsonResponse({"message": "success"})


@login_required
@permission_required("payroll.change_payslip")
def bulk_update_payslip_status(request):
    """
    This method is used to update payslip status when generating payslip through
    generate payslip method
    """
    json_data = request.GET["json_data"]
    pay_data = json.loads(json_data)
    status = request.GET["status"]

    for json_entry in pay_data:
        data = json.loads(json_entry)
        emp_id = data["employee"]
        employee = Employee.objects.get(id=emp_id)

        payslip_kwargs = {
            "employee_id": employee,
            "start_date": data["start_date"],
            "end_date": data["end_date"],
        }
        filtered_instance = Payslip.objects.filter(**payslip_kwargs).first()
        instance = filtered_instance if filtered_instance is not None else Payslip()

        instance.employee_id = employee
        instance.start_date = data["start_date"]
        instance.end_date = data["end_date"]
        instance.status = status
        instance.basic_pay = data["basic_pay"]
        instance.contract_wage = data["contract_wage"]
        instance.gross_pay = data["gross_pay"]
        instance.deduction = data["total_deductions"]
        instance.net_pay = data["net_pay"]
        instance.pay_head_data = data
        instance.save()

    return JsonResponse({"message": "success"})


@login_required
# @permission_required("payroll.view_payslip")
def view_created_payslip(request, payslip_id):
    """
    This method is used to view the saved payslips
    """
    payslip = Payslip.objects.get(id=payslip_id)
    # the data must be dictionary in the payslip model for the json field
    data = payslip.pay_head_data
    data["employee"] = payslip.employee_id
    data["payslip"] = payslip
    data["json_data"] = data.copy()
    data["json_data"]["employee"] = payslip.employee_id.id
    data["json_data"]["payslip"] = payslip.id

    return render(request, "payroll/payslip/individual_payslip.html", data)


@login_required
@permission_required("payroll.delete_payslip")
def delete_payslip(request, payslip_id):
    """
    This method is used to delete payslip instances
    Args:
        payslip_id (int): Payslip model instance id
    """
    try:
        Payslip.objects.get(id=payslip_id).delete()
        messages.success(request, _("Payslip deleted"))
    except:
        messages.error(request, _("Something went wrong"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("payroll.add_contract")
def contract_info_initial(request):
    """
    This is an ajax method to return json response to auto fill the contract
    form fields
    """
    employee_id = request.GET["employee_id"]
    work_info = EmployeeWorkInformation.objects.filter(employee_id=employee_id).first()
    response_data = {
        "department": work_info.department_id.id
        if work_info.department_id is not None
        else "",
        "job_position": work_info.job_position_id.id
        if work_info.job_position_id is not None
        else "",
        "job_role": work_info.job_role_id.id
        if work_info.job_role_id is not None
        else "",
        "shift": work_info.shift_id.id if work_info.shift_id is not None else "",
        "work_type": work_info.work_type_id.id
        if work_info.work_type_id is not None
        else "",
        "wage": work_info.basic_salary,
    }
    return JsonResponse(response_data)
