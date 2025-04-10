from django.http import JsonResponse
from django.shortcuts import render

from asset.models import Asset
from horilla_views.cbv_methods import login_required


@login_required
def asset_report(request):

    if not request.user.is_superuser:
        return render(request, "404.html")
    return render(request, "report/asset_report.html")


@login_required
def asset_pivot(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    data = Asset.objects.values(
        "asset_name",
        "asset_purchase_date",
        "asset_tracking_id",
        "asset_purchase_cost",
        "asset_status",
        "asset_category_id__asset_category_name",
        "asset_lot_number_id__lot_number",
        "expiry_date",
        "assetassignment__assigned_by_employee_id__employee_work_info__department_id__department",
        "assetassignment__assigned_by_employee_id__employee_work_info__job_position_id__job_position",
        "assetassignment__assigned_by_employee_id__employee_work_info__job_role_id__job_role",
        "assetassignment__assigned_by_employee_id__email",
        "assetassignment__assigned_by_employee_id__phone",
        "assetassignment__assigned_by_employee_id__gender",
        "assetassignment__assigned_by_employee_id__employee_first_name",
        "assetassignment__assigned_by_employee_id__employee_last_name",
        "assetassignment__assigned_date",
        "assetassignment__return_date",
        "assetassignment__return_status",
    )
    data_list = [
        {
            "Asset Name": item["asset_name"],
            "Asset User": (
                f"{item['assetassignment__assigned_by_employee_id__employee_first_name']} {item['assetassignment__assigned_by_employee_id__employee_last_name']}"
                if item["assetassignment__assigned_by_employee_id__employee_first_name"]
                or item["assetassignment__assigned_by_employee_id__employee_last_name"]
                else "-"
            ),
            "Email": (
                item["assetassignment__assigned_by_employee_id__email"]
                if item["assetassignment__assigned_by_employee_id__email"]
                else "-"
            ),
            "Phone": (
                item["assetassignment__assigned_by_employee_id__phone"]
                if item["assetassignment__assigned_by_employee_id__phone"]
                else "-"
            ),
            "Gender": (
                item["assetassignment__assigned_by_employee_id__gender"]
                if item["assetassignment__assigned_by_employee_id__gender"]
                else "-"
            ),
            "Department": (
                item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__department_id__department"
                ]
                if item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__department_id__department"
                ]
                else "-"
            ),
            "Job Position": (
                item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__job_position_id__job_position"
                ]
                if item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__job_position_id__job_position"
                ]
                else "-"
            ),
            "Job Role": (
                item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__job_role_id__job_role"
                ]
                if item[
                    "assetassignment__assigned_by_employee_id__employee_work_info__job_role_id__job_role"
                ]
                else "-"
            ),
            "Asset Purchce Date": item["asset_purchase_date"],
            "Asset Cost": item["asset_purchase_cost"],
            "Status": item["asset_status"],
            "Assigned Date": (
                item["assetassignment__assigned_date"]
                if item["assetassignment__assigned_date"]
                else "-"
            ),
            "Return Date": (
                item["assetassignment__return_date"]
                if item["assetassignment__return_date"]
                else "-"
            ),
            "Return Condition": (
                item["assetassignment__return_status"]
                if item["assetassignment__return_status"]
                else "-"
            ),
            "Category": item["asset_category_id__asset_category_name"],
            "Lot Number": item["asset_lot_number_id__lot_number"],
            "Tracking ID": item["asset_tracking_id"],
            "Expiry Date": item["expiry_date"] if item["expiry_date"] else "-",
        }
        for item in data
    ]
    return JsonResponse(data_list, safe=False)
