"""
This module is used to write custom template filters.
"""

from django.template.defaultfilters import register

from project.models import Project


@register.filter(name="task_crud_perm")
def task_crud_perm(user, task):
    """
    This method is used to check the requested user is task manager or project manager or has permission
    """
    try:
        employee = user.employee_get
        is_task_manager = employee in task.task_managers.all()
        is_project_manager = employee in task.project.managers.all()
        return is_task_manager or is_project_manager

    except Exception as _:
        return False


@register.filter(name="time_sheet_crud_perm")
def time_sheet_crud_perm(user, timesheet):
    """
    This method is used to check the requested user is task manager or project manager or has permission
    """
    try:
        employee = user.employee_get
        is_task_manager = employee in timesheet.task_id.task_managers.all()
        is_project_manager = employee in timesheet.project_id.managers.all()
        is_own_timesheet = timesheet.employee_id == employee

        return is_task_manager or is_project_manager or is_own_timesheet

    except Exception as _:
        return False


@register.filter(name="is_project_manager_or_member")
def is_project_manager_or_member(user, project):
    """
    This method will return true, if the user is manger or member of the project
    """
    employee = user.employee_get

    return (
        Project.objects.filter(id=project.id, managers=employee).exists()
        or Project.objects.filter(id=project.id, members=employee).exists()
    )


@register.filter(name="is_project_manager")
def is_project_manager(user, project):
    """
    This method will return true, if the user is manager of the project
    """
    if user.is_superuser:
        return True
    employee = user.employee_get
    return Project.objects.filter(id=project.id, managers=employee).exists()


@register.filter(name="is_task_manager")
def is_task_manager(user, task):
    """
    This method will return True if the user is a manager of the task.
    """
    try:
        employee = user.employee_get
        return employee in task.task_managers.all()
    except AttributeError:
        # Handle cases where user or task might not have the expected structure
        return False
