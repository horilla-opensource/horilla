import datetime
import sys

from apscheduler.schedulers.background import BackgroundScheduler

today = datetime.datetime.today()


def create_work_record(date=today):
    from attendance.models import WorkRecords
    from employee.models import Employee

    work_records = WorkRecords.objects.all()
    employees = Employee.objects.all()
    if len(work_records.filter(date=date)) == len(employees):
        return
    else:
        for employee in employees:
            try:
                shift = employee.employee_work_info.shift_id

                WorkRecords.objects.get_or_create(
                    employee_id=employee,
                    date=date,
                    defaults={
                        "work_record_type": "DFT",
                        "shift_id": shift,
                        "message": "",
                    },
                )
            except:
                pass


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        create_work_record, "interval", hours=3, misfire_grace_time=3600 * 3
    )
    scheduler.add_job(
        create_work_record, "cron", hour=0, minute=30, misfire_grace_time=3600 * 9
    )

    scheduler.start()
