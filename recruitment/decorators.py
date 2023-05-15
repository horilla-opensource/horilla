from employee.models import Employee
from recruitment.models import Recruitment,Stage
from django.contrib import messages
from django.http import HttpResponseRedirect

decorator_with_arguments = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)
@decorator_with_arguments
def manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager.
    """
    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = Stage.objects.filter(stage_managers=employee).exists() or Recruitment.objects.filter(recruitment_managers=employee).exists()
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        else:
            messages.info(request,'You dont have permission.')
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return _function




decorator_with_arguments = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)
@decorator_with_arguments
def recruitment_manager_can_enter(function, perm):
    """
    This method is used to check permission to employee for enter to the function if the employee
    do not have permission also checks, has reporting manager.
    """
    def _function(request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(employee_user_id=user).first()
        is_manager = Recruitment.objects.filter(recruitment_managers=employee).exists()
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))

    return _function

