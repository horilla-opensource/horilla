from django.http import JsonResponse
from django.shortcuts import render

from employee.models import EmployeeWorkInformation
from horilla_views.cbv_methods import login_required


@login_required
def employee_report(request):

    if not request.user.is_superuser:
        return render(request, "404.html")
    return render(request, "report/employee_report.html")


@login_required
def employee_pivot(request):

    if not request.user.is_superuser:
        return render(request, "404.html")

    data = EmployeeWorkInformation.objects.values(
        "employee_id__employee_first_name",
        "employee_id__employee_last_name",
        "employee_id__gender",
        "employee_id__email",
        "employee_id__phone",
        "department_id__department",
        "job_position_id__job_position",
        "job_role_id__job_role",
        "work_type_id__work_type",
        "shift_id__employee_shift",
        "employee_type_id__employee_type",
        "reporting_manager_id__employee_first_name",
        "reporting_manager_id__employee_last_name",
        "company_id__company",
        "date_joining",
        "experience",
    )
    choice_gender = {
        "male": "Male",
        "female": "Female",
        "other": "Other",
    }

    # Transform data to match format
    data_list = [
        {
            "Name": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
            "Gender": choice_gender.get(item["employee_id__gender"]),
            "Email": item["employee_id__email"],
            "Phone": item["employee_id__phone"],
            "Department": item["department_id__department"],
            "Job Position": item["job_position_id__job_position"],
            "Job Role": item["job_role_id__job_role"],
            "Work Type": item["work_type_id__work_type"],
            "Shift": item["shift_id__employee_shift"],
            "Employee Type": item["employee_type_id__employee_type"],
            "Reporting Manager": f"{item['reporting_manager_id__employee_first_name']} {item['reporting_manager_id__employee_last_name']}",
            "Date of Joining": item["date_joining"],
            "Experience": round(float(item["experience"] or 0), 2),
            "Company": item["company_id__company"],
        }
        for item in data
    ]
    return JsonResponse(data_list, safe=False)
