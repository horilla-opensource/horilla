from project.methods import any_project_manager, any_project_member, any_task_manager, any_task_member
from .models import Project,Task,ProjectStage
from django.contrib import messages
from django.http import HttpResponseRedirect


decorator_with_arguments = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)

@decorator_with_arguments
def is_projectmanager_or_member_or_perms(function,perm):
    def _function(request, *args, **kwargs):
        """
        This method is used to check the employee is project manager or not       
        """
        user = request.user
        if (
            user.has_perm(perm) or 
            any_project_manager(user) or
            any_project_member(user) or
            any_task_manager(user) or
            any_task_member(user)
        ):
            return function(request, *args, **kwargs)
        messages.info(request, "You don't have permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return _function

@decorator_with_arguments
def project_update_permission(function=None, *args, **kwargs):
    def check_project_member(request,project_id=None,*args, **kwargs,):
        """
        This method is used to check the employee is project member or not       
        """
        project = Project.objects.get(id = project_id)
        if (request.user.has_perm('project.change_project') or 
            request.user.employee_get == project.manager or
            request.user.employee_get in project.members.all()    
        ):
            return function(request, *args,project_id=project_id, **kwargs)
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
        # return function(request, *args, **kwargs)
    return check_project_member


@decorator_with_arguments
def project_delete_permission(function=None,*args,**kwargs):
    def is_project_manager(request,project_id=None,*args, **kwargs,):
        """
        This method is used to check the employee is project manager or not       
        """
        project = Project.objects.get(id = project_id)
        if ( 
            request.user.employee_get == project.manager or
            request.user.has_perm('project.delete_project')
        ):
            return function(request, *args,project_id=project_id, **kwargs)
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return is_project_manager


@decorator_with_arguments
def project_stage_update_permission(function=None, *args, **kwargs):
    def check_project_member(request,stage_id=None,*args, **kwargs,):
        """
        This method is used to check the employee is project stage member or not       
        """
        project = ProjectStage.objects.get(id = stage_id).project
        if (request.user.has_perm('project.change_project') or
            request.user.has_perm('project.change_task') or 
            request.user.employee_get == project.manager or
            request.user.employee_get in project.members.all() 
        ):
            return function(request, *args,stage_id=stage_id, **kwargs)
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
        # return function(request, *args, **kwargs)
    return check_project_member

@decorator_with_arguments
def project_stage_delete_permission(function=None,*args,**kwargs):
    def is_project_manager(request,stage_id=None,*args, **kwargs,):
        """
        This method is used to check the employee is project stage manager or not       
        """
        project = ProjectStage.objects.get(id = stage_id).project
        if ( 
            request.user.employee_get == project.manager or
            request.user.has_perm('project.delete_project')
        ):
            return function(request, *args,stage_id=stage_id, **kwargs)
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return is_project_manager

@decorator_with_arguments
def task_update_permission(function=None,*args,**kwargs):
    def is_task_member(request,task_id):
        """
        This method is used to check the employee is task member or not       
        """
        task = Task.objects.get(id = task_id)
        project = task.project

        if (request.user.has_perm('project.change_task') or 
            request.user.has_perm('project.change_project') or 
            request.user.employee_get == task.task_manager or
            request.user.employee_get in task.task_members.all() or
            request.user.employee_get == project.manager or
            request.user.employee_get in project.members.all()     
        ):
            return function(request, *args,task_id=task_id, **kwargs)
        
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))    
    return is_task_member


@decorator_with_arguments
def task_delete_permission(function=None,*args,**kwargs):
    def is_task_manager(request,task_id):
        """
        This method is used to check the employee is task manager or not       
        """
        task = Task.objects.get(id = task_id)
        project = task.project

        if (request.user.has_perm('project.delete_task') or 
            request.user.has_perm('project.delete_project') or 
            request.user.employee_get == task.task_manager or
            request.user.employee_get == project.manager 
        ):
            return function(request,task_id=task_id)
        
        messages.info(request,'You dont have permission.')
        return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))    
    return is_task_manager