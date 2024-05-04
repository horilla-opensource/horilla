from django import template
from django.template.defaultfilters import register

register = template.Library()


@register.filter(name="cancel_request")
def cancel_request(user, request):
    employee = user.employee_get
    employee_manages = employee.reporting_manager.all()
    return bool(
        request.employee_id == employee
        or user.has_perm("perms.base.cancel_worktyperequest")
        or user.has_perm("perms.base.cancel_shiftrequest")
        or employee_manages.exists()
    )


@register.filter(name="update_request")
def update_request(user, request):
    employee = user.employee_get
    return bool(
        not request.canceled
        and not request.approved
        and (
            employee == request.employee_id
            or user.has_perm("perms.base.change_worktyperequest")
            or user.has_perm("perms.base.change_shiftrequest")
        )
    )
