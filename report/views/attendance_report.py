from datetime import datetime, time

from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import render

if apps.is_installed("attendance"):

    from attendance.filters import AttendanceFilters
    from attendance.models import Attendance
    from base.models import Company
    from horilla.decorators import login_required, permission_required

    def convert_time_to_decimal_w(time_str):
        try:
            if isinstance(time_str, str):
                hours, minutes = map(int, time_str.split(":"))
            elif isinstance(time_str, time):
                hours, minutes = time_str.hour, time_str.minute
            else:
                return "00.00"

            # Format as HH.MM
            formatted_time = f"{hours:02}.{minutes:02}"
            return formatted_time
        except (ValueError, TypeError):
            return "00.00"

    def convert_time_to_decimal(time_str):
        """Format time as HH.MM for aggregation."""
        try:
            if isinstance(time_str, str):  # When time comes as string
                t = datetime.strptime(time_str, "%H:%M:%S").time()
            elif isinstance(time_str, time):
                t = time_str
            else:
                return "00.00"

            # Format as HH.MM
            formatted_time = f"{t.hour:02}.{t.minute:02}"
            return formatted_time
        except Exception:
            return "00.00"

    @login_required
    @permission_required(perm="attendance.view_attendance")
    def attendance_report(request):
        company = "all"
        selected_company = request.session.get("selected_company")
        if selected_company != "all":
            company = Company.objects.filter(id=selected_company).first()

        return render(
            request,
            "report/attendance_report.html",
            {"company": company, "f": AttendanceFilters()},
        )

    @login_required
    @permission_required(perm="attendance.view_attendance")
    def attendance_pivot(request):
        qs = Attendance.objects.all()
        filter_obj = AttendanceFilters(request.GET, queryset=qs)
        qs = filter_obj.qs

        data = list(
            qs.values(
                "employee_id__employee_first_name",
                "employee_id__employee_last_name",
                "attendance_date",
                "attendance_clock_in",
                "attendance_clock_out",
                "attendance_worked_hour",
                "minimum_hour",
                "attendance_overtime",
                "at_work_second",
                "work_type_id__work_type",
                "shift_id__employee_shift",
                "attendance_day__day",
                "employee_id__gender",
                "employee_id__email",
                "employee_id__phone",
                "employee_id__employee_work_info__department_id__department",
                "employee_id__employee_work_info__job_role_id__job_role",
                "employee_id__employee_work_info__job_position_id__job_position",
                "employee_id__employee_work_info__employee_type_id__employee_type",
                "employee_id__employee_work_info__experience",
                "batch_attendance_id__title",
                "employee_id__employee_work_info__company_id__company",
            )
        )
        DAY = {
            "monday": "Monday",
            "tuesday": "Tuesday",
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday",
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
                "Department": (
                    item["employee_id__employee_work_info__department_id__department"]
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
                    if item["employee_id__employee_work_info__job_role_id__job_role"]
                    else "-"
                ),
                "Work Type": (
                    item["work_type_id__work_type"]
                    if item["work_type_id__work_type"]
                    else "-"
                ),
                "Shift": (
                    item["shift_id__employee_shift"]
                    if item["shift_id__employee_shift"]
                    else "-"
                ),
                "Experience": item["employee_id__employee_work_info__experience"],
                "Attendance Date": item["attendance_date"],
                "Attendance Day": DAY.get(item["attendance_day__day"]),
                "Clock-in": format_time(item["attendance_clock_in"]),
                "Clock-out": format_time(item["attendance_clock_out"]),
                "At Work": format_seconds_to_time(item["at_work_second"]),
                "Worked Hour": item["attendance_worked_hour"],
                "Minimum Hour": item["minimum_hour"],
                "Overtime": item["attendance_overtime"],
                "Batch": (
                    item["batch_attendance_id__title"]
                    if item["batch_attendance_id__title"]
                    else "-"
                ),
                "Company": item["employee_id__employee_work_info__company_id__company"],
                # For correct total
                "Clock-in Decimal": convert_time_to_decimal(
                    item["attendance_clock_in"]
                ),
                "Clock-out Decimal": convert_time_to_decimal(
                    item["attendance_clock_out"]
                ),
                "At Work Decimal": convert_time_to_decimal_w(
                    format_seconds_to_time(item["at_work_second"])
                ),
                "Worked Hour Decimal": convert_time_to_decimal_w(
                    item["attendance_worked_hour"]
                ),
                "Minimum Hour Decimal": convert_time_to_decimal_w(item["minimum_hour"]),
                "Overtime Decimal": convert_time_to_decimal_w(
                    item["attendance_overtime"]
                ),
            }
            for item in data
        ]
        return JsonResponse(data_list, safe=False)

    # Helper function to format time
    def format_time(time_value):
        if isinstance(time_value, str):  # In case time is string
            time_value = datetime.strptime(time_value, "%H:%M:%S").time()
        return time_value.strftime("%H:%M") if time_value else ""

    def format_seconds_to_time(seconds):
        """Convert seconds to HH:MM format."""
        try:
            seconds = int(seconds)
            hours, remainder = divmod(seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours:02}:{minutes:02}"
        except (ValueError, TypeError):
            return "00:00"
