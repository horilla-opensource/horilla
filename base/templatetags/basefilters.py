import json

from django import template
from django.apps import apps
from django.core.paginator import Page, Paginator
from django.template.defaultfilters import register

from base.methods import get_pagination
from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation

register = template.Library()


@register.filter(name="cancel_request")
def cancel_request(user, request):
    employee = user.employee_get
    employee_manages = employee.reporting_manager.all()
    return bool(
        request.employee_id == employee
        or user.has_perm("perms.base.cancel_worktyperequest")
        or user.has_perm("perms.base.cancel_shiftrequest")
        or employee_manages.exists()
    )


@register.filter(name="update_request")
def update_request(user, request):
    employee = user.employee_get
    return bool(
        not request.canceled
        and not request.approved
        and (
            employee == request.employee_id
            or user.has_perm("perms.base.change_worktyperequest")
            or user.has_perm("perms.base.change_shiftrequest")
        )
    )


@register.filter(name="is_reportingmanager")
def is_reportingmanager(user):
    """{% load basefilters %}

    This method will return true if the user employee profile is reporting manager to any employee
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    return EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee
    ).exists()


@register.filter(name="is_leave_approval_manager")
def is_leave_approval_manager(user):
    """
    This method will return true if the user is comes in MultipleApprovalCondition model as approving manager
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    manager = (
        MultipleApprovalManagers.objects.filter(employee_id=employee.id).exists()
        if employee
        else False
    )
    return manager


@register.filter(name="check_manager")
def check_manager(user, instance):
    try:
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == user.employee_get
        return (
            user.employee_get
            == instance.employee_id.employee_work_info.reporting_manager_id
        )
    except:
        return False


@register.filter(name="filtersubordinates")
def filtersubordinates(user):
    """
    This method returns true if the user employee has corresponding related reporting manager object in EmployeeWorkInformation model
    args:
        user    : request.user
    """
    employee = user.employee_get
    employee_manages = employee.reporting_manager.all()
    return employee_manages.exists()


@register.filter(name="filter_field")
def filter_field(value):
    if value.endswith("_id"):
        value = value[:-3]
    if value.endswith("_ids"):
        value = value[:-4]
    splitted = value.split("__")

    return splitted[-1].replace("_", " ").capitalize()


@register.filter(name="user_perms")
def user_perms(perms):
    """
    permission names return method
    """
    return json.dumps(list(perms.values_list("codename", flat="True")))


@register.filter(name="abs_value")
def abs_value(value):
    """
    permission names return method
    """
    return abs(value)


@register.filter(name="config_perms")
def config_perms(user):
    app_permissions = {
        "leave": [
            "leave.add_holiday",
            "leave.change_holiday",
            "leave.add_companyleaves",
            "leave.change_companyleaves",
            "leave.view_restrictleave",
        ],
        "base": [
            "base.add_horillamailtemplates",
            "base.view_horillamailtemplates",
        ],
    }

    for app, perms in app_permissions.items():
        if apps.is_installed(app):
            for perm in perms:
                if user.has_perm(perm):
                    return True
    return False


@register.filter(name="startswith")
def startswith(value, arg):
    """Checks if the value starts with the provided argument."""
    return value.startswith(arg)
