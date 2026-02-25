"""CBV decorators for offboarding permission checks."""

from horilla.decorators import decorator_with_arguments
from horilla.horilla_middlewares import _thread_locals
from horilla.methods import handle_no_permission
from offboarding.models import Offboarding, OffboardingStage, OffboardingTask


@decorator_with_arguments
def any_manager_can_enter(function, perm, offboarding_employee_can_enter=False):
    """Allow access if user has perm, is offboarding employee, or is manager on any offboarding/stage/task."""

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

        return handle_no_permission(request)

    return _function


@decorator_with_arguments
def offboarding_manager_can_enter(function, perm):
    """Allow access if user has perm or is manager on an Offboarding."""

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

        return handle_no_permission(request)

    return _function


@decorator_with_arguments
def offboarding_or_stage_manager_can_enter(function, perm):
    """Allow access if user has perm or is manager on an Offboarding or OffboardingStage."""

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

        return handle_no_permission(request)

    return _function
