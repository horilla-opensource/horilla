from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render

from employee.models import Employee
from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import decorator_with_arguments
from recruitment.models import Recruitment, Stage


@decorator_with_arguments
def manager_can_enter(function, perm):
    """
    Decorator that checks if the user has the specified permission or is a manager.

    Args:
        perm (str): The permission to check.

    Returns:
        function: The decorated function.

    Raises:
        None

    """

    def _function(self, *args, **kwargs):
        """
        Inner function that performs the permission and manager check.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response from the decorated function.

        """
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            Stage.objects.filter(stage_managers=employee).exists()
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(self, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function


@decorator_with_arguments
def all_manager_can_enter(function, perm):
    """
    Decorator that checks if the user has the specified permission or is a manager.

    Args:
        perm (str): The permission to check.

    Returns:
        function: The decorated function.

    Raises:
        None

    """

    def _function(self, *args, **kwargs):
        """
        Inner function that performs the permission and manager check.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response from the decorated function.

        """
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            Stage.objects.filter(stage_managers=employee).exists()
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
            or request.user.employee_get.onboardingstage_set.exists()
            or request.user.employee_get.onboarding_task.exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(self, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function
