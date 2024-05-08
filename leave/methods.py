import calendar
from datetime import datetime, timedelta

from django.db.models import Q


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
    from attendance.filters import AttendanceFilters
    from attendance.models import Attendance
    from leave.models import CompensatoryLeaveRequest, LeaveRequest

    holiday_dates = LeaveRequest.holiday_dates(None)
    company_leave_dates = LeaveRequest.company_leave_dates(None)
    leave_day_attendance = Attendance.objects.none()
    converted_dates = []
    if (
        CompensatoryLeaveRequest.objects.filter(employee_id=employee)
        .exclude(Q(id=comp_id) | Q(status="rejected"))
        .exists()
    ):
        comp_leave_reqs = CompensatoryLeaveRequest.objects.filter(
            employee_id=employee
        ).exclude(Q(id=comp_id) | Q(status="rejected"))
        attendances = Attendance.objects.none()  # Empty queryset to start with
        for req in comp_leave_reqs:
            attendances |= req.attendance_id.all()
        converted_dates = [attendance.attendance_date for attendance in attendances]
    leave_dates = set(company_leave_dates + holiday_dates) - set(converted_dates)
    for leave_day in leave_dates:
        attendance_qs = AttendanceFilters(
            {"employee": employee.id, "attendance_date": leave_day}
        ).qs
        if attendance_qs.exists():
            leave_day_attendance |= attendance_qs

    return leave_day_attendance


def attendance_days(employee, attendances):
    """
    This function returns count of workrecord from the attendance
    """
    from payroll.models.models import WorkRecord

    attendance_days = 0
    for attendance in attendances:
        if WorkRecord.objects.filter(
            employee_id=employee, date=attendance.attendance_date
        ).exists():
            work_record_type = (
                WorkRecord.objects.filter(
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
