import datetime
import sys
from datetime import timedelta

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.utils import timezone

from base.backends import logger


def auto_punch_out():
    from attendance.methods.utils import Request
    from attendance.models import Attendance, AttendanceActivity
    from attendance.views.clock_in_out import clock_out
    from base.models import EmployeeShiftSchedule

    automatic_check_out_shifts = EmployeeShiftSchedule.objects.filter(
        is_auto_punch_out_enabled=True
    )

    for shift_schedule in automatic_check_out_shifts:
        activities = AttendanceActivity.objects.filter(
            shift_day=shift_schedule.day,
            clock_out_date=None,
            clock_out=None,
        ).order_by("-created_at")

        for activity in activities:
            attendance = Attendance.objects.filter(
                employee_id=activity.employee_id,
                attendance_clock_out=None,
                attendance_clock_out_date=None,
                shift_id=shift_schedule.shift_id,
                attendance_day=shift_schedule.day,
                attendance_date=activity.attendance_date,
            ).first()

            if attendance:
                date = activity.attendance_date
                if (
                    shift_schedule.is_night_shift
                    and shift_schedule.start_time
                    and shift_schedule.end_time
                    and shift_schedule.start_time > shift_schedule.end_time
                ):
                    date += timedelta(days=1)

                combined_datetime = timezone.make_aware(
                    datetime.datetime.combine(date, shift_schedule.auto_punch_out_time)
                )

                if combined_datetime < timezone.now():
                    try:
                        clock_out(
                            Request(
                                user=attendance.employee_id.employee_user_id,
                                date=date,
                                time=shift_schedule.auto_punch_out_time,
                                datetime=combined_datetime,
                            )
                        )
                    except Exception as e:
                        logger.error(f"auto_punch_out error: {e}")


def create_work_record():
    from attendance.models import WorkRecords
    from employee.models import Employee

    date = datetime.date.today()
    work_records = WorkRecords.objects.filter(date=date).values_list(
        "employee_id", flat=True
    )
    employees = Employee.objects.exclude(id__in=work_records)
    records_to_create = []

    for employee in employees:
        try:
            shift_schedule = employee.get_shift_schedule()
            if shift_schedule is None:
                continue

            shift = employee.get_shift()
            record = WorkRecords(
                employee_id=employee,
                date=date,
                work_record_type="DFT",
                shift_id=shift,
                message="",
            )
            records_to_create.append(record)
        except Exception as e:
            logger.error(f"Error preparing work record for {employee}: {e}")

    if records_to_create:
        try:
            WorkRecords.objects.bulk_create(records_to_create, ignore_conflicts=True)
        except Exception as e:
            logger.error(f"Failed to bulk create work records: {e}")


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler(timezone=pytz.timezone(settings.TIME_ZONE))

    scheduler.add_job(
        create_work_record, "interval", minutes=30, misfire_grace_time=3600 * 3
    )
    scheduler.add_job(
        create_work_record,
        "cron",
        hour=0,
        minute=30,
        misfire_grace_time=3600 * 9,
        id="create_daily_work_record",
        replace_existing=True,
    )
    scheduler.add_job(
        auto_punch_out,
        "interval",
        minutes=5,
        misfire_grace_time=600,
        id="auto_punch_out",
        replace_existing=True,
    )

    scheduler.start()
