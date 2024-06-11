import logging
import os
from urllib.parse import urlencode

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from base.models import BiometricAttendance, MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from horilla import settings
from horilla.settings import BASE_DIR, TEMPLATES

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
        object_instance = kwargs["model"].objects.filter(pk=obj_id).first()
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


from urllib.parse import urlparse


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
            logger.error(e)
            if (
                "notifications_notification" in str(e)
                and request.headers.get("X-Requested-With") != "XMLHttpRequest"
            ):
                referer = request.META.get("HTTP_REFERER", "/")
                messages.warning(request, str(e))
                return HttpResponse(
                    f"<script>window.location.href ='{str(referer)}'</script>"
                )

            if not settings.DEBUG:
                return render(request, "went_wrong.html")
            return view_func(request, *args, **kwargs)
        return func

    return wrapped_view


def hx_request_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        key = "HTTP_HX_REQUEST"
        if key not in request.META.keys():
            html_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Method Not Allowed</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f8f9fa;
                        color: #333;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        text-align: center;
                        background: #fff;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                    h1 {
                        font-size: 24px;
                        margin-bottom: 10px;
                    }
                    p {
                        font-size: 18px;
                        margin-bottom: 20px;
                    }
                    a {
                        color: #007bff;
                        text-decoration: none;
                        font-weight: bold;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>405 Method Not Allowed</h1>
                    <p>The request method is not allowed. Please make sure you are sending a proper request.</p>
                    <a href="/">Go Back to Home</a>
                </div>
            </body>
            </html>
            """
            return HttpResponse(html_content, content_type="text/html", status=405)
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
            try:
                employee = model.objects.get(id=instance_id).employee_id
            except:
                messages.error(request, ("Sorry, something went wrong!"))
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
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


def install_required(function):
    def _function(request, *args, **kwargs):
        object = BiometricAttendance.objects.all().first()
        if object.is_installed:
            return function(request, *args, **kwargs)
        else:
            messages.info(
                request,
                _(
                    "Please activate the biometric attendance feature in the settings menu."
                ),
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return _function


@decorator_with_arguments
def meeting_manager_can_enter(function, perm, answerable=False):
    def _function(request, *args, **kwargs):

        user = request.user
        employee = user.employee_get
        is_answer_employee = False

        is_manager = (
            Employee.objects.filter(
                meeting_manager__isnull=False,
            )
            .filter(id=employee.id)
            .exists()
        )

        if answerable:
            is_answer_employee = (
                Employee.objects.filter(
                    meeting_answer_employees__isnull=False,
                )
                .filter(id=employee.id)
                .exists()
            )

        if user.has_perm(perm) or is_manager or is_answer_employee:
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
