from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render

from horilla.decorators import decorator_with_arguments
from horilla.horilla_middlewares import _thread_locals
from offboarding.models import Offboarding, OffboardingStage, OffboardingTask


@decorator_with_arguments
def any_manager_can_enter(function, perm, offboarding_employee_can_enter=False):
    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        employee = request.user.employee_get
        if (
            request.user.has_perm(perm)
            or offboarding_employee_can_enter
            or (
                Offboarding.objects.filter(managers=employee).exists()
                | OffboardingStage.objects.filter(managers=employee).exists()
                | OffboardingTask.objects.filter(managers=employee).exists()
            )
        ):
            return function(self, *args, **kwargs)
        else:
            previous_url = request.META.get("HTTP_REFERER", "/")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(self, "decorator_404.html")
            return HttpResponse(script)

    return _function


@decorator_with_arguments
def offboarding_manager_can_enter(function, perm):
    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        employee = request.user.has_perm(perm)
        if (
            request.user.has_perm(perm)
            or Offboarding.objects.filter(managers=employee).exists()
        ):
            return function(self, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(self, "decorator_404.html")
            return HttpResponse(script)

    return _function


@decorator_with_arguments
def offboarding_or_stage_manager_can_enter(function, perm):
    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        employee = request.user.has_perm(perm)
        if (
            request.user.has_perm(perm)
            or Offboarding.objects.filter(managers=employee).exists()
            or OffboardingStage.objects.filter(managers=employee).exists()
        ):
            return function(self, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            return HttpResponse(script)

    return _function
