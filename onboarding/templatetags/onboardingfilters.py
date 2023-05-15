from django.template.defaultfilters import register
from django import template


# from django.forms.boundfield

register = template.Library()
    
  
@register.filter(name='is_taskmanager')
def is_taskmanager(user):
    """   
    """
    try:
        employee = user.employee_get
        return employee.onboardingtask_set.all().exists() or employee.onboardingstage_set.all().exists() or employee.recruitment_set.exists()
    except Exception:
        return False

 
@register.filter(name='task_manages')
def task_manages(user, recruitment):
    """
    
    """
    try:
        employee = user.employee_get
        return recruitment.onboarding_task.filter(employee_id = employee).exists() or recruitment.onboardingstage_set.filter(employee_id = employee).exists() or recruitment.recruitment_managers.filter(id=user.employee_get.id).exists()
    except Exception:
        return False
 

@register.filter(name='stage_manages')
def stage_manages(user, stage):
    """
    """
    try:
        employee = user.employee_get
        return stage.employee_id.filter(id=employee.id).exists() or stage.recruitment_id.filter(recruitment_managers=employee).exists()
    except Exception:
        return False



@register.filter(name='task_manager')
def task_manager(user, task):
    """
    
    """
    try:
        employee = user.employee_get
        return task.onboarding_task_id.employee_id.filter(id = employee.id).exists() or task.candidate_id.onboarding_stage.onboarding_stage_id.employee_id.filter(id=employee.id).exists() or  task.onboarding_task_id.recruitment_id.first().recruitment_managers.filter(id=user.employee_get.id).exists()
    except Exception:
        return False