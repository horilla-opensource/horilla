from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from pyexpat.errors import messages

from employee.models import EmployeeWorkInformation
from pms.models import EmployeeObjective, Feedback, Objective

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def pms_manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager or manager of respective objective.
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = user.employee_get
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        is_objective_manager = Objective.objects.filter(managers=employee).exists()
        if user.has_perm(perm) or is_manager or is_objective_manager:
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


@decorator_with_arguments
def pms_owner_and_manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager or manager of respective objective.
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = user.employee_get
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        is_objective_owner = EmployeeObjective.objects.filter(
            employee_id=employee
        ).exists()
        is_objective_manager = Objective.objects.filter(managers=employee).exists()
        if (
            user.has_perm(perm)
            or is_manager
            or is_objective_manager
            or is_objective_owner
        ):
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


def check_permission_feedback_detailed_view(request, feedback, perm):
    """
    Checks if the user has permission to view the detailed view of feedback.

    The user is allowed if they:
    - Have the required permission
    - Are the owner of the feedback
    - Are the reporting manager of the feedback owner
    - Are the feedback manager

    Args:
        request: The HTTP request object containing the user.
        feedback: The feedback object being accessed.
        perm: The specific permission required.

    Returns:
        bool: True if the user has permission, False otherwise.
    """
    user = request.user
    employee = user.employee_get

    # Check if the user is the reporting manager of the feedback owner
    is_manager = EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee, employee_id=feedback.employee_id
    ).exists()

    # Check for permission, if the user is the feedback manager, reporting manager, or the feedback owner
    has_permission = (
        user.has_perm(perm)
        or feedback.manager_id == employee
        or is_manager
        or feedback.employee_id == employee
    )

    return has_permission
