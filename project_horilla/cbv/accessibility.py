"""
Accessibility
"""

from django.contrib.auth.context_processors import PermWrapper

from employee.models import Employee
from project.models import Project, Task


def task_crud_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    to access crud operations
    """
    employee = request.user.employee_get
    is_task_manager = employee in instance.task_managers.all()
    is_project_manager = employee in instance.project.managers.all()
    if (
        request.user.has_perm("project.view_task")
        or is_project_manager
        or is_task_manager
    ):
        return True
    else:
        return False


def project_manager_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    to access edit Project
    """
    return (
        request.user.employee_get in instance.managers.all()
        or request.user.is_superuser
    )
