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


def can_view_employee_permissions(request, employee) -> bool:
    """
    Groups & Permissions visible to: the employee, their reporting manager,
    and superadmins.
    """
    if not employee or not request.user.is_authenticated:
        return False
    user = request.user
    if user.is_superuser:
        return True
    if getattr(employee, "employee_user_id", None) == user:
        return True
    try:
        return check_manager(user.employee_get, employee)
    except Exception:
        return False


def can_edit_employee_permissions(request, employee) -> bool:
    """
    Who may change an employee's groups/permissions from the profile:
    superadmin only. Reporting managers and the employee get view access.
    """
    if not employee or not request.user.is_authenticated:
        return False
    return bool(request.user.is_superuser)


def permission_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    Groups & Permissions tab: visible to the employee themselves,
    their reporting manager, and superadmins.
    """
    return can_view_employee_permissions(request, instance)


def note_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for note tab
    """
    if instance.employee_user_id != request.user or request.user.is_superuser:
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
        or request.user.has_perm("base.view_worktyperequest")
        or request.user.has_perm("base.view_shiftrequest")
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


def project_accessibility(
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
        or request.user.has_perm("project.view_project")
    ):
        return True
    return False
