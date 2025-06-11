from django.contrib.auth.context_processors import PermWrapper

from base.methods import check_manager
from employee.models import Employee


def payroll_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for payroll tab
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("payroll.view_payslip")
        or request.user == employee.employee_user_id
    ):
        return True
    return False


def bonus_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for bonus tab
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("employee.view_bonuspoint")
        or check_manager(request.user.employee_get, instance)
        or request.user == employee.employee_user_id
    ):
        return True
    return False


def allowance_and_deduction_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for allowance and deduction tab
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("payroll.view_payslip")
        or request.user == employee.employee_user_id
    ):
        return True
    return False
