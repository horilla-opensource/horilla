"""
Accessibility page to specify the permissions
"""

from django.contrib.auth.context_processors import PermWrapper

from base.context_processors import resignation_request_enabled
from employee.models import Employee
from offboarding.templatetags.offboarding_filter import (
    is_any_stage_manager,
    is_offboarding_manager,
)


def resignation_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for resignation tab employee individual and employee profile
    """
    employee = Employee.objects.get(id=instance.pk)
    enabled_resignation_request = resignation_request_enabled(request)
    value = enabled_resignation_request.get("enabled_resignation_request")
    if (request.user == employee.employee_user_id) and value:
        return True
    return False


def edit_stage_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for stage edit
    """
    perm = request.user.has_perm(
        "offboarding.change_offboardingstage"
    ) or is_offboarding_manager(request.user.employee_get)
    return perm


def add_employee_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
):
    """
    accessibility to add employee to stages
    """
    perms = (
        request.user.has_perm("offboarding.change_offboarding")
        or request.user.has_perm("offboarding.change_offboardingemployee")
        or is_any_stage_manager(request.user.employee_get)
    )
    return perms


def delete_stage_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
):
    """
    accessibility to delete stage
    """
    perm = request.user.has_perm("offboarding.delete_offboarding")
    return perm


def archive_employee_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
):
    stage_type = instance.stage_id.type
    if stage_type == "archived" and add_employee_accessibility(request):
        return True

    return False


def edit_employee_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
):
    stage_type = instance.stage_id.type
    if stage_type != "archived" and add_employee_accessibility(request):
        return True

    return False


def managing_records_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
):
    if (
        instance.employee_id
        and instance.employee_id.get_archive_condition()
        and add_employee_accessibility(request)
    ):
        return True
    return False
