"""
decorator functions for base
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render

from base.models import MultipleApprovalManagers
from employee.models import EmployeeWorkInformation

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def report_manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager.
    """

    def _function(request, *args, **kwargs):
        leave_perm = [
            "leave.view_leaverequest",
            "leave.change_leaverequest",
            "leave.delete_leaverequest",
        ]
        user = request.user
        employee = user.employee_get
        if perm in leave_perm:
            is_approval_manager = MultipleApprovalManagers.objects.filter(
                employee_id=employee.id
            ).exists()
            if is_approval_manager:
                return function(request, *args, **kwargs)
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            return HttpResponse(script)

    return _function
