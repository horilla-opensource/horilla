"""
Accessiblility for pms
"""

from django.contrib.auth.context_processors import PermWrapper

from base.methods import check_manager
from employee.models import Employee


def performance_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    permission for performance tab
    """
    employee = Employee.objects.get(id=instance.pk)
    check_manages = check_manager(request.user.employee_get, instance)
    return (
        request.user == employee.employee_user_id
        or check_manages
        or request.user.has_perm("pms.view_feedback")
    )


def create_objective_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    To check the user has permission to add objectives
    """
    return request.user.has_perm("pms.add_objective")
