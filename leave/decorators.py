"""
decorator functions for leave
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from horilla.methods import handle_no_permission
from leave.models import LeaveGeneralSetting

from .models import LeaveAllocationRequest

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
            request.user.has_perm("leave.change_leaveallocationrequest")
            or request.user.employee_get
            == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
            or request.user.employee_get == leave_allocation_request.employee_id
        ):
            return function(request, *args, req_id=req_id, **kwargs)

        return handle_no_permission(request)

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
        try:
            leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
            if (
                request.user.has_perm("leave.delete_leaveallocationrequest")
                or request.user.employee_get
                == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
                or request.user.employee_get == leave_allocation_request.employee_id
            ):
                return function(request, *args, req_id=req_id, **kwargs)

            return handle_no_permission(request)

        except (LeaveAllocationRequest.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Leave allocation request not found"))
            return redirect("/leave/leave-allocation-request-view/")

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
        try:
            leave_allocation_request = LeaveAllocationRequest.objects.get(id=req_id)
            if (
                request.user.has_perm("leave.delete_leaveallocationrequest")
                or request.user.employee_get
                == leave_allocation_request.employee_id.employee_work_info.reporting_manager_id
            ):
                return function(request, *args, req_id=req_id, **kwargs)

            return handle_no_permission(request)

        except (LeaveAllocationRequest.DoesNotExist, OverflowError, ValueError):
            messages.error(request, _("Leave allocation request not found"))
            return redirect("/leave/leave-allocation-request-view/")

    return check_permission


@decorator_with_arguments
def is_compensatory_leave_enabled(func=None, *args, **kwargs):
    def function(request, *args, **kwargs):
        """
        This function check whether the compensatory leave feature is enabled
        """
        if (
            LeaveGeneralSetting.objects.exists()
            and LeaveGeneralSetting.objects.all().first().compensatory_leave
        ):
            return func(request, *args, **kwargs)

        return handle_no_permission(
            request, message=_("Sorry,Compensatory leave is not enabled.")
        )

    return function
