"""
recruitmentfilters.py

This module is used to write custom template filters.

"""
import uuid
from django.template.defaultfilters import register
from django import template
from django.contrib.auth.models import User

# from django.forms.boundfield

register = template.Library()


@register.filter(name="is_stagemanager")
def is_stagemanager(user):
    """
    This method is used to check the employee is stage or recruitment manager
    """
    try:
        employee_obj = user.employee_get
        return (
            employee_obj.stage_set.all().exists()
            or employee_obj.recruitment_set.exists()
        )
    except Exception:
        return False


@register.filter(name="is_recruitmentmanager")
def is_recruitmentmangers(user):
    """
    This method is used to check the employee is recruitment manager
    """
    try:
        employee_obj = user.employee_get
        return employee_obj.recruitment_set.exists()
    except Exception:
        return False


@register.filter(name="stage_manages")
def stage_manages(user, recruitment):
    """
    This method is used to check the employee is manager in any stage in a recruitment
    """
    try:
        return (
            recruitment.stage_set.filter(stage_managers=user.employee_get).exists()
            or recruitment.recruitment_managers.filter(id=user.employee_get.id).exists()
        )
    except Exception as _:
        return False


@register.filter(name="recruitment_manages")
def recruitment_manages(user, recruitment):
    """
    This method is used to check the employee in recruitment managers
    """
    try:
        employee_obj = user.employee_get
        return recruitment.recruitment_managers.filter(id=employee_obj.id).exists()
    except Exception:
        return False


@register.filter(name="employee")
def employee(uid):
    """
    This method is used to return user object with the arg id.

    Args:
        uid (int): user object id

    Returns:
        user object
    """
    return User.objects.get(id=uid).employee_get if uid is not None else None


@register.filter(name="media_path")
def media_path(form_tag):
    """
    This method will returns the path of media
    """
    return form_tag.subwidgets[0].__dict__["data"]["value"]


@register.filter(name="generate_id")
def generate_id(element, label=""):
    """
    This method is used to generate element id attr
    """
    element.field.widget.attrs.update({"id": label + str(uuid.uuid1())})
    return element


# @register.filter
