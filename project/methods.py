import random
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import HttpResponseRedirect
from base.methods import get_pagination
from recruitment.decorators import decorator_with_arguments
from employee.models import Employee
from project.models import TimeSheet,Project,Task


def strtime_seconds(time):
    """
    this method is used to reconvert time in H:M formate string back to seconds and return it
    args:
        time : time in H:M format
    """
    ftr = [3600, 60, 1]
    return sum(a * b for a, b in zip(ftr, map(int, time.split(":"))))


def paginator_qry(qryset, page_number):
    """
    This method is used to generate common paginator limit.
    """
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


def random_color_generator():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    if r==g or g==b or b==r:
        random_color_generator()
    return f"rgba({r}, {g}, {b} , 0.7)"


# color_palette=[]
# Function to generate distinct colors for each project
def generate_colors(num_colors):
    # Define a color palette with distinct colors
    color_palette = [
        "rgba(255, 99, 132, 1)",   # Red
        "rgba(54, 162, 235, 1)",   # Blue
        "rgba(255, 206, 86, 1)",   # Yellow
        "rgba(75, 192, 192, 1)",   # Green
        "rgba(153, 102, 255, 1)",  # Purple
        "rgba(255, 159, 64, 1)",   # Orange
    ]
    
    if num_colors > len(color_palette):
        for i in range(num_colors-len(color_palette)):
            color_palette.append(random_color_generator())

    colors = []
    for i in range(num_colors):
        # color=random_color_generator()
        colors.append(color_palette[i % len(color_palette)])

    return colors

def any_project_manager(user):
    employee = user.employee_get
    if employee.project_manager.all().exists():
        return True
    else:
        return False

def any_project_member(user):
    employee = user.employee_get
    if employee.project_members.all().exists():
        return True
    else:
        return False
    
def any_task_manager(user):
    employee = user.employee_get
    if employee.task_set.all().exists():
        return True
    else:
        return False

def any_task_member(user):
    employee = user.employee_get
    if employee.tasks.all().exists():
        return True
    else:
        return False
    
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


# def is_project_member(request,project_id):
#     """
#     This method is used to check the employee is project member or not       
#     """
#     print(Project.objects.get(id = project_id))
#     print(Project.objects.get(id = project_id).members.all() )
#     if (request.user.has_perm('project.change_project') or 
#         request.user.employee_get == Project.objects.get(id = project_id).manager or
#         request.user.employee_get in Project.objects.get(id = project_id).members.all()    
#     ):
#         return True
#     return False

# def is_project_manager(request,project_id):
#     """
#     This method is used to check the employee is project manager or not       
#     """
#     print(Project.objects.get(id = project_id))
#     print(Project.objects.get(id = project_id).manager )
#     if ( 
#         request.user.employee_get == Project.objects.get(id = project_id).manager or
#         request.user.has_perm('project.delete_project')

#     ):
#         return True
#     return False


# def is_project_manager(request, project_id):
#     """
#     This function checks if the user is a project manager or has permission to delete a project.
#     """
#     user = request.user
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return False  # Project with the specified ID does not exist

#     if user.employee_get == project.manager or user.has_perm('project.delete_project'):
#         return True  # User is a project manager or has delete_project permission
    
#     return False  # User does not have the required permission


def is_task_member(request,task_id):
    """
    This method is used to check the employee is task member or not       
    """
    if (request.user.has_perm('project.change_task') or 
        request.user.employee_get == Task.objects.get(id = task_id).task_manager or
        request.user.employee_get in Task.objects.get(id = task_id).task_members.all()    
    ):
        return True
    return False

def is_task_manager(request,task_id):
    """
    This method is used to check the employee is task member or not       
    """
    if (request.user.has_perm('project.delete_task') or 
        request.user.employee_get == Task.objects.get(id = task_id).task_manager    
    ):
        return True
    return False


def time_sheet_update_permissions(request,time_sheet_id):
    if (
        request.user.has_perm("project.change_timesheet") 
        or request.user.employee_get == TimeSheet.objects.get(id=time_sheet_id).employee_id
        or TimeSheet.objects.get(id=time_sheet_id).employee_id in Employee.objects.filter(employee_work_info__reporting_manager_id=request.user.employee_get)
    ):
        return True
    else:
        return False
    
def time_sheet_delete_permissions(request,time_sheet_id):
    if (
        request.user.has_perm("project.delete_timesheet") 
        or request.user.employee_get == TimeSheet.objects.get(id=time_sheet_id).employee_id
        or TimeSheet.objects.get(id=time_sheet_id).employee_id in Employee.objects.filter(employee_work_info__reporting_manager_id=request.user.employee_get)
    ):
        return True
    else:
        return False