from apscheduler.schedulers.background import BackgroundScheduler


def update_experience():
    from employee.models import EmployeeWorkInformation
    """
    This scheduled task to trigger the experience calculator
    to update the employee work experience
    """
    queryset = EmployeeWorkInformation.objects.filter(
        employee_id__is_active=True
    )
    for instance in queryset:
        instance.experience_calculator()
    return


scheduler = BackgroundScheduler()
scheduler.add_job(update_experience, "interval", days=1)
scheduler.start()