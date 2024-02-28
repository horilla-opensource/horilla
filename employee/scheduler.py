# import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# from employee.models import DisciplinaryAction
# from employee.policies import employee_account_block_unblock


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


# def block_unblock_disciplinary():
#     from employee.models import Employee
#     """
#     This scheduled task to trigger the experience calculator
#     to update the employee work experience
#     """
#     dis_action = DisciplinaryAction.objects.all()
#     for i in dis_action:
#         if i.action.action_type == 'suspension':
#             if datetime.date.today() >= i.start_date or datetime.date.today() >= i.end_date:
#                 for emp in i.employee_id:
#                     employee_account_block_unblock(emp_id=emp.id)



    
#     return

scheduler = BackgroundScheduler()
scheduler.add_job(update_experience, "interval", days=1)
scheduler.start()