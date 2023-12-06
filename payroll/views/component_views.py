"""
component_views.py

This module is used to write methods to the component_urls patterns respectively
"""
import json
import operator
from datetime import date, datetime
from urllib.parse import parse_qs
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import pandas as pd
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from base.methods import get_key_instances
from base.methods import closest_numbers
import payroll.models.models
from payroll.models.models import Allowance, Deduction, Payslip
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
from payroll.methods.methods import (
    compute_salary_on_period,
    paginator_qry,
    save_payslip,
)
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

    loss_of_pay_amount = (
        float(loss_of_pay) if not contract.deduct_leave_from_basic_pay else 0
    )

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
        net_pay,
        post_tax_deductions["net_pay_deduction"],
        **kwargs,
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
            messages.success(request, _("Allowance created."))
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
    allowance_ids = json.dumps([instance.id for instance in allowances.object_list])
    return render(
        request,
        "payroll/allowance/view_allowance.html",
        {
            "allowances": allowances,
            "f": allowance_filter,
            "allowance_ids": allowance_ids,
        },
    )


@login_required
@permission_required("payroll.view_allowance")
def view_single_allowance(request, allowance_id):
    """
    This method is used render template to view the selected allowance instances
    """
    allowance = payroll.models.models.Allowance.objects.get(id=allowance_id)
    allowance_ids_json = request.GET.get("instances_ids")
    context = {
        "allowance": allowance,
    }
    if allowance_ids_json:
        allowance_ids = json.loads(allowance_ids_json)
        previous_id, next_id = closest_numbers(allowance_ids, allowance_id)
        context["next"] = next_id
        context["previous"] = previous_id
        context["allowance_ids"] = allowance_ids
    return render(
        request,
        "payroll/allowance/view_single_allowance.html",
        context,
    )


@login_required
@permission_required("payroll.view_allowance")
def filter_allowance(request):
    """
    Filter and retrieve a list of allowances based on the provided query parameters.
    """
    query_string = request.GET.urlencode()
    allowances = AllowanceFilter(request.GET).qs
    list_view = "payroll/allowance/list_allowance.html"
    card_view = "payroll/allowance/card_allowance.html"
    template = card_view
    if request.GET.get("view") == "list":
        template = list_view
    allowances = paginator_qry(allowances, request.GET.get("page"))
    allowance_ids = json.dumps([instance.id for instance in allowances.object_list])
    data_dict = parse_qs(query_string)
    get_key_instances(Allowance, data_dict)
    return render(
        request,
        template,
        {
            "allowances": allowances,
            "pd": query_string,
            "filter_dict": data_dict,
            "allowance_ids": allowance_ids,
        },
    )


@login_required
@permission_required("payroll.change_allowance")
def update_allowance(request, allowance_id, **kwargs):
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
            messages.success(request, _("Allowance updated."))
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
        messages.success(request, _("Allowance deleted successfully"))
    except ObjectDoesNotExist(Exception):
        messages.error(request, _("Allowance not found"))
    except ValidationError as validation_error:
        messages.error(
            request, _("Validation error occurred while deleting the allowance")
        )
        messages.error(request, str(validation_error))
    except Exception as exception:
        messages.error(request, _("An error occurred while deleting the allowance"))
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
            messages.success(request, _("Deduction created."))
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
    deduction_ids = json.dumps([instance.id for instance in deductions.object_list])
    return render(
        request,
        "payroll/deduction/view_deduction.html",
        {
            "deductions": deductions,
            "f": deduction_filter,
            "deduction_ids": deduction_ids,
        },
    )


@login_required
@permission_required("payroll.view_allowance")
def view_single_deduction(request, deduction_id):
    """
    This method is used render template to view all the deduction instances
    """

    deduction = payroll.models.models.Deduction.objects.get(id=deduction_id)
    context = {"deduction": deduction}
    deduction_ids_json = request.GET.get("instances_ids")
    if deduction_ids_json:
        deduction_ids = json.loads(deduction_ids_json)
        previous_id, next_id = closest_numbers(deduction_ids, deduction_id)
        context["next"] = next_id
        context["previous"] = previous_id
        context["deduction_ids"] = deduction_ids
    return render(
        request,
        "payroll/deduction/view_single_deduction.html",
        context,
    )


@login_required
@permission_required("payroll.view_allowance")
def filter_deduction(request):
    """
    This method is used search the deduction
    """
    query_string = request.GET.urlencode()
    deductions = DeductionFilter(request.GET).qs
    list_view = "payroll/deduction/list_deduction.html"
    card_view = "payroll/deduction/card_deduction.html"
    template = card_view
    if request.GET.get("view") == "list":
        template = list_view
    deductions = paginator_qry(deductions, request.GET.get("page"))
    deduction_ids = json.dumps([instance.id for instance in deductions.object_list])
    data_dict = parse_qs(query_string)
    get_key_instances(Deduction, data_dict)
    return render(
        request,
        template,
        {
            "deductions": deductions,
            "pd": query_string,
            "filter_dict": data_dict,
            "deduction_ids": deduction_ids,
        },
    )


@login_required
@permission_required("payroll.change_deduction")
def update_deduction(request, deduction_id, **kwargs):
    """
    This method is used to update the deduction instance
    """
    instance = payroll.models.models.Deduction.objects.get(id=deduction_id)
    form = forms.DeductionForm(instance=instance)
    if request.method == "POST":
        form = forms.DeductionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Deduction updated."))
            return redirect(view_deduction)
    return render(request, "payroll/common/form.html", {"form": form})


@login_required
@permission_required("payroll.delete_deduction")
def delete_deduction(request, deduction_id):
    """
    This method is used to delete the deduction instance
    Args:
        id : deduction instance id
    """
    payroll.models.models.Deduction.objects.get(id=deduction_id).delete()
    messages.success(request, _("Deduction deleted successfully"))
    return redirect(view_deduction)


@login_required
@permission_required("payroll.add_payslip")
def generate_payslip(request):
    """
    Generate payslips for selected employees within a specified date range.

    Requires the user to be logged in and have the 'payroll.add_payslip' permission.

    """
    payslips = []
    json_data = []
    form = forms.GeneratePayslipForm()
    if request.method == "POST":
        form = forms.GeneratePayslipForm(request.POST)
        if form.is_valid():
            instances = []
            employees = form.cleaned_data["employee_id"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            group_name = form.cleaned_data["group_name"]
            for employee in employees:
                contract = payroll.models.models.Contract.objects.filter(
                    employee_id=employee, contract_status="active"
                ).first()
                if start_date < contract.contract_start_date:
                    start_date = contract.contract_start_date
                payslip = payroll_calculation(employee, start_date, end_date)
                payslips.append(payslip)
                json_data.append(payslip["json_data"])

                payslip["payslip"] = payslip
                data = {}
                data["employee"] = employee
                data["group_name"] = group_name
                data["start_date"] = payslip["start_date"]
                data["end_date"] = payslip["end_date"]
                data["status"] = "draft"
                data["contract_wage"] = payslip["contract_wage"]
                data["basic_pay"] = payslip["basic_pay"]
                data["gross_pay"] = payslip["gross_pay"]
                data["deduction"] = payslip["total_deductions"]
                data["net_pay"] = payslip["net_pay"]
                data["pay_data"] = json.loads(payslip["json_data"])
                instance = save_payslip(**data)
                instances.append(instance)
            messages.success(request, f"{employees.count()} payslip saved as draft")
            return redirect(
                f"/payroll/view-payslip?group_by=group_name&active_group={group_name}"
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
                data = {}
                data["employee"] = employee
                data["start_date"] = payslip_data["start_date"]
                data["end_date"] = payslip_data["end_date"]
                data["status"] = (
                    "draft"
                    if request.GET.get("status") is None
                    else request.GET["status"]
                )
                data["contract_wage"] = payslip_data["contract_wage"]
                data["basic_pay"] = payslip_data["basic_pay"]
                data["gross_pay"] = payslip_data["gross_pay"]
                data["deduction"] = payslip_data["total_deductions"]
                data["net_pay"] = payslip_data["net_pay"]
                data["pay_data"] = json.loads(payslip_data["json_data"])
                payslip_data["instance"] = save_payslip(**data)
                form = forms.PayslipForm()
                messages.success(request, _("Payslip Saved"))
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
    end_datetime = None
    start_datetime = None
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    employee_id = request.GET.getlist("employee_id")
    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d").date()
    error_message = ""
    response = {"valid": True, "message": error_message}
    for emp_id in employee_id:
        contract = payroll.models.models.Contract.objects.filter(
            employee_id__id=emp_id, contract_status="active"
        ).first()

        if start_datetime is not None and start_datetime < contract.contract_start_date:
            error_message = f"<ul class='errorlist'><li>The {contract.employee_id}'s \
                contract start date is smaller than pay period start date</li></ul>"
            response["message"] = error_message
            response["valid"] = False

    if (
        start_datetime is not None
        and end_datetime is not None
        and start_datetime > end_datetime
    ):
        error_message = "<ul class='errorlist'><li>The end date must be greater than \
                or equal to the start date.</li></ul>"
        response["message"] = error_message
        response["valid"] = False

    if end_datetime is not None:
        if end_datetime > datetime.today().date():
            error_message = '<ul class="errorlist"><li>The end date cannot be in the future.</li></ul>'
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
    export_column = forms.PayslipExportColumnForm()
    filter_form = PayslipFilter(request.GET, payslips)
    payslips = filter_form.qs
    individual_form = forms.PayslipForm()
    bulk_form = forms.GeneratePayslipForm()
    field = request.GET.get("group_by")
    if field in Payslip.__dict__.keys():
        payslips = payslips.filter(group_name__isnull=False).order_by(field)
    payslips = paginator_qry(payslips, request.GET.get("page"))
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(Payslip, data_dict)
    return render(
        request,
        "payroll/payslip/view_payslips.html",
        {
            "payslips": payslips,
            "f": filter_form,
            "export_column": export_column,
            "export_filter": PayslipFilter(request.GET),
            "individual_form": individual_form,
            "bulk_form": bulk_form,
            "filter_dict": data_dict,
        },
    )


@login_required
def filter_payslip(request):
    """
    Filter and retrieve a list of payslips based on the provided query parameters.
    """
    query_string = request.GET.urlencode()
    if request.user.has_perm("payroll.view_payslip"):
        payslips = PayslipFilter(request.GET).qs
    else:
        emp_request = request.GET.copy()
        employee = Employee.objects.filter(employee_user_id = request.user.id).first()
        employee_id = employee.id
        emp_request["employee_id"] = str(employee_id)
        print(emp_request)
        payslips = PayslipFilter(emp_request).qs
        # payslips = PayslipFilter(request.GET).qs
        # payslips = payroll.models.models.Payslip.objects.filter(
        #     employee_id__employee_user_id=request.user
        # )
    template = "payroll/payslip/payslip_table.html"
    field = request.GET.get("view")
    if field == "card":
        template = "payroll/payslip/group_payslips.html"
        payslips = payslips.filter(group_name__isnull=False).order_by("-group_name")
    payslips = paginator_qry(payslips, request.GET.get("page"))
    data_dict = []
    if not request.GET.get("dashboard"):
        data_dict = parse_qs(query_string)
        get_key_instances(Payslip, data_dict)
    if "status" in data_dict:
        status_list = data_dict["status"]
        if len(status_list) > 1:
            data_dict["status"] = [status_list[-1]]

    return render(
        request,
        template,
        {
            "payslips": payslips,
            "pd": query_string,
            "filter_dict": data_dict,
        },
    )


@login_required
def payslip_export(request):
    """
    This view exports payslip data based on selected fields and filters,
    and generates an Excel file for download.
    """
    choices_mapping = {
        "draft": _("Draft"),
        "review_ongoing": _("Review Ongoing"),
        "confirmed": _("Confirmed"),
        "paid": _("Paid"),
    }
    selected_columns = []
    payslips_data = {}
    payslips = PayslipFilter(request.GET).qs
    today_date = date.today().strftime("%Y-%m-%d")
    file_name = f"Payslip_excel_{today_date}.xlsx"
    selected_fields = request.GET.getlist("selected_fields")
    form = forms.PayslipExportColumnForm()

    if not selected_fields:
        selected_fields = form.fields["selected_fields"].initial
        ids = request.GET.get("ids")
        id_list = json.loads(ids)
        payslips = Payslip.objects.filter(id__in=id_list)

    for field in forms.excel_columns:
        value = field[0]
        key = field[1]
        if value in selected_fields:
            selected_columns.append((value, key))

    for column_value, column_name in selected_columns:
        nested_attributes = column_value.split("__")
        payslips_data[column_name] = []
        for payslip in payslips:
            value = payslip
            for attr in nested_attributes:
                value = getattr(value, attr, None)
                if value is None:
                    break
            data = str(value) if value is not None else ""
            if column_name == "Status":
                data = choices_mapping.get(value, "")
            else:
                data = str(value) if value is not None else ""
            payslips_data[column_name].append(data)

    data_frame = pd.DataFrame(data=payslips_data)
    data_frame = data_frame.style.applymap(
        lambda x: "text-align: center", subset=pd.IndexSlice[:, :]
    )
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    data_frame.to_excel(response, index=False)
    writer = pd.ExcelWriter(response, engine="xlsxwriter")
    data_frame.to_excel(writer, index=False, sheet_name="Sheet1")
    worksheet = writer.sheets["Sheet1"]
    worksheet.set_column("A:Z", 20)
    writer.close()
    return response


@login_required
@permission_required("payroll.add_allowance")
def hx_create_allowance(request):
    """
    This method is used to render htmx allowance form
    """
    form = forms.AllowanceForm()
    return render(request, "payroll/htmx/form.html", {"form": form})
