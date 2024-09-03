import calendar
from datetime import datetime, timedelta

from django.apps import apps
from django.db.models import Q

from employee.models import Employee
from horilla.methods import get_horilla_model_class


def calculate_requested_days(
    start_date, end_date, start_date_breakdown, end_date_breakdown
):
    if start_date == end_date:
        if start_date_breakdown == "full_day" and end_date_breakdown == "full_day":
            requested_days = 1
        else:
            requested_days = 0.5
    else:
        start_days = 0
        end_days = 0
        if start_date_breakdown != "full_day":
            start_days = 0.5

        if end_date_breakdown != "full_day":
            end_days = 0.5

        if start_date_breakdown == "full_day" and end_date_breakdown == "full_day":
            requested_days = (end_date - start_date).days + start_days + end_days + 1
        else:
            if start_date_breakdown == "full_day" or end_date_breakdown == "full_day":
                requested_days = (end_date - start_date).days + start_days + end_days
            else:
                requested_days = (
                    (end_date - start_date).days + start_days + end_days - 1
                )

    return requested_days


def leave_requested_dates(start_date, end_date):
    """
    :return: this functions returns a list of dates from start date to end date.
    """
    request_start_date = start_date
    request_end_date = end_date
    if request_end_date is None:
        request_end_date = start_date
    requested_days = request_end_date - request_start_date
    requested_dates = []
    for i in range(requested_days.days + 1):
        date = request_start_date + timedelta(i)
        requested_dates.append(date)
    return requested_dates


def holiday_dates_list(holidays):
    """
    :return: this functions returns a list of all holiday dates.
    """
    holiday_dates = []
    for holiday in holidays:
        holiday_start_date = holiday.start_date
        holiday_end_date = holiday.end_date
        if holiday_end_date is None:
            holiday_end_date = holiday_start_date
        holiday_days = holiday_end_date - holiday_start_date
        for i in range(holiday_days.days + 1):
            date = holiday_start_date + timedelta(i)
            holiday_dates.append(date)
    return holiday_dates


def company_leave_dates_list(company_leaves, start_date):
    """
    :return: This function returns a list of all company leave dates"""
    company_leave_dates = []
    for company_leave in company_leaves:
        year = start_date.year
        based_on_week = company_leave.based_on_week
        based_on_week_day = company_leave.based_on_week_day
        for month in range(1, 13):
            if based_on_week != None:
                # Set Sunday as the first day of the week
                calendar.setfirstweekday(6)
                month_calendar = calendar.monthcalendar(year, month)
                try:
                    weeks = month_calendar[int(based_on_week)]
                    weekdays_in_weeks = [day for day in weeks if day != 0]
                    for day in weekdays_in_weeks:
                        date = datetime.strptime(
                            f"{year}-{month:02}-{day:02}", "%Y-%m-%d"
                        ).date()
                        if (
                            date.weekday() == int(based_on_week_day)
                            and date not in company_leave_dates
                        ):
                            company_leave_dates.append(date)
                except IndexError:
                    pass
            else:
                # Set Monday as the first day of the week
                calendar.setfirstweekday(0)
                month_calendar = calendar.monthcalendar(year, month)
                for week in month_calendar:
                    if week[int(based_on_week_day)] != 0:
                        date = datetime.strptime(
                            f"{year}-{month:02}-{week[int(based_on_week_day)]:02}",
                            "%Y-%m-%d",
                        ).date()
                        if date not in company_leave_dates:
                            company_leave_dates.append(date)
    return company_leave_dates


def get_leave_day_attendance(employee, comp_id=None):
    """
    This function returns a queryset of attendance on leave dates
    """
    Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
    from leave.models import CompensatoryLeaveRequest

    attendances_to_exclude = Attendance.objects.none()  # Empty queryset to start with
    # Check for compensatory leave requests that are not rejected and not the current one
    if (
        CompensatoryLeaveRequest.objects.filter(employee_id=employee)
        .exclude(Q(id=comp_id) | Q(status="rejected"))
        .exists()
    ):
        comp_leave_reqs = CompensatoryLeaveRequest.objects.filter(
            employee_id=employee
        ).exclude(Q(id=comp_id) | Q(status="rejected"))
        for req in comp_leave_reqs:
            attendances_to_exclude |= req.attendance_id.all()
    # Filter holiday attendance excluding the attendances in attendances_to_exclude
    holiday_attendance = Attendance.objects.filter(
        is_holiday=True, employee_id=employee, attendance_validated=True
    ).exclude(id__in=attendances_to_exclude.values_list("id", flat=True))
    return holiday_attendance


def attendance_days(employee, attendances):
    """
    This function returns count of workrecord from the attendance
    """
    attendance_days = 0
    if apps.is_installed("attendance"):
        from attendance.models import WorkRecords

        for attendance in attendances:
            if WorkRecords.objects.filter(
                employee_id=employee, date=attendance.attendance_date
            ).exists():
                work_record_type = (
                    WorkRecords.objects.filter(
                        employee_id=employee, date=attendance.attendance_date
                    )
                    .first()
                    .work_record_type
                )
                if work_record_type == "HDP":
                    attendance_days += 0.5
                elif work_record_type == "FDP":
                    attendance_days += 1
    return attendance_days


def filter_conditional_leave_request(request):
    """
    Filters and returns LeaveRequest objects that have been conditionally approved by the previous sequence of approvals.
    """
    approval_manager = Employee.objects.filter(employee_user_id=request.user).first()
    leave_request_ids = []
    if apps.is_installed("leave"):
        from leave.models import LeaveRequest, LeaveRequestConditionApproval

        multiple_approval_requests = LeaveRequestConditionApproval.objects.filter(
            manager_id=approval_manager
        )
    else:
        multiple_approval_requests = None
    for instance in multiple_approval_requests:
        if instance.sequence > 1:
            pre_sequence = instance.sequence - 1
            leave_request_id = instance.leave_request_id
            instance = LeaveRequestConditionApproval.objects.filter(
                leave_request_id=leave_request_id, sequence=pre_sequence
            ).first()
            if instance and instance.is_approved:
                leave_request_ids.append(instance.leave_request_id.id)
        else:
            leave_request_ids.append(instance.leave_request_id.id)
    return LeaveRequest.objects.filter(pk__in=leave_request_ids)
