from django.template.defaultfilters import register
from django import template
from recruitment.models import Stage,Recruitment
from django.contrib.auth.models import User
import uuid

# from django.forms.boundfield

register = template.Library()


@register.filter(name='is_stagemanager')
def is_stagemanager(user):
    """
    This method is used to check the employee is stage or recruitment manager
    """
    try:
        employee = user.employee_get
        return employee.stage_set.all().exists() or employee.recruitment_set.exists()
    except:
        return False

@register.filter(name='is_recruitmentmanager')
def is_recruitmentmangers(user):
    """
    This method is used to check the employee is recruitment manager
    """
    try:
        employee = user.employee_get
        return employee.recruitment_set.exists()
    except Exception:
        return False


@register.filter(name='stage_manages')
def stage_manages(user,recruitment):
    """
    This method is used to check the employee is manager in any stage in a recruitment
    """
    try:
        return recruitment.stage_set.filter(stage_managers=user.employee_get).exists() or recruitment.recruitment_managers.filter(id=user.employee_get.id).exists()
    except Exception as e:
        return False


@register.filter(name='recruitment_manages')
def recruitment_manages(user,recruitment):
    """
    This method is used to check the employee in recruitment managers
    """
    try:
        employee =user.employee_get
        return recruitment.recruitment_managers.filter(id=employee.id).exists()
    except Exception:
        return False


@register.filter(name='employee')
def employee(uid):
    if uid is not None:
        return User.objects.get(id=uid).employee_get

@register.filter(name='media_path')
def media_path(form_tag):    
    return form_tag.subwidgets[0].__dict__['data']['value']


@register.filter(name='generate_id')
def generate_id(element,label=''):
    element.field.widget.attrs.update({'id':label + str(uuid.uuid1())})
    return element

# @register.filter