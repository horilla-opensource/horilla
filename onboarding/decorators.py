"""
decorators.py

Custom decorators for permission and manager checks in the application.
"""

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from employee.models import Employee
from onboarding.models import OnboardingStage, OnboardingTask
from recruitment.models import Recruitment


def decorator_with_arguments(decorator):
    """
    Decorator that allows decorators to accept arguments and keyword arguments.

    Args:
        decorator (function): The decorator function to be wrapped.

    Returns:
        function: The wrapper function.

    """

    def wrapper(*args, **kwargs):
        """
        Wrapper function that captures the arguments and keyword arguments.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            function: The inner wrapper function.

        """

        def inner_wrapper(func):
            """
            Inner wrapper function that applies the decorator to the function.

            Args:
                func (function): The function to be decorated.

            Returns:
                function: The decorated function.

            """
            return decorator(func, *args, **kwargs)

        return inner_wrapper

    return wrapper


@decorator_with_arguments
def all_manager_can_enter(function, perm):
    """
    This method is used to check permission of employee for enter to the function
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            OnboardingTask.objects.filter(employee_id=employee).exists()
            or OnboardingStage.objects.filter(employee_id=employee)
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function


@decorator_with_arguments
def stage_manager_can_enter(function, perm):
    """
    This method is used to check permission of employee for enter to the function
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            OnboardingStage.objects.filter(employee_id=employee)
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function


@decorator_with_arguments
def recruitment_manager_can_enter(function, perm):
    """
    This method is used to check permission of employee for enter to the function
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = Recruitment.objects.filter(recruitment_managers=employee).exists()
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function
