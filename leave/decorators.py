"""
decorator functions for leave
"""
from django.contrib import messages
from django.http import HttpResponseRedirect
from.models import LeaveAllocationRequest
from django.utils.translation import gettext_lazy as _

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)

@decorator_with_arguments
def leave_allocation_change_permission(function=None, *args, **kwargs):
    def check_permission(
        request,
        req_id=None,
        *args,
        **kwargs,
    ):
        """
        This method is used to check the employee can change a leave allocation request or not
        """
        leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
        if (
            request.user.has_perm('leave.change_leaveallocationrequest')
            or request.user.employee_get == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
            or request.user.employee_get == leave_allocation_request.employee_id
        ):
            return function(request,*args,req_id=req_id,**kwargs)
        messages.info(
            request,
            _("You dont have permission.")
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return check_permission


@decorator_with_arguments
def leave_allocation_delete_permission(function=None, *args, **kwargs):
    def check_permission(
        request,
        req_id=None,
        *args,
        **kwargs,
    ):
        """
        This method is used to check the employee can delete a leave allocation request or not
        """
        leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
        if (
            request.user.has_perm('leave.delete_leaveallocationrequest')
            or request.user.employee_get == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
            or request.user.employee_get == leave_allocation_request.employee_id
        ):
            return function(request,*args,req_id=req_id,**kwargs)
        messages.info(
            request,
            _("You dont have permission.")
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return check_permission


@decorator_with_arguments
def leave_allocation_reject_permission(function=None, *args, **kwargs):
    def check_permission(
        request,
        req_id=None,
        *args,
        **kwargs,
    ):
        """
        This method is used to check the employee can reject a leave allocation request or not
        """
        leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
        if (
            request.user.has_perm('leave.delete_leaveallocationrequest')
            or request.user.employee_get == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
        ):
            return function(request,*args,req_id=req_id,**kwargs)
        messages.info(
            request,
            _("You dont have permission.")
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return check_permission
