from django.http import JsonResponse
from django.shortcuts import render

from horilla_views.cbv_methods import login_required
from leave.models import AvailableLeave, LeaveRequest


@login_required
def leave_report(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    return render(request, "report/leave_report.html")

@login_required
def leave_pivot(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    model_type = request.GET.get("model", "leave_request")  # Default to LeaveRequest

    if model_type == "leave_request":
        data = LeaveRequest.objects.values(
            "employee_id__employee_first_name","employee_id__employee_last_name","leave_type_id__name",
            "start_date","start_date_breakdown","end_date","end_date_breakdown","requested_days","status",
            'employee_id__gender','employee_id__email','employee_id__phone','employee_id__employee_work_info__department_id__department', 
            'employee_id__employee_work_info__job_role_id__job_role','employee_id__employee_work_info__job_position_id__job_position', 
            'employee_id__employee_work_info__employee_type_id__employee_type','employee_id__employee_work_info__experience',
            'employee_id__employee_work_info__work_type_id__work_type','employee_id__employee_work_info__shift_id__employee_shift',

        )
        BREAKDOWN_MAP = {
            "full_day": "Full Day",
            "first_half": "First Half",
            "second_half": "Second Half",
        }

        choice_gender = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
        }
        data_list = [
            {
                "Name": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
                "Gender": choice_gender.get(item["employee_id__gender"]),
                "Email": item["employee_id__email"],
                "Phone": item["employee_id__phone"],
                "Department": item["employee_id__employee_work_info__department_id__department"],
                "Job Position": item["employee_id__employee_work_info__job_position_id__job_position"],
                "Job Role": item["employee_id__employee_work_info__job_role_id__job_role"],
                "Work Type": item["employee_id__employee_work_info__work_type_id__work_type"],
                "Shift": item["employee_id__employee_work_info__shift_id__employee_shift"],
                "Experience": round(float(item["employee_id__employee_work_info__experience"] or 0), 2),
                "Leave Type": item["leave_type_id__name"],
                "Start Date": item["start_date"],
                "Start Date Breakdown": BREAKDOWN_MAP.get(item["start_date_breakdown"], "-"),
                "End Date Breakdown": BREAKDOWN_MAP.get(item["end_date_breakdown"], "-"),
                "End Date": item["end_date"],
                "Requested Days": item["requested_days"],
                "Status": item["status"],
            }
            for item in data
        ]
    elif model_type == "available_leave":
        data = AvailableLeave.objects.values(
            "employee_id__employee_first_name","employee_id__employee_last_name","leave_type_id__name",
            "available_days","carryforward_days","total_leave_days","assigned_date","reset_date","expired_date",
            'employee_id__gender','employee_id__email','employee_id__phone','employee_id__employee_work_info__department_id__department', 
            'employee_id__employee_work_info__job_role_id__job_role','employee_id__employee_work_info__job_position_id__job_position', 
            'employee_id__employee_work_info__employee_type_id__employee_type','employee_id__employee_work_info__experience',
            'employee_id__employee_work_info__work_type_id__work_type','employee_id__employee_work_info__shift_id__employee_shift',
        )
        choice_gender = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
        }
        data_list = [
            {
                "Name": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
                "Gender": choice_gender.get(item["employee_id__gender"]),
                "Email": item["employee_id__email"],
                "Phone": item["employee_id__phone"],
                "Department": item["employee_id__employee_work_info__department_id__department"],
                "Job Position": item["employee_id__employee_work_info__job_position_id__job_position"],
                "Job Role": item["employee_id__employee_work_info__job_role_id__job_role"],
                "Work Type": item["employee_id__employee_work_info__work_type_id__work_type"],
                "Shift": item["employee_id__employee_work_info__shift_id__employee_shift"],
                "Experience": item["employee_id__employee_work_info__experience"],
                "Leave Type": item["leave_type_id__name"],
                "Available Days": item["available_days"],
                "Carryforward Days": item["carryforward_days"],
                "Total Leave Days": item["total_leave_days"],
                "Assigned Date": item["assigned_date"],
                "Reset Date": item.get("reset_date", "-") or "-",
                "Expired Date": item.get("expired_date", "-") or "-"
            }
            for item in data
        ]
    else:
        data_list = []  # Empty if invalid model selected

    return JsonResponse(data_list, safe=False)
