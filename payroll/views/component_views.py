"""
component_views.py

This module is used to write methods to the component_urls patterns respectively
"""
import json
import operator
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from horilla.decorators import login_required, permission_required
import payroll.models.models
from payroll.methods.payslip_calc import (
    calculate_allowance,
    calculate_gross_pay,
    calculate_taxable_gross_pay,
)
from payroll.methods.payslip_calc import (
    calculate_post_tax_deduction,
    calculate_pre_tax_deduction,
    calculate_tax_deduction,
)
from payroll.filters import AllowanceFilter, DeductionFilter, PayslipFilter
from payroll.forms import component_forms as forms
from payroll.methods.payslip_calc import (
    calculate_net_pay_deduction,
)
from payroll.methods.tax_calc import calculate_taxable_amount
from payroll.methods.methods import compute_salary_on_period, paginator_qry
from payroll.methods.deductions import update_compensation_deduction

operator_mapping = {
    "equal": operator.eq,
    "notequal": operator.ne,
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
    "icontains": operator.contains,
}


def payroll_calculation(employee, start_date, end_date):
    """
    Calculate payroll components for the specified employee within the given date range.


    Args:
        employee (Employee): The employee for whom the payroll is calculated.
        start_date (date): The start date of the payroll period.
        end_date (date): The end date of the payroll period.


    Returns:
        dict: A dictionary containing the calculated payroll components:
    """

    basic_pay_details = compute_salary_on_period(employee, start_date, end_date)
    contract = basic_pay_details["contract"]
    contract_wage = basic_pay_details["contract_wage"]
    basic_pay = basic_pay_details["basic_pay"]
    loss_of_pay = basic_pay_details["loss_of_pay"]

    working_days_details = basic_pay_details["month_data"]

    updated_basic_pay_data = update_compensation_deduction(
        employee, basic_pay, "basic_pay", start_date, end_date
    )
    basic_pay = updated_basic_pay_data["compensation_amount"]
    basic_pay_deductions = updated_basic_pay_data["deductions"]

    loss_of_pay_amount = float(loss_of_pay) if not contract.deduct_leave_from_basic_pay else 0

    basic_pay = basic_pay - loss_of_pay_amount

    kwargs = {
        "employee": employee,
        "start_date": start_date,
        "end_date": end_date,
        "basic_pay": basic_pay,
        "day_dict": working_days_details,
    }
    # basic pay will be basic_pay = basic_pay - update_compensation_amount
    allowances = calculate_allowance(**kwargs)

    # finding the total allowance
    total_allowance = sum(allowance["amount"] for allowance in allowances["allowances"])

    kwargs["allowances"] = allowances
    kwargs["total_allowance"] = total_allowance
    gross_pay = calculate_gross_pay(**kwargs)["gross_pay"]
    updated_gross_pay_data = update_compensation_deduction(
        employee, gross_pay, "gross_pay", start_date, end_date
    )
    gross_pay = updated_gross_pay_data["compensation_amount"]
    gross_pay_deductions = updated_gross_pay_data["deductions"]

    pretax_deductions = calculate_pre_tax_deduction(**kwargs)
    post_tax_deductions = calculate_post_tax_deduction(**kwargs)

    taxable_gross_pay = calculate_taxable_gross_pay(**kwargs)
    tax_deductions = calculate_tax_deduction(**kwargs)
    federal_tax = calculate_taxable_amount(**kwargs)

    # gross_pay = (basic_pay + total_allowances)
    # deduction = (
    #   post_tax_deductions_amount
    #   + pre_tax_deductions _amount
    #   + tax_deductions + federal_tax_amount
    #   + lop_amount
    #   + one_time_basic_deduction_amount
    #   + one_time_gross_deduction_amount
    #   )
    # net_pay = gross_pay - deduction
    # net_pay = net_pay - net_pay_deduction

    total_allowance = sum(item["amount"] for item in allowances["allowances"])
    total_pretax_deduction = sum(
        item["amount"] for item in pretax_deductions["pretax_deductions"]
    )
    total_post_tax_deduction = sum(
        item["amount"] for item in post_tax_deductions["post_tax_deductions"]
    )
    total_tax_deductions = sum(
        item["amount"] for item in tax_deductions["tax_deductions"]
    )

    total_deductions = (
        total_pretax_deduction
        + total_post_tax_deduction
        + total_tax_deductions
        + federal_tax
        + loss_of_pay_amount
    )

    net_pay = (basic_pay + total_allowance) - total_deductions
    updated_net_pay_data = update_compensation_deduction(
        employee, net_pay, "net_pay", start_date, end_date
    )
    net_pay = updated_net_pay_data["compensation_amount"]
    update_net_pay_deductions = updated_net_pay_data["deductions"]

    net_pay_deductions = calculate_net_pay_deduction(
        net_pay, post_tax_deductions["net_pay_deduction"], working_days_details
    )
    net_pay_deduction_list = net_pay_deductions["net_pay_deductions"]
    for deduction in update_net_pay_deductions:
        net_pay_deduction_list.append(deduction)
    net_pay = net_pay - net_pay_deductions["net_deduction"]
    payslip_data = {
        "net_pay": net_pay,
        "employee": employee,
        "allowances": allowances["allowances"],
        "gross_pay": gross_pay,
        "contract_wage": contract_wage,
        "basic_pay": basic_pay,
        "taxable_gross_pay": taxable_gross_pay,
        "basic_pay_deductions": basic_pay_deductions,
        "gross_pay_deductions": gross_pay_deductions,
        "pretax_deductions": pretax_deductions["pretax_deductions"],
        "post_tax_deductions": post_tax_deductions["post_tax_deductions"],
        "tax_deductions": tax_deductions["tax_deductions"],
        "net_deductions": net_pay_deduction_list,
        "total_deductions": total_deductions,
        "loss_of_pay": loss_of_pay,
        "federal_tax": federal_tax,
        "start_date": start_date,
        "end_date": end_date,
        "range": f"{start_date.strftime('%b %d %Y')} - {end_date.strftime('%b %d %Y')}",
    }
    data_to_json = payslip_data.copy()
    data_to_json["employee"] = employee.id
    data_to_json["start_date"] = start_date.strftime("%Y-%m-%d")
    data_to_json["end_date"] = end_date.strftime("%Y-%m-%d")
    json_data = json.dumps(data_to_json)

    payslip_data["json_data"] = json_data
    return payslip_data


@login_required
@permission_required("payroll.add_allowance")
def create_allowance(request):
    """
    This method is used to create allowance condition template
    """
    form = forms.AllowanceForm()
    if request.method == "POST":
        form = forms.AllowanceForm(request.POST)
        if form.is_valid():
            form.save()
            form = forms.AllowanceForm()
            messages.success(request, "Allowance created.")
            return redirect(view_allowance)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.view_allowance")
def view_allowance(request):
    """
    This method is used render template to view all the allowance instances
    """
    allowances = payroll.models.models.Allowance.objects.all()
    allowance_filter = AllowanceFilter(request.GET)
    allowances = paginator_qry(allowances, request.GET.get("page"))
    return render(
        request,
        "payroll/allowance/view_allowance.html",
        {"allowances": allowances, "f": allowance_filter},
    )


@login_required
@permission_required("payroll.view_allowance")
def view_single_allowance(request, allowance_id):
    """
    This method is used render template to view the selected allowance instances
    """
    allowance = payroll.models.models.Allowance.objects.get(id=allowance_id)
    return render(
        request,
        "payroll/allowance/view_single_allowance.html",
        {"allowance": allowance},
    )


@login_required
@permission_required("payroll.view_allowance")
def filter_allowance(request):
    """
    Filter and retrieve a list of allowances based on the provided query parameters.
    """
    query_string = request.environ["QUERY_STRING"]
    allowances = AllowanceFilter(request.GET).qs
    template = "payroll/allowance/list_allowance.html"
    allowances = paginator_qry(allowances, request.GET.get("page"))
    return render(request, template, {"allowances": allowances, "pd": query_string})


@login_required
@permission_required("payroll.change_allowance")
def update_allowance(request, allowance_id):
    """
    This method is used to update the allowance
    Args:
        id : allowance instance id
    """
    instance = payroll.models.models.Allowance.objects.get(id=allowance_id)
    form = forms.AllowanceForm(instance=instance)
    if request.method == "POST":
        form = forms.AllowanceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Allowance updated.")
            return redirect(view_allowance)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.delete_allowance")
def delete_allowance(request, allowance_id):
    """
    This method is used to delete the allowance instance
    """
    try:
        payroll.models.models.Allowance.objects.get(id=allowance_id).delete()
        messages.success(request, "Allowance deleted")
    except ObjectDoesNotExist(Exception):
        messages.error(request, "Allowance not found")
    except ValidationError as validation_error:
        messages.error(
            request, "Validation error occurred while deleting the allowance"
        )
        messages.error(request, str(validation_error))
    except Exception as exception:
        messages.error(request, "An error occurred while deleting the allowance")
        messages.error(request, str(exception))
    return redirect(view_allowance)


@login_required
@permission_required("payroll.add_deduction")
def create_deduction(request):
    """
    This method is used to create deduction
    """
    form = forms.DeductionForm()
    if request.method == "POST":
        form = forms.DeductionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Deduction created.")
            return redirect(view_deduction)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.view_allowance")
def view_deduction(request):
    """
    This method is used render template to view all the deduction instances
    """

    deductions = payroll.models.models.Deduction.objects.all()
    deduction_filter = DeductionFilter(request.GET)
    deductions = paginator_qry(deductions, request.GET.get("page"))
    return render(
        request,
        "payroll/deduction/view_deduction.html",
        {"deductions": deductions, "f": deduction_filter},
    )


@login_required
@permission_required("payroll.view_allowance")
def view_single_deduction(request, deduction_id):
    """
    This method is used render template to view all the deduction instances
    """

    deduction = payroll.models.models.Deduction.objects.get(id=deduction_id)
    return render(
        request,
        "payroll/deduction/view_single_deduction.html",
        {"deduction": deduction},
    )


@login_required
@permission_required("payroll.view_allowance")
def filter_deduction(request):
    """
    This method is used search the deduction
    """
    query_string = request.environ["QUERY_STRING"]
    deductions = DeductionFilter(request.GET).qs
    template = "payroll/deduction/list_deduction.html"
    deductions = paginator_qry(deductions, request.GET.get("page"))
    return render(request, template, {"deductions": deductions, "pd": query_string})


@login_required
@permission_required("payroll.change_deduction")
def update_deduction(request, deduction_id):
    """
    This method is used to update the deduction instance
    """
    instance = payroll.models.models.Deduction.objects.get(id=deduction_id)
    form = forms.DeductionForm(instance=instance)
    if request.method == "POST":
        form = forms.DeductionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Deduction updated.")
            return redirect(view_deduction)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.delete_deduction")
def delete_deduction(_request, deduction_id):
    """
    This method is used to delete the deduction instance
    Args:
        id : deduction instance id
    """
    payroll.models.models.Deduction.objects.get(id=deduction_id).delete()
    return redirect(view_deduction)


@login_required
@permission_required("payroll.add_payslip")
def generate_payslip(request):
    """
    Generate payslips for selected employees within a specified date range.

    Requires the user to be logged in and have the 'payroll.add_payslip' permission.

    """
    payslip_data = []
    json_data = []
    form = forms.GeneratePayslipForm()
    if request.method == "POST":
        form = forms.GeneratePayslipForm(request.POST)
        if form.is_valid():
            employees = form.cleaned_data["employee_id"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            for employee in employees:
                contract = payroll.models.models.Contract.objects.filter(
                    employee_id=employee, contract_status="active"
                ).first()
                if start_date < contract.contract_start_date:
                    start_date = contract.contract_start_date
                payslip = payroll_calculation(employee, start_date, end_date)
                payslip_data.append(payslip)
                json_data.append(payslip["json_data"])

            return render(
                request,
                "payroll/payslip/generate_payslip_list.html",
                {
                    "payslip_data": payslip_data,
                    "json_data": json_data,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.add_payslip")
def create_payslip(request):
    """
    Create a payslip for an employee.

    This method is used to create a payslip for an employee based on the provided form data.

    Args:
        request: The HTTP request object.

    Returns:
        A rendered HTML template for the payslip creation form.
    """
    form = forms.PayslipForm()
    if request.method == "POST":
        form = forms.PayslipForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data["employee_id"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            payslip = payroll.models.models.Payslip.objects.filter(
                employee_id=employee, start_date=start_date, end_date=end_date
            ).first()

            if form.is_valid():
                employee = form.cleaned_data["employee_id"]
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                contract = payroll.models.models.Contract.objects.filter(
                    employee_id=employee, contract_status="active"
                ).first()
                if start_date < contract.contract_start_date:
                    start_date = contract.contract_start_date
                payslip_data = payroll_calculation(employee, start_date, end_date)
                payslip_data["payslip"] = payslip
                return render(
                    request,
                    "payroll/payslip/individual_payslip.html",
                    payslip_data,
                )
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.add_attendance")
def validate_start_date(request):
    """
    This method to validate the contract start date and the pay period start date
    """
    print("hitting.....")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    employee_id = request.GET.getlist("employee_id")
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d").date()

    error_message = ""
    response = {"valid": True, "message": error_message}
    for emp_id in employee_id:
        contract = payroll.models.models.Contract.objects.filter(
            employee_id__id=emp_id, contract_status="active"
        ).first()
        if start_datetime < contract.contract_start_date:
            error_message = f"<ul class='errorlist'><li>The {contract.employee_id}'s \
                contract start date is smaller than pay period start date</li></ul>"
            response["message"] = error_message
            response["valid"] = False
    if start_datetime > end_datetime:
        error_message = "<ul class='errorlist'><li>The end date must be greater than \
                or equal to the start date.</li></ul>"
        response["message"] = error_message
        response["valid"] = False
    print(end_datetime)
    print(datetime.today())
    if end_datetime > datetime.today().date():
        error_message = (
            '<ul class="errorlist"><li>The end date cannot be in the future.</li></ul>'
        )
        response["message"] = error_message
        response["valid"] = False
    return JsonResponse(response)


@login_required
@permission_required("payroll.view_payslip")
def view_individual_payslip(request, employee_id, start_date, end_date):
    """
    This method is used to render the template for viewing a payslip.
    """

    payslip_data = payroll_calculation(employee_id, start_date, end_date)
    return render(
        request,
        "payroll/payslip/individual_payslip.html",
        payslip_data,
    )


@login_required
def view_payslip(request):
    """
    This method is used to render the template for viewing a payslip.
    """
    if request.user.has_perm("payroll.view_payslip"):
        payslips = payroll.models.models.Payslip.objects.all()
    else:
        payslips = payroll.models.models.Payslip.objects.filter(
            employee_id__employee_user_id=request.user
        )
    filter_form = PayslipFilter(request.GET)
    individual_form = forms.PayslipForm()
    bulk_form = forms.GeneratePayslipForm()
    payslips = paginator_qry(payslips, request.GET.get("page"))

    return render(
        request,
        "payroll/payslip/view_payslips.html",
        {
            "payslips": payslips,
            "f": filter_form,
            "individual_form": individual_form,
            "bulk_form": bulk_form,
        },
    )


@login_required
def filter_payslip(request):
    """
    Filter and retrieve a list of payslips based on the provided query parameters.
    """
    query_string = request.environ["QUERY_STRING"]
    if request.user.has_perm("payroll.view_payslip"):
        payslips = PayslipFilter(request.GET).qs
    else:
        payslips = payroll.models.models.Payslip.objects.filter(
            employee_id__employee_user_id=request.user
        )
    template = "payroll/payslip/list_payslips.html"
    payslips = paginator_qry(payslips, request.GET.get("page"))
    return render(request, template, {"payslips": payslips, "pd": query_string})


@login_required
@permission_required("payroll.add_allowance")
def hx_create_allowance(request):
    """
    This method is used to render htmx allowance form
    """
    form = forms.AllowanceForm()
    return render(request, "payroll/htmx/form.html", {"form": form})
