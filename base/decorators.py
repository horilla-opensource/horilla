"""
decorator functions for base
"""

from django.contrib import messages
from django.http import HttpResponseRedirect

from .models import ShiftRequest, WorkTypeRequest

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def shift_request_change_permission(function=None, *args, **kwargs):
    def check_permission(
        request,
        shift_request_id=None,
        *args,
        **kwargs,
    ):
        """
        This method is used to check the employee can change a shift request or not
        """
        shift_request = ShiftRequest.objects.get(id=shift_request_id)
        if (
            request.user.has_perm("base.change_shiftrequest")
            or request.user.employee_get
            == shift_request.employee_id.employee_work_info.reporting_manager_id
            or request.user.employee_get == shift_request.employee_id
        ):
            return function(request, *args, shift_request_id=shift_request_id, **kwargs)
        messages.info(request, "You dont have permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        # return function(request, *args, **kwargs)

    return check_permission


@decorator_with_arguments
def work_type_request_change_permission(function=None, *args, **kwargs):
    def check_permission(
        request,
        work_type_request_id=None,
        *args,
        **kwargs,
    ):
        """
        This method is used to check the employee can change a shift request or not
        """
        work_type_request = WorkTypeRequest.objects.get(id=work_type_request_id)
        if (
            request.user.has_perm("base.change_worktyperequest")
            or request.user.employee_get
            == work_type_request.employee_id.employee_work_info.reporting_manager_id
            or request.user.employee_get == work_type_request.employee_id
        ):
            return function(
                request, *args, work_type_request_id=work_type_request_id, **kwargs
            )
        messages.info(request, "You dont have permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        # return function(request, *args, **kwargs)

    return check_permission
