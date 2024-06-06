import datetime
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone


def auto_check_out():

    from attendance.models import AttendanceActivity
    from attendance.views.clock_in_out import clock_out_attendance_and_activity
    from base.models import EmployeeShiftSchedule
    from employee.models import Employee

    try:
        today = datetime.now()
        shift_schedules = EmployeeShiftSchedule.objects.all()
        employees = Employee.objects.all()
        for employee in employees:
            work_info = getattr(employee, "employee_work_info", None)
            shift_id = getattr(work_info, "shift_id", None)
            shift_schedule = shift_schedules.filter(
                day__day=today.strftime("%A").lower(), shift_id=shift_id
            ).first()
            attendance_activity = AttendanceActivity.objects.filter(
                employee_id=employee, clock_out__isnull=True
            ).first()
            if (
                shift_schedule
                and attendance_activity
                and attendance_activity.attendance_date < today.date()
            ):
                if (
                    not attendance_activity.clock_out
                    and shift_schedule.start_time <= today.time()
                ):
                    clock_out_attendance_and_activity(
                        employee=employee,
                        date_today=today.date(),
                        now=today.time().strftime("%H:%M"),
                        out_datetime=today,
                    )

    except:
        pass


scheduler = BackgroundScheduler()
scheduler.add_job(auto_check_out, "interval", seconds=30)
scheduler.start()
