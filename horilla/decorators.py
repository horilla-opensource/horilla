from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import redirect
from employee.models import Employee, EmployeeWorkInformation
from django.contrib import messages

decorator_with_arguments = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)
@decorator_with_arguments
def permission_required(function, perm):
    def _function(request, *args, **kwargs):
        if request.user.has_perm(perm):
            return function(request, *args, **kwargs)
        else:
            messages.info(request,'You dont have permission.')
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))

    return _function



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
        is_manager = EmployeeWorkInformation.objects.filter(reporting_manager_id=employee).exists()
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        else:
            messages.info(request,'You dont have permission.')
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return _function


def login_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        path = request.path
        res = path.split('/', 2)[1].capitalize().replace('-',' ').upper()
        request.session['title'] = res
        if path == '' or path == '/':
            request.session['title'] = 'Dashboard'.upper()
        if not request.user.is_authenticated:
            return redirect('/login')
        return view_func(request, *args, **kwargs)
    return wrapped_view

def hx_request_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        key = 'HTTP_HX_REQUEST'
        if key not in request.META.keys():
            return HttpResponse('method not allowed...')
        return view_func(request, *args, **kwargs)
    return wrapped_view




