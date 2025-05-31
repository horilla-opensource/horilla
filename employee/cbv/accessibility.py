"""
Accessiblility
"""

from django.contrib.auth.context_processors import PermWrapper

from base.methods import check_manager
from employee.models import Employee
from horilla_audit.models import AccountBlockUnblock


def edit_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    To access edit
    """
    # employee = Employee.objects.get(id=instance.pk)
    if (
        (request.user.has_perm("employee.change_employee"))
        or check_manager(request.user.employee_get, instance)
        or request.user == instance.employee_user_id
    ):
        return True
    return False


def password_reset_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    To password  reset
    """
    # employee = Employee.objects.get(id=instance.pk)
    if (
        (request.user.has_perm("employee.add_employee"))
        or check_manager(request.user.employee_get, instance)
        or request.user == instance.employee_user_id
    ):
        return True
    return False


def block_account_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    To block  account
    """
    enabled_block_unblock = (
        AccountBlockUnblock.objects.exists()
        and AccountBlockUnblock.objects.first().is_enabled
    )
    if (
        enabled_block_unblock
        and request.user.has_perm("employee.change_employee")
        and instance.employee_user_id.is_active
    ):
        return True
    return False


def un_block_account_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    To block  account
    """
    enabled_block_unblock = (
        AccountBlockUnblock.objects.exists()
        and AccountBlockUnblock.objects.first().is_enabled
    )
    if (
        enabled_block_unblock
        and request.user.has_perm("employee.change_employee")
        and not instance.employee_user_id.is_active
    ):
        return True
    return False


def action_accessible(request, instance, user_perms):
    """
    To access archive and delete functionalities

    """

    if request.user.has_perm("employee.change_employee"):
        return True


def permission_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for permissions tab in employee profile and individual view
    """
    if request.user.has_perm("auth.view_permissions") or request.user.has_perm(
        "auth.view_group"
    ):
        return True
    return False


def note_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for note tab
    """
    if request.user.has_perm("employee.view_employeenote") or check_manager(
        request.user.employee_get, instance
    ):
        return True
    return False


def document_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for document tab
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("horilla_documents.view_document")
        or request.user == employee.employee_user_id
    ):
        return True
    return False


def workshift_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    permission for work type and shift tab in employee profile
    """
    employee = Employee.objects.get(id=instance.pk)
    check_manages = check_manager(request.user.employee_get, instance)
    if (
        request.user == employee.employee_user_id
        or check_manages
        or request.user.has_perm("attendance.view_worktyperequest")
        or request.user.has_perm("attendance.view_shiftrequest")
    ):
        return True
    return False


def mail_log_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    permission for mail log tab
    """

    if request.user.has_perm("employee.view_employee"):
        return True
    return False


def history_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for history tab
    """
    if request.user.has_perm(
        "employee.view_historicalemployeeworkinformation"
    ) or check_manager(request.user.employee_get, instance):
        return True
    return False
