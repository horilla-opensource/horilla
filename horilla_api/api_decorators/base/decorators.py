from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from horilla.decorators import check_manager
from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import decorator_with_arguments


class ManagerPermission(BasePermission):
    leave_perm = [
        "leave.view_leaverequest",
        "leave.change_leaverequest",
        "leave.delete_leaverequest",
    ]

    def has_permission(self, request, perm):
        user = request.user
        employee = user.employee_get
        if perm in self.leave_perm:
            is_approval_manager = MultipleApprovalManagers.objects.filter(
                employee_id=employee.id
            ).exists()
            if is_approval_manager:
                return True

        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()

        if user.has_perm(perm) or is_manager:
            return True
        return False


def manager_permission_required(perm):
    """
    Decorator for views that checks whether the user has appropriate manager permissions.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            permission = ManagerPermission()
            if permission.has_permission(request, perm):
                return func(self, request, *args, **kwargs)
            else:
                return Response(
                    {"error": _("You do not have permission to perform this action.")},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return wrapper

    return decorator


def manager_or_owner_permission_required(model_class, perm):
    """
    Allow the owner of the record, a user holding ``perm``, or the reporting
    manager *of the specific employee the record belongs to*.

    The manager test has to name its target. This used to delegate to
    ``ManagerPermission``, which asks only whether anybody at all reports to the
    caller -- so any employee who managed one person passed the check for every
    employee in the company. On EmployeeBankDetails that let a line manager
    rewrite the account another employee's salary is paid into
    (GHSA-39gq-9wwx-p8hx). The same decorator also guards document requests and
    work-type and shift requests, which were reachable the same way.

    ``check_manager`` returns False for a target it cannot resolve, so an
    unknown or missing employee id denies rather than falls through.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, pk=None, *args, **kwargs):
            employee = request.user.employee_get

            if pk:
                try:
                    target = model_class.objects.get(pk=pk)
                except model_class.DoesNotExist:
                    return Response(
                        {"error": f"{model_class.__name__} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if target.employee_id == employee:
                    return func(self, request, pk, *args, **kwargs)
            else:
                # Nothing exists yet, so the target is whoever the payload names.
                # Compare as text: a form-encoded body delivers the id as a
                # string and JSON as an int, and an owner whose own id failed to
                # match would previously fall through to the manager branch.
                target_id = request.data.get("employee_id")
                if target_id is not None and str(target_id) == str(employee.id):
                    return func(self, request, *args, **kwargs)
                target = Employee.objects.filter(pk=target_id).first()

            if request.user.has_perm(perm) or check_manager(employee, target):
                if pk:
                    return func(self, request, pk, *args, **kwargs)
                return func(self, request, *args, **kwargs)

            return Response(
                {"error": _("You do not have permission to perform this action.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        return wrapper

    return decorator


def check_approval_status(model, perm):
    """checking the object approval status"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, pk, *args, **kwargs):
            object = model.objects.filter(id=pk).first()
            if object.approved:
                return Response(
                    {
                        "error": _("Approved %(model)s can't preform this action ")
                        % {"model": model.__name__}
                    },
                    status=400,
                )
            if object.canceled:
                return Response(
                    {
                        "error": _("Canceled %(model)s can't preform this action ")
                        % {"model": model.__name__}
                    },
                    status=400,
                )
            return func(self, request, pk, *args, **kwargs)

        return wrapper

    return decorator


@decorator_with_arguments
def permission_required(function, perm):
    """
    Decorator to validate user permissions
    """

    def _function(self, *args, **kwargs):
        request = getattr(_thread_locals, "request")
        if not getattr(self, "request", None):
            self.request = request
        if request.user.has_perm(perm):
            return function(self, *args, **kwargs)
        else:
            return Response({"message": _("No permission")}, status=401)

    return _function
