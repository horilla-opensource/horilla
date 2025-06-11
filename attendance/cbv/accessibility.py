"""
Accessiblility
"""

from django.contrib.auth.context_processors import PermWrapper

from base.methods import check_manager
from employee.models import Employee


def attendance_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    permission for attendance tab
    """

    check_manages = check_manager(request.user.employee_get, instance)
    employee = Employee.objects.get(id=instance.pk)
    if (
        check_manages
        or request.user.has_perm("attendance.view_attendance")
        or request.user == employee.employee_user_id
    ):
        return True
    return False


def penalty_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    permission for penalty tab
    """

    employee = Employee.objects.get(id=instance.pk)
    check_manages = check_manager(request.user.employee_get, instance)
    if (
        request.user.has_perm("attendance.view_penaltyaccount")
        or request.user == employee.employee_user_id
        or check_manages
    ):
        return True
    return False


def create_attendance_request_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    employee = Employee.objects.get(id=instance.pk)
    if request.user == employee.employee_user_id:
        return True
    return False
