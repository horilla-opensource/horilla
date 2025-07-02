from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render

from employee.models import Employee
from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import decorator_with_arguments
from onboarding.models import OnboardingStage, OnboardingTask
from recruitment.models import Recruitment


@decorator_with_arguments
def recruitment_manager_can_enter(function, perm):
    """
    This method is used to check permission of employee for enter to the function
    """

    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = Recruitment.objects.filter(recruitment_managers=employee).exists()
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
def stage_manager_can_enter(function, perm):
    """
    This method is used to check permission of employee for enter to the function
    """

    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            OnboardingStage.objects.filter(employee_id=employee)
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
    This method is used to check permission of employee for enter to the function
    """

    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = (
            OnboardingTask.objects.filter(employee_id=employee).exists()
            or OnboardingStage.objects.filter(employee_id=employee)
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
