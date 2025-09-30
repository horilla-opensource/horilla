from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import render

if apps.is_installed("leave"):

    from base.models import Company
    from horilla.decorators import login_required, permission_required
    from leave.filters import AssignedLeaveFilter, LeaveRequestFilter
    from leave.models import AvailableLeave, LeaveRequest

    @login_required
    @permission_required(perm="leave.view_leaverequest")
    def leave_report(request):
        company = "all"
        selected_company = request.session.get("selected_company")
        if selected_company != "all":
            company = Company.objects.filter(id=selected_company).first()

        leave_request_filter = LeaveRequestFilter()

        return render(
            request,
            "report/leave_report.html",
            {
                "company": company,
                "form": leave_request_filter.form,
                "f": AssignedLeaveFilter(),
            },
        )

    @login_required
    @permission_required(perm="leave.view_leaverequest")
    def leave_pivot(request):
        model_type = request.GET.get(
            "model", "leave_request"
        )  # Default to LeaveRequest

        if model_type == "leave_request":

            qs = LeaveRequest.objects.all()
            leave_filter = LeaveRequestFilter(request.GET, queryset=qs)
            qs = leave_filter.qs

            data = list(
                qs.values(
                    "employee_id__employee_first_name",
                    "employee_id__employee_last_name",
                    "leave_type_id__name",
                    "start_date",
                    "start_date_breakdown",
                    "end_date",
                    "end_date_breakdown",
                    "requested_days",
                    "status",
                    "employee_id__gender",
                    "employee_id__email",
                    "employee_id__phone",
                    "employee_id__employee_work_info__department_id__department",
                    "employee_id__employee_work_info__job_role_id__job_role",
                    "employee_id__employee_work_info__job_position_id__job_position",
                    "employee_id__employee_work_info__employee_type_id__employee_type",
                    "employee_id__employee_work_info__experience",
                    "employee_id__employee_work_info__work_type_id__work_type",
                    "employee_id__employee_work_info__shift_id__employee_shift",
                    "employee_id__employee_work_info__company_id__company",
                )
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

            LEAVE_STATUS = {
                "requested": "Requested",
                "approved": "Approved",
                "cancelled": "Cancelled",
                "rejected": "Rejected",
            }
            data_list = [
                {
                    "Name": f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}",
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
                    "Experience": item["employee_id__employee_work_info__experience"],
                    "Leave Type": item["leave_type_id__name"],
                    "Start Date": item["start_date"],
                    "Start Date Breakdown": BREAKDOWN_MAP.get(
                        item["start_date_breakdown"], "-"
                    ),
                    "End Date Breakdown": BREAKDOWN_MAP.get(
                        item["end_date_breakdown"], "-"
                    ),
                    "End Date": item["end_date"],
                    "Requested Days": item["requested_days"],
                    "Status": LEAVE_STATUS.get(item["status"]),
                    "Company": item[
                        "employee_id__employee_work_info__company_id__company"
                    ],
                }
                for item in data
            ]
        elif model_type == "available_leave":

            qs = AvailableLeave.objects.all()
            available_leave_filter = AssignedLeaveFilter(request.GET, queryset=qs)
            qs = available_leave_filter.qs

            data = list(
                qs.values(
                    "employee_id__employee_first_name",
                    "employee_id__employee_last_name",
                    "leave_type_id__name",
                    "available_days",
                    "carryforward_days",
                    "total_leave_days",
                    "assigned_date",
                    "reset_date",
                    "expired_date",
                    "employee_id__gender",
                    "employee_id__email",
                    "employee_id__phone",
                    "employee_id__employee_work_info__department_id__department",
                    "employee_id__employee_work_info__job_role_id__job_role",
                    "employee_id__employee_work_info__job_position_id__job_position",
                    "employee_id__employee_work_info__employee_type_id__employee_type",
                    "employee_id__employee_work_info__experience",
                    "employee_id__employee_work_info__work_type_id__work_type",
                    "employee_id__employee_work_info__shift_id__employee_shift",
                    "employee_id__employee_work_info__company_id__company",
                )
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
                    "Experience": item["employee_id__employee_work_info__experience"],
                    "Leave Type": item["leave_type_id__name"],
                    "Available Days": item["available_days"],
                    "Carryforward Days": item["carryforward_days"],
                    "Total Leave Days": item["total_leave_days"],
                    "Assigned Date": item["assigned_date"],
                    "Reset Date": item.get("reset_date", "-") or "-",
                    "Expired Date": item.get("expired_date", "-") or "-",
                    "Company": item[
                        "employee_id__employee_work_info__company_id__company"
                    ],
                }
                for item in data
            ]
        else:
            data_list = []  # Empty if invalid model selected

        return JsonResponse(data_list, safe=False)
