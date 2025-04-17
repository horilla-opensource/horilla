import random

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from base.methods import get_pagination, get_subordinates
from employee.models import Employee
from project.models import Project, Task, TimeSheet

decorator_with_arguments = (
    lambda decorator: lambda *args, **kwargs: lambda func: decorator(
        func, *args, **kwargs
    )
)


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
    if r == g or g == b or b == r:
        random_color_generator()
    return f"rgba({r}, {g}, {b} , 0.7)"


# color_palette=[]
# Function to generate distinct colors for each project
def generate_colors(num_colors):
    # Define a color palette with distinct colors
    color_palette = [
        "rgba(255, 99, 132, 1)",  # Red
        "rgba(54, 162, 235, 1)",  # Blue
        "rgba(255, 206, 86, 1)",  # Yellow
        "rgba(75, 192, 192, 1)",  # Green
        "rgba(153, 102, 255, 1)",  # Purple
        "rgba(255, 159, 64, 1)",  # Orange
    ]

    if num_colors > len(color_palette):
        for i in range(num_colors - len(color_palette)):
            color_palette.append(random_color_generator())

    colors = []
    for i in range(num_colors):
        # color=random_color_generator()
        colors.append(color_palette[i % len(color_palette)])

    return colors


def any_project_manager(user):
    employee = user.employee_get
    if employee.project_managers.all().exists():
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
def is_projectmanager_or_member_or_perms(function, perm):
    def _function(request, *args, **kwargs):
        """
        This method is used to check the employee is project manager or not
        """
        user = request.user
        if (
            user.has_perm(perm)
            or any_project_manager(user)
            or any_project_member(user)
            or any_task_manager(user)
            or any_task_member(user)
        ):
            return function(request, *args, **kwargs)
        messages.info(request, "You don't have permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    return _function


def is_task_member(request, task_id):
    """
    This method is used to check the employee is task member or not
    """
    if (
        request.user.has_perm("project.change_task")
        or request.user.employee_get in Task.objects.get(id=task_id).task_managers.all()
        or request.user.employee_get in Task.objects.get(id=task_id).task_members.all()
    ):
        return True
    return False


def is_task_manager(request, task_id):
    """
    This method is used to check the employee is task member or not
    """
    if (
        request.user.has_perm("project.delete_task")
        or request.user.employee_get in Task.objects.get(id=task_id).task_managers.all()
    ):
        return True
    return False


def time_sheet_update_permissions(request, time_sheet_id):
    if (
        request.user.has_perm("project.change_timesheet")
        or request.user.employee_get
        == TimeSheet.objects.get(id=time_sheet_id).employee_id
        or TimeSheet.objects.get(id=time_sheet_id).employee_id
        in Employee.objects.filter(
            employee_work_info__reporting_manager_id=request.user.employee_get
        )
    ):
        return True
    else:
        return False


def time_sheet_delete_permissions(request, time_sheet_id):
    employee = request.user.employee_get
    timesheet = TimeSheet.objects.filter(id=time_sheet_id).first()
    if (
        request.user.has_perm("project.delete_timesheet")
        or timesheet.employee_id == employee
        or employee in timesheet.task_id.task_managers.all()
        or employee in timesheet.task_id.project.managers.all()
    ):
        return True
    else:
        return False


def get_all_project_members_and_managers():
    all_projects = Project.objects.all()
    all_tasks = Task.objects.all()

    all_ids = set()

    for project in all_projects:
        all_ids.update(
            manager.id for manager in project.managers.all()
        )  # Add manager ID
        all_ids.update(member.id for member in project.members.all())  # Add member IDs

    for task in all_tasks:
        all_ids.update(
            task_manager.id for task_manager in task.task_managers.all()
        )  # Add task manager ID
        all_ids.update(
            task_member.id for task_member in task.task_members.all()
        )  # Add task member IDs

    # Return a single queryset for all employees
    return Employee.objects.filter(id__in=all_ids)


def has_subordinates(request):
    """
    used to check whether the project contain users subordinates or not
    """
    all_members_info = get_all_project_members_and_managers()
    subordinates = get_subordinates(request)

    member = {member for member in all_members_info}

    for subordinate in subordinates:
        if subordinate in member:
            return True

    return False


def is_project_manager_or_super_user(request, project):
    """
    Method to check whether user is a manager of project or
    user is a super user.
    """
    return (
        request.user.employee_get in project.managers.all() or request.user.is_superuser
    )


def you_dont_have_permission(request):
    """
    Method to return you dont have permission
    """
    messages.info(request, "You dont have permission.")
    previous_url = request.META.get("HTTP_REFERER", "/")
    key = "HTTP_HX_REQUEST"
    if key in request.META.keys():
        return render(request, "decorator_404.html")
    script = f'<script>window.location.href = "{previous_url}"</script>'
    return HttpResponse(script)
