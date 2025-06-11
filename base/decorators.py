"""
decorator functions for base
"""

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from employee.models import EmployeeWorkInformation
from horilla.horilla_middlewares import _thread_locals

from .models import MultipleApprovalManagers, ShiftRequest, WorkTypeRequest

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


@decorator_with_arguments
def manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager.
    """

    def _function(self, *args, **kwargs):
        leave_perm = [
            "leave.view_leaverequest",
            "leave.change_leaverequest",
            "leave.delete_leaverequest",
        ]
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = user.employee_get
        if perm in leave_perm:
            is_approval_manager = MultipleApprovalManagers.objects.filter(
                employee_id=employee.id
            ).exists()
            if is_approval_manager:
                return function(self, *args, **kwargs)
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        if user.has_perm(perm) or is_manager:
            return function(self, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            return HttpResponse(script)

    return _function
