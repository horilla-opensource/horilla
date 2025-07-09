"""
decorators.py

Custom decorators for permission and manager checks in the application.
"""

from functools import wraps

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render

from employee.models import Employee
from recruitment.models import Recruitment, Stage


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
def manager_can_enter(function, perm=None, perms=None):
    """
    Decorator that checks if the user has the specified permission(s) or is a manager.

    Args:
        perm (str): A single permission string.
        perms (list): A list of permission strings.

    Returns:
        function: The decorated view.
    """

    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()

        is_manager = (
            Stage.objects.filter(stage_managers=employee).exists()
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
        )

        # Combine perm and perms into one list to check
        all_perms = []
        if perm:
            all_perms.append(perm)
        if perms:
            all_perms.extend(perms)

        has_required_perm = any(user.has_perm(p) for p in all_perms)

        if has_required_perm or is_manager:
            return function(request, *args, **kwargs)

        messages.info(request, "You don't have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")

        if request.META.get("HTTP_HX_REQUEST"):
            return render(request, "decorator_404.html")

        return HttpResponse(f'<script>window.location.href = "{previous_url}"</script>')

    return _function


@decorator_with_arguments
def recruitment_manager_can_enter(function, perm):
    """
    Decorator that checks if the user has the specified permission or is a recruitment manager.

    Args:
        perm (str): The permission to check.

    Returns:
        function: The decorated function.

    Raises:
        None

    """

    def _function(request, *args, **kwargs):
        """
        Inner function that performs the permission and manager check.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response from the decorated function.
        """
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


def candidate_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if request.user.has_perm("recruitment.view_candidate"):
            return view_func(request, *args, **kwargs)
        if request.user:
            if request.user.is_authenticated:
                if (
                    request.user.employee_get.stage_set.exists()
                    or request.user.employee_get.recruitment_set.exists()
                ):
                    return view_func(request, *args, **kwargs)

        if "candidate_id" in request.session:
            return view_func(request, *args, **kwargs)
        return redirect("candidate-login")

    return _wrapped_view
