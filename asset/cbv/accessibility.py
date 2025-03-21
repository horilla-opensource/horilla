from django.contrib.auth.context_processors import PermWrapper

from base.methods import check_manager
from employee.models import Employee


def asset_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for asset tab
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("asset.view_asset")
        or check_manager(request.user.employee_get, instance)
        or request.user == employee.employee_user_id
    ):
        return True
    return False


def create_asset_request_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    if request.user.has_perm("asset.add_assetrequest"):
        return True
    return False
