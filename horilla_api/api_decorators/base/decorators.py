from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from base.models import MultipleApprovalManagers
from employee.models import EmployeeWorkInformation
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
                    {"error": "You do not have permission to perform this action."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return wrapper

    return decorator


def manager_or_owner_permission_required(model_class, perm):
    """
    Decorator for views that checks whether the user has either manager or owner permissions and a specific permission for a specific object for a given model class.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, pk=None, *args, **kwargs):
            if pk:
                try:
                    obj = model_class.objects.get(pk=pk)
                    # Check if the requesting user is the owner of the object
                    if obj.employee_id == request.user.employee_get:
                        return func(self, request, pk, *args, **kwargs)
                except model_class.DoesNotExist:
                    return Response(
                        {"error": f"{model_class.__name__} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                if (
                    request.data.get("employee_id", None)
                    == request.user.employee_get.id
                ):
                    return func(self, request, *args, **kwargs)
            # If not the owner, check for manager permission
            permission = ManagerPermission()
            if permission.has_permission(request, perm) and pk:
                return func(self, request, pk, *args, **kwargs)
            elif permission.has_permission(request, perm) and pk == None:
                return func(self, request, *args, **kwargs)
            else:
                return Response(
                    {"error": "You do not have permission to perform this action."},
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
                    {"error": f"Approved {model.__name__} can't preform this action "},
                    status=400,
                )
            if object.canceled:
                return Response(
                    {"error": f"Canceled {model.__name__} can't preform this action "},
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
            return Response({"message": "No permission"}, status=401)

    return _function
