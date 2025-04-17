"""
offboarding/decorators.py

This module is used to write custom authentication decorators for offboarding module
"""

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from horilla.decorators import decorator_with_arguments
from offboarding.models import (
    Offboarding,
    OffboardingGeneralSetting,
    OffboardingStage,
    OffboardingTask,
)


@decorator_with_arguments
def any_manager_can_enter(function, perm, offboarding_employee_can_enter=False):
    def _function(request, *args, **kwargs):
        employee = request.user.employee_get
        permissions = perm
        has_permission = False
        if not isinstance(permissions, (list, tuple, set)):
            permissions = [permissions]
        has_permission = any(request.user.has_perm(perm) for perm in permissions)
        if (
            has_permission
            or offboarding_employee_can_enter
            or (
                Offboarding.objects.filter(managers=employee).exists()
                | OffboardingStage.objects.filter(managers=employee).exists()
                | OffboardingTask.objects.filter(managers=employee).exists()
            )
        ):
            return function(request, *args, **kwargs)
        else:
            messages.info(request, "You don't have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            return HttpResponse(script)

    return _function


@decorator_with_arguments
def offboarding_manager_can_enter(function, perm):
    def _function(request, *args, **kwargs):
        employee = request.user.employee_get
        if (
            request.user.has_perm(perm)
            or Offboarding.objects.filter(managers=employee).exists()
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


@decorator_with_arguments
def offboarding_or_stage_manager_can_enter(function, perm):
    def _function(request, *args, **kwargs):
        employee = request.user.employee_get
        if (
            request.user.has_perm(perm)
            or Offboarding.objects.filter(managers=employee).exists()
            or OffboardingStage.objects.filter(managers=employee).exists()
        ):
            return function(request, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            return HttpResponse(script)

    return _function


@decorator_with_arguments
def check_feature_enabled(function, feature_name):
    def _function(request, *args, **kwargs):
        general_setting = OffboardingGeneralSetting.objects.first()
        enabled = getattr(general_setting, feature_name, False)
        if enabled:
            return function(request, *args, **kwargs)
        messages.info(request, "Feature is not enabled on the settings")
        previous_url = request.META.get("HTTP_REFERER", "/")
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        return HttpResponse(script)

    return _function
