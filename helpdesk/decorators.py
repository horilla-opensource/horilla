from django.http import HttpResponseRedirect
from django.shortcuts import render
from pyexpat.errors import messages

from base.methods import check_manager
from helpdesk.models import Ticket

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


@decorator_with_arguments
def ticket_owner_can_enter(function, perm: str, model: object, manager_access=False):
    from employee.models import Employee, EmployeeWorkInformation

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
            or Ticket.objects.filter(assigned_to__in=[request.user.employee_get])
            or Ticket.objects.filter(created_by=request.user)
        )
        if can_enter:
            return function(request, *args, **kwargs)
        return render(request, "no_perm.html")

    return _function
