"""
Accessibility page to specify the permissions
"""

from django.contrib.auth.context_processors import PermWrapper

from base.context_processors import resignation_request_enabled
from employee.models import Employee


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
