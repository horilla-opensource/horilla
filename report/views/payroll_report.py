from django.http import JsonResponse
from django.shortcuts import render

from horilla_views.cbv_methods import login_required
from payroll.models.models import Payslip


@login_required
def payroll_report(request):

    if not request.user.is_superuser:
        return render(request, "404.html")
    return render(request, "report/payroll_report.html")


@login_required
def payroll_pivot(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    model_type = request.GET.get("model", "payslip")

    if model_type == "payslip":
        data = Payslip.objects.values(
            "id",  # Include payslip ID to fetch pay_head_data later
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__gender",
            "employee_id__email",
            "employee_id__phone",
            "start_date",
            "end_date",
            "contract_wage",
            "basic_pay",
            "gross_pay",
            "deduction",
            "net_pay",
            "status",
            "employee_id__employee_work_info__department_id__department",
            "employee_id__employee_work_info__job_role_id__job_role",
            "employee_id__employee_work_info__job_position_id__job_position",
            "employee_id__employee_work_info__work_type_id__work_type",
            "employee_id__employee_work_info__shift_id__employee_shift",
            "employee_id__employee_work_info__employee_type_id__employee_type",
            "employee_id__employee_work_info__experience",
        )

        choice_gender = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
        }

        STATUS = {
            "draft": "Draft",
            "review_ongoing": "Review Ongoing",
            "confirmed": "Confirmed",
            "paid": "Paid",
        }

        # Fetch pay_head_data separately and map by payslip ID
        payslip_ids = [item["id"] for item in data]
        pay_head_data_dict = dict(
            Payslip.objects.filter(id__in=payslip_ids).values_list(
                "id", "pay_head_data"
            )
        )

        data_list = []
        for item in data:
            # Load pay_head_data for current payslip
            pay_head_data = pay_head_data_dict.get(item["id"], {})

            # Extract allowances and deductions
            allowances = pay_head_data.get("allowances", [])
            deductions = pay_head_data.get("pretax_deductions", []) + pay_head_data.get(
                "post_tax_deductions", []
            )

            # Prepare allowance and deduction lists with properly rounded amounts
            allowance_titles = (
                ", ".join([allowance["title"] for allowance in allowances]) or "-"
            )
            allowance_amounts = (
                ", ".join(
                    [
                        str(round(float(allowance["amount"] or 0), 2))
                        for allowance in allowances
                    ]
                )
                or "-"
            )

            deduction_titles = (
                ", ".join([deduction["title"] for deduction in deductions]) or "-"
            )
            deduction_amounts = (
                ", ".join(
                    [
                        str(round(float(deduction["amount"] or 0), 2))
                        for deduction in deductions
                    ]
                )
                or "-"
            )

            # Calculate total allowance amount
            total_allowance_amount = sum(
                [round(float(allowance["amount"] or 0), 2) for allowance in allowances]
            )

            # Calculate total deduction amount
            total_deduction_amount = sum(
                [round(float(deduction["amount"] or 0), 2) for deduction in deductions]
            )

            # Main data structure
            data_list.append(
                {
                    "Employee": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
                    "Gender": choice_gender.get(item["employee_id__gender"]),
                    "Email": item["employee_id__email"],
                    "Phone": item["employee_id__phone"],
                    "Department": (
                        item[
                            "employee_id__employee_work_info__department_id__department"
                        ]
                        if item[
                            "employee_id__employee_work_info__department_id__department"
                        ]
                        else "-"
                    ),
                    "Job Position": (
                        item[
                            "employee_id__employee_work_info__job_position_id__job_position"
                        ]
                        if item[
                            "employee_id__employee_work_info__job_position_id__job_position"
                        ]
                        else "-"
                    ),
                    "Job Role": (
                        item["employee_id__employee_work_info__job_role_id__job_role"]
                        if item[
                            "employee_id__employee_work_info__job_role_id__job_role"
                        ]
                        else "-"
                    ),
                    "Work Type": (
                        item["employee_id__employee_work_info__work_type_id__work_type"]
                        if item[
                            "employee_id__employee_work_info__work_type_id__work_type"
                        ]
                        else "-"
                    ),
                    "Shift": (
                        item[
                            "employee_id__employee_work_info__shift_id__employee_shift"
                        ]
                        if item[
                            "employee_id__employee_work_info__shift_id__employee_shift"
                        ]
                        else "-"
                    ),
                    "Employee Type": (
                        item[
                            "employee_id__employee_work_info__employee_type_id__employee_type"
                        ]
                        if item[
                            "employee_id__employee_work_info__employee_type_id__employee_type"
                        ]
                        else "-"
                    ),
                    "Payslip Start Date": item["start_date"],
                    "Payslip End Date": item["end_date"],
                    "Contract Wage": round(float(item["contract_wage"] or 0), 2),
                    "Basic Salary": round(float(item["basic_pay"] or 0), 2),
                    "Gross Pay": round(float(item["gross_pay"] or 0), 2),
                    "Net Pay": round(float(item["net_pay"] or 0), 2),
                    "Allowance Title": allowance_titles,
                    "Allowance Amount": allowance_amounts,
                    "Total Allowance Amount": round(total_allowance_amount, 2),
                    "Deduction Title": deduction_titles,
                    "Deduction Amount": deduction_amounts,
                    "Total Deduction Amount": round(total_deduction_amount, 2),
                    "Status": STATUS.get(item["status"]),
                    "Experience": round(
                        float(item["employee_id__employee_work_info__experience"] or 0),
                        2,
                    ),
                }
            )

    elif model_type == "allowance":
        data = Payslip.objects.values(
            "id",  # Include payslip ID to fetch pay_head_data later
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__gender",
            "employee_id__email",
            "employee_id__phone",
            "start_date",
            "end_date",
            "status",
            "employee_id__employee_work_info__department_id__department",
            "employee_id__employee_work_info__job_role_id__job_role",
            "employee_id__employee_work_info__job_position_id__job_position",
            "employee_id__employee_work_info__work_type_id__work_type",
            "employee_id__employee_work_info__shift_id__employee_shift",
        )

        choice_gender = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
        }

        STATUS = {
            "draft": "Draft",
            "review_ongoing": "Review Ongoing",
            "confirmed": "Confirmed",
            "paid": "Paid",
        }

        # Fetch pay_head_data separately and map by payslip ID
        payslip_ids = [item["id"] for item in data]
        pay_head_data_dict = dict(
            Payslip.objects.filter(id__in=payslip_ids).values_list(
                "id", "pay_head_data"
            )
        )

        data_list = []
        for item in data:
            # Load pay_head_data for current payslip
            pay_head_data = pay_head_data_dict.get(item["id"], {})

            # Combine Allowances and Deductions in a single section
            all_pay_data = []

            # Add Allowances to combined data
            for allowance in pay_head_data.get("allowances", []):
                all_pay_data.append(
                    {
                        "Pay Type": "Allowance",
                        "Title": allowance["title"],
                        "Amount": allowance["amount"],
                    }
                )

            # Add Deductions to combined data
            for deduction in pay_head_data.get(
                "pretax_deductions", []
            ) + pay_head_data.get("post_tax_deductions", []):
                all_pay_data.append(
                    {
                        "Pay Type": "Deduction",
                        "Title": deduction["title"],
                        "Amount": deduction["amount"],
                    }
                )

            # Add combined data to main data list
            for pay_item in all_pay_data:
                data_list.append(
                    {
                        "Employee": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
                        "Gender": choice_gender.get(item["employee_id__gender"]),
                        "Email": item["employee_id__email"],
                        "Phone": item["employee_id__phone"],
                        "Department": (
                            item[
                                "employee_id__employee_work_info__department_id__department"
                            ]
                            if item[
                                "employee_id__employee_work_info__department_id__department"
                            ]
                            else "-"
                        ),
                        "Job Position": (
                            item[
                                "employee_id__employee_work_info__job_position_id__job_position"
                            ]
                            if item[
                                "employee_id__employee_work_info__job_position_id__job_position"
                            ]
                            else "-"
                        ),
                        "Job Role": (
                            item[
                                "employee_id__employee_work_info__job_role_id__job_role"
                            ]
                            if item[
                                "employee_id__employee_work_info__job_role_id__job_role"
                            ]
                            else "-"
                        ),
                        "Work Type": (
                            item[
                                "employee_id__employee_work_info__work_type_id__work_type"
                            ]
                            if item[
                                "employee_id__employee_work_info__work_type_id__work_type"
                            ]
                            else "-"
                        ),
                        "Shift": (
                            item[
                                "employee_id__employee_work_info__shift_id__employee_shift"
                            ]
                            if item[
                                "employee_id__employee_work_info__shift_id__employee_shift"
                            ]
                            else "-"
                        ),
                        "Payslip Start Date": item["start_date"],
                        "Payslip End Date": item["end_date"],
                        "Allowance & Deduction": pay_item["Pay Type"],
                        "Allowance & Deduction Title": pay_item["Title"],
                        "Allowance & Deduction Amount": pay_item["Amount"],
                        "Status": STATUS.get(item["status"]),
                    }
                )
    else:
        data_list = []

    return JsonResponse(data_list, safe=False)
