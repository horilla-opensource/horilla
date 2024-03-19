import logging, os
from urllib.parse import urlencode
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.urls import reverse
from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from django.contrib import messages
from django.shortcuts import render
from horilla.settings import TEMPLATES, BASE_DIR
from horilla import settings
from leave.models import LeaveRequestConditionApproval


logger = logging.getLogger(__name__)

TEMPLATES[0]["DIRS"] = [os.path.join(BASE_DIR, "templates")]

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


def check_manager(employee, instance):
    try:
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == employee
        return employee == instance.employee_id.employee_work_info.reporting_manager_id
    except:
        return False


@decorator_with_arguments
def permission_required(function, perm):
    def _function(request, *args, **kwargs):
        if request.user.has_perm(perm):
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


decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def delete_permission(function):
    def _function(request, *args, **kwargs):
        user = request.user
        employee = user.employee_get
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        if (
            request.user.has_perm(
                kwargs["model"]._meta.app_label
                + ".delete_"
                + kwargs["model"]._meta.model_name
            )
            or is_manager
        ):
            return function(request, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission for delete.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            return HttpResponse(script)

    return _function


decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def duplicate_permission(function):
    def _function(request, *args, **kwargs):
        user = request.user
        employee = user.employee_get
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        
        app_label = kwargs["model"]._meta.app_label
        model_name = kwargs["model"]._meta.model_name
        obj_id = kwargs["obj_id"]
        object_instance =  kwargs["model"].objects.filter(pk=obj_id).first()
        try:
            if object_instance.employee_id == employee:
                 return function(request, *args, **kwargs)
        except:
            pass
        permission = f"{app_label}.add_{model_name}"
        if request.user.has_perm(permission) or is_manager:
            return function(request, *args, **kwargs)
        else:
            messages.info(request, "You dont have permission for duplicate action.")
            previous_url = request.META.get("HTTP_REFERER", "/")
            key = "HTTP_HX_REQUEST"
            if key in request.META.keys():
                return render(request, "decorator_404.html")
            script = f'<script>window.location.href = "{previous_url}"</script>'
            return HttpResponse(script)

    return _function


decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager.
    """

    def _function(request, *args, **kwargs):
        leave_perm = [
            "leave.view_leaverequest",
            "leave.change_leaverequest",
            "leave.delete_leaverequest",
        ]
        user = request.user
        employee = user.employee_get
        if perm in leave_perm:
            is_approval_manager = MultipleApprovalManagers.objects.filter(
                employee_id=employee.id
            ).exists()
            if is_approval_manager:
                return function(request, *args, **kwargs)
        is_manager = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee
        ).exists()
        if user.has_perm(perm) or is_manager:
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


def login_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        path = request.path
        res = path.split("/", 2)[1].capitalize().replace("-", " ").upper()
        if res == "PMS":
            res = "Performance"
        request.session["title"] = res
        if path == "" or path == "/":
            request.session["title"] = "Dashboard".upper()
        if not request.user.is_authenticated:
            login_url = reverse("login")
            params = urlencode(request.GET)
            url = f"{login_url}?next={request.path}"
            if params:
                url += f"&{params}"
            return redirect(url)
        try:
            func = view_func(request, *args, **kwargs)
        except Exception as e:
            logger.exception(e)
            if not settings.DEBUG:
                return render(request, "went_wrong.html")
            return view_func(request, *args, **kwargs)
        return func

    return wrapped_view


def hx_request_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        key = "HTTP_HX_REQUEST"
        if key not in request.META.keys():
            return HttpResponse("method not allowed...")
        return view_func(request, *args, **kwargs)

    return wrapped_view


@decorator_with_arguments
def owner_can_enter(function, perm: str, model: object, manager_access=False):
    """
    Only the users with permission, or the owner, or employees manager can enter,
    If manager_access:True then all the managers can enter
    """

    def _function(request, *args, **kwargs):
        instance_id = kwargs[list(kwargs.keys())[0]]
        if model == Employee:
            employee = Employee.objects.get(id=instance_id)
        else:
            employee = model.objects.get(id=instance_id).employee_id
        can_enter = (
            request.user.employee_get == employee
            or request.user.has_perm(perm)
            or check_manager(request.user.employee_get, employee)
            or (
                EmployeeWorkInformation.objects.filter(
                    reporting_manager_id__employee_user_id=request.user
                ).exists()
                if manager_access
                else False
            )
        )
        if can_enter:
            return function(request, *args, **kwargs)
        return render(request, "no_perm.html")

    return _function
