import calendar
import datetime
import json
import logging
from collections import defaultdict
from urllib.parse import parse_qs, urlparse

import pandas as pd
import xlsxwriter
from django.contrib import messages
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.methods import filtersubordinates, get_key_instances
from horilla.decorators import hx_request_required, login_required, permission_required
from notifications.signals import notify
from project.cbv.projects import DynamicProjectCreationFormView
from project.cbv.tasks import DynamicTaskCreateFormView
from project.cbv.timesheet import TimeSheetFormView
from project.methods import (
    generate_colors,
    paginator_qry,
    strtime_seconds,
    time_sheet_delete_permissions,
    time_sheet_update_permissions,
)

from .decorator import *
from .filters import ProjectFilter, TaskAllFilter, TaskFilter, TimeSheetFilter
from .forms import *
from .methods import (
    is_project_manager_or_super_user,
    is_projectmanager_or_member_or_perms,
    is_task_manager,
    is_task_member,
    you_dont_have_permission,
)
from .models import *

logger = logging.getLogger(__name__)

# Create your views here.
# Dash board view


@login_required
def dashboard_view(request):
    """
    Dashboard view of project
    Returns:
        it will redirect to dashboard.
    """

    # Get the current date
    today = datetime.date.today()
    # Find the last day of the current month
    last_day = calendar.monthrange(today.year, today.month)[1]
    # Construct the last date of the current month
    last_date = datetime.date(today.year, today.month, last_day)

    total_projects = Project.objects.all().count()
    new_projects = Project.objects.filter(status="new").count()
    projects_in_progress = Project.objects.filter(status="in_progress").count()
    date_range = {"end_till": last_date}
    projects_due_in_this_month = ProjectFilter(date_range).qs
    unexpired_project = []
    for project in projects_due_in_this_month:
        if project.status != "expired":
            unexpired_project.append(project)

    context = {
        "total_projects": total_projects,
        "new_projects": new_projects,
        "projects_in_progress": projects_in_progress,
        "unexpired_project": unexpired_project,
    }
    return render(request, "dashboard/project_dashboard.html", context=context)


@login_required
def project_status_chart(request):
    """
    This method is used generate project dataset for the dashboard
    """
    initial_data = []
    data_set = []
    choices = Project.PROJECT_STATUS
    labels = [type[1] for type in choices]
    for label in choices:
        initial_data.append(
            {
                "label": label[1],
                "data": [],
            }
        )

    for status in choices:
        count = Project.objects.filter(status=status[0]).count()
        data = []
        for index, label in enumerate(initial_data):
            if status[1] == initial_data[index]["label"]:
                data.append(count)
            else:
                data.append(0)
        data_set.append(
            {
                "label": status[1],
                "data": data,
            }
        )
    return JsonResponse({"dataSet": data_set, "labels": labels})


@login_required
def task_status_chart(request):
    """
    This method is used generate project dataset for the dashboard
    """
    # projects = Project.objects.all()
    initial_data = []
    data_set = []
    choices = Task.TASK_STATUS
    labels = [type[1] for type in choices]
    for label in choices:
        initial_data.append(
            {
                "label": label[1],
                "data": [],
            }
        )
    # for status in choices:
    #    count = Project.objects.filter(status=status[0]).count()

    for status in choices:
        count = Task.objects.filter(status=status[0]).count()
        data = []
        for index, label in enumerate(initial_data):
            if status[1] == initial_data[index]["label"]:
                data.append(count)
            else:
                data.append(0)
        data_set.append(
            {
                "label": status[1],
                "data": data,
            }
        )
    return JsonResponse({"dataSet": data_set, "labels": labels})


@login_required
def project_detailed_view(request, project_id):
    project = Project.objects.get(id=project_id)
    task_count = project.task_set.count()
    context = {
        "project": project,
        "task_count": task_count,
    }
    return render(request, "dashboard/project_details.html", context=context)


# Project views


@login_required
@is_projectmanager_or_member_or_perms(perm="project.view_project")
def project_view(request):
    """
    Overall view of project, the default view
    """
    form = ProjectFilter()
    view_type = "card"
    if request.GET.get("view") == "list":
        view_type = "list"
    projects = Project.objects.all()
    if request.GET.get("search") is not None:
        projects = ProjectFilter(request.GET).qs
    previous_data = request.environ["QUERY_STRING"]
    page_number = request.GET.get("page")
    context = {
        "view_type": view_type,
        "projects": paginator_qry(projects, page_number),
        "pd": previous_data,
        "f": form,
    }
    return render(request, "project/new/overall.html", context)


@permission_required(perm="project.add_project")
@login_required
def create_project(request):
    """
    For creating new project
    """
    form = ProjectForm()
    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("New project created"))
            response = render(
                request,
                "project/new/forms/project_creation.html",
                context={"form": form},
            )

            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request, "project/new/forms/project_creation.html", context={"form": form}
    )


@login_required
@project_update_permission()
def project_update(request, project_id):
    """
    Update an existing project.

    Args:
        request: The HTTP request object.
        project_id: The ID of the project to update.

    Returns:
        If the request method is POST and the form is valid, redirects to the project overall view.
        Otherwise, renders the project update form.

    """
    project = Project.objects.get(id=project_id)
    project_form = ProjectForm(instance=project)
    if request.method == "POST":
        project_form = ProjectForm(request.POST, request.FILES, instance=project)
        if project_form.is_valid():
            project_form.save()
            messages.success(request, _("Project updated"))
            response = render(
                request,
                "project/new/forms/project_update.html",
                {"form": project_form, "project_id": project_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "project/new/forms/project_update.html",
        {"form": project_form, "project_id": project_id},
    )


@login_required
@project_update_permission()
def change_project_status(request, project_id):
    """
    HTMX function to update the status of a project.
    Args:
    - project_id: ID of the Project object.
    """
    status = request.POST.get("status")
    try:
        project = get_object_or_404(Project, id=project_id)
        if status:
            if project.status != status:
                project.status = status
                project.save()
                messages.success(
                    request,
                    _(f"{project} status updated to {project.get_status_display()}."),
                )
                # Notify all project managers and members
                employees = (project.managers.all() | project.members.all()).distinct()
                for employee in employees:
                    try:
                        notify.send(
                            request.user.employee_get,
                            recipient=employee.employee_user_id,
                            verb=f"The status of the project '{project}' has been changed to {project.get_status_display()}.",
                            verb_ar=f"تم تغيير حالة المشروع '{project}' إلى {project.get_status_display()}.",
                            verb_de=f"Der Status des Projekts '{project}' wurde auf {project.get_status_display()} geändert.",
                            verb_es=f"El estado del proyecto '{project}' ha sido cambiado a {project.get_status_display()}.",
                            verb_fr=f"Le statut du projet '{project}' a été changé en {project.get_status_display()}.",
                            redirect=reverse(
                                "task-view",
                                kwargs={"project_id": project.id},
                            ),
                        )
                    except Exception as e:
                        logger.error(e)
            else:
                messages.info(
                    request,
                    _(
                        f"{project} status is already set to {project.get_status_display()}."
                    ),
                )
        else:
            messages.error(request, _("Invalid status or missing data."))

    except Http404:
        messages.error(request, _("The specified project does not exist."))
    return HttpResponse("<script>$('#reloadMessagesButton').click();</script>")


@login_required
@project_delete_permission()
def project_delete(request, project_id):
    """
    For deleting existing project
    """
    view_type = request.GET.get("view")
    project_view_url = reverse("project-view")
    redirected_url = f"{project_view_url}?view={view_type}"
    Project.objects.get(id=project_id).delete()

    return redirect(redirected_url)


@login_required
def project_filter(request):
    """
    For filtering projects
    """
    projects = ProjectFilter(request.GET).qs
    templete = "project/new/project_kanban_view.html"
    if request.GET.get("view") == "list":
        templete = "project/new/project_list_view.html"
    previous_data = request.environ["QUERY_STRING"]
    page_number = request.GET.get("page")
    filter_obj = projects
    data_dict = parse_qs(previous_data)
    get_key_instances(Project, data_dict)
    context = {
        "projects": paginator_qry(projects, page_number),
        "pd": previous_data,
        "f": filter_obj,
        "filter_dict": data_dict,
    }
    return render(request, templete, context)


def convert_nan(field, dicts):
    """
    This method is returns None or field value
    """
    field_value = dicts.get(field)
    try:
        float(field_value)
        return None
    except ValueError:
        return field_value


@login_required
def project_import(request):
    """
    This method is used to import Project instances and creates related objects
    """
    data_frame = pd.DataFrame(
        columns=[
            "Title",
            "Manager Badge id",
            "Member Badge id",
            "Status",
            "Start Date",
            "End Date",
            "Description",
        ]
    )
    # Export the DataFrame to an Excel file
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="project_template.xlsx"'
    data_frame.to_excel(response, index=False)

    if request.method == "POST" and request.FILES.get("file") is not None:
        file = request.FILES["file"]
        data_frame = pd.read_excel(file)
        project_dicts = data_frame.to_dict("records")
        error_lists = []
        for project in project_dicts:
            try:
                # getting datas from imported file
                title = project["Title"]
                manager_badge_id = convert_nan("Manager Badge id", project)
                member_badge_id = convert_nan("Member Badge id", project)
                status = project["Status"]
                start_date = project["Start Date"]
                end_date = project["End Date"]
                description = project["Description"]

                # checcking all the imported values
                is_save = True
                # getting employee using badge id, for manager
                if manager_badge_id:
                    ids = manager_badge_id.split(",")
                    error_ids = []
                    managers = []
                    for id in ids:
                        if Employee.objects.filter(badge_id=id).exists():
                            employee = Employee.objects.filter(badge_id=id).first()
                            managers.append(employee)
                        else:
                            error_ids.append(id)
                            is_save = False
                    if error_ids:
                        ids = ",".join(map(str, error_ids))
                        project["Manager error"] = f"{ids} - This id not exists"
                    # if Employee.objects.filter(badge_id=manager_badge_id).exists():
                    #     manager = Employee.objects.filter(
                    #         badge_id=manager_badge_id
                    #     ).first()
                    # else:
                    #     project["Manager error"] = (
                    #         f"{manager_badge_id} - This badge not exist"
                    #     )
                    #     is_save = False

                # getting employee using badge id, for member
                if member_badge_id:
                    ids = member_badge_id.split(",")
                    error_ids = []
                    employees = []
                    for id in ids:
                        if Employee.objects.filter(badge_id=id).exists():
                            employee = Employee.objects.filter(badge_id=id).first()
                            employees.append(employee)
                        else:
                            error_ids.append(id)
                            is_save = False
                    if error_ids:
                        ids = ",".join(map(str, error_ids))
                        project["Member error"] = f"{ids} - This id not exists"

                if status:
                    if status not in [stat for stat, _ in Project.PROJECT_STATUS]:
                        project["Status error"] = (
                            f"{status} not available in Project status"
                        )
                        is_save = False
                else:
                    project["Status error"] = "Status is a required field"
                    is_save = False

                format = "%Y-%m-%d"
                if start_date:

                    # using try-except to check for truth value
                    try:
                        res = bool(
                            datetime.datetime.strptime(
                                start_date.strftime("%Y-%m-%d"), format
                            )
                        )
                    except Exception as e:
                        res = False
                    if res == False:
                        project["Start date error"] = (
                            "Date must be in 'YYYY-MM-DD' format"
                        )
                        is_save = False
                else:
                    project["Start date error"] = "Start date is a required field"
                    is_save = False

                if end_date:
                    # using try-except to check for truth value
                    try:
                        res = bool(
                            datetime.datetime.strptime(
                                end_date.strftime("%Y-%m-%d"), format
                            )
                        )
                        if end_date < start_date:
                            project["end date error"] = (
                                "End date must be greater than Start date"
                            )
                            is_save = False
                    except ValueError:
                        res = False
                    if res == False:
                        project["end date error"] = (
                            "Date must be in 'YYYY-MM-DD' format"
                        )
                        is_save = False

                if is_save == True:
                    # creating new project
                    if Project.objects.filter(title=title).exists():
                        project_obj = Project.objects.filter(title=title).first()
                    else:
                        project_obj = Project(title=title)
                    project_obj.start_date = start_date.strftime("%Y-%m-%d")
                    project_obj.end_date = end_date.strftime("%Y-%m-%d")
                    project_obj.status = status
                    project_obj.description = description
                    project_obj.save()
                    for manager in managers:
                        project_obj.managers.add(manager)
                    project_obj.save()
                    for member in employees:
                        project_obj.members.add(member)
                    project_obj.save()
                else:
                    error_lists.append(project)

            except Exception as e:
                error_lists.append(project)
        if error_lists:
            res = defaultdict(list)
            for sub in error_lists:
                for key in sub:
                    res[key].append(sub[key])
            data_frame = pd.DataFrame(error_lists, columns=error_lists[0].keys())
            # Create an HTTP response object with the Excel file
            response = HttpResponse(content_type="application/ms-excel")
            response["Content-Disposition"] = 'attachment; filename="ImportError.xlsx"'
            data_frame.to_excel(response, index=False)
            return response
        return HttpResponse("Imported successfully")
    return response


@login_required
# @permission_required("employee.delete_employee")
# @require_http_methods(["POST"])
def project_bulk_export(request):
    """
    This method is used to export bulk of Project instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    data_list = []
    # Add headers to the worksheet
    headers = [
        "Title",
        "Managers",
        "Members",
        "Status",
        "Start Date",
        "End Date",
        "Description",
    ]

    # Get the list of field names for your model
    for project_id in ids:
        project = Project.objects.get(id=project_id)
        data = {
            "Title": f"{project.title}",
            "Managers": f"{',' .join([manager.employee_first_name + ' ' + manager.employee_last_name for manager in project.managers.all()]) if project.managers.exists() else ''}",
            "Members": f"{',' .join([member.employee_first_name + ' ' + member.employee_last_name for member in project.members.all()]) if project.members.exists() else ''}",
            "Status": f"{project.status}",
            "Start Date": f'{project.start_date.strftime("%Y-%m-%d")}',
            "End Date": f'{project.end_date.strftime("%Y-%m-%d") if project.end_date else ""}',
            "Description": f"{project.description}",
        }
        data_list.append(data)
    data_frame = pd.DataFrame(data_list, columns=headers)
    # Export the DataFrame to an Excel file
    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="project details.xlsx"'
    writer = pd.ExcelWriter(response, engine="xlsxwriter")
    # data_frame.to_excel(response, index=False)
    data_frame.to_excel(
        writer,
        sheet_name="Project details",
        index=False,
        startrow=3,
    )
    workbook = writer.book
    worksheet = writer.sheets["Project details"]
    max_columns = len(data)
    heading_format = workbook.add_format(
        {
            "bg_color": "#ffd0cc",
            "bold": True,
            "font_size": 14,
            "align": "center",
            "valign": "vcenter",
            "font_size": 20,
        }
    )
    header_format = workbook.add_format(
        {
            "bg_color": "#EDF1FF",
            "bold": True,
            "text_wrap": True,
            "font_size": 12,
            "align": "center",
            "border": 1,
        }
    )
    worksheet.set_row(0, 30)
    worksheet.merge_range(
        0,
        0,
        0,
        max_columns - 1,
        "Project details ",
        heading_format,
    )
    for col_num, value in enumerate(data_frame.columns.values):
        worksheet.write(3, col_num, value, header_format)
        col_letter = chr(65 + col_num)
        header_width = max(len(value) + 2, len(data_frame[value].astype(str).max()) + 2)
        worksheet.set_column(f"{col_letter}:{col_letter}", header_width)

    # worksheet.set_row(4, 30)

    writer.close()

    return response


@login_required
# @project_delete_permission
def project_bulk_archive(request):
    """
    This method is used to archive bulk of Project instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for project_id in ids:
        project = Project.objects.filter(id=project_id).first()
        if project and is_project_manager_or_super_user(request, project):
            is_active = eval(request.GET.get("is_active"))
            message = "Archived"
            if is_active:
                message = "Un-Archived"
            project.is_active = is_active
            project.save()
            messages.success(request, f"{project} is {message} successfully.")
    return JsonResponse({"message": "Success"})


@login_required
# @permission_required("employee.delete_employee")
def project_bulk_delete(request):
    """
    This method is used to delete set of Employee instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    del_id = []
    for project_id in ids:
        project = Project.objects.get(id=project_id)
        try:
            if is_project_manager_or_super_user(request, project):
                project.delete()
                del_id.append(project)
        except Exception as error:
            messages.error(request, error)
            messages.error(
                request, _("You cannot delete %(project)s.") % {"project": project}
            )
    messages.success(request, _("{} Projects deleted".format(len(del_id))))
    return JsonResponse({"message": "Success"})


@login_required
@project_delete_permission()
def project_archive(request, project_id):
    """
    This method is used to archive project instance
    Args:
            project_id : Project instance id
    """
    project = Project.objects.get(id=project_id)
    project.is_active = not project.is_active
    project.save()
    message = _(f"{project} Un-Archived successfully.")
    if not project.is_active:
        message = _(f"{project} Archived successfully.")
    messages.success(request, message)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


# Task views


@login_required
@project_update_permission()
def task_view(request, project_id, **kwargs):
    """
    For showing tasks
    """
    form = TaskAllFilter()
    view_type = "card"
    project = Project.objects.get(id=project_id)
    stages = ProjectStage.objects.filter(project=project).order_by("sequence")
    tasks = Task.objects.filter(project=project)
    form.form.fields["stage"].queryset = ProjectStage.objects.filter(project=project.id)
    if request.GET.get("view") == "list":
        view_type = "list"
    context = {
        "view_type": view_type,
        "tasks": tasks,
        "stages": stages,
        "project_id": project_id,
        "project": project,
        "today": datetime.datetime.today().date(),
        "f": form,
    }
    return render(request, "task/new/overall.html", context)


@login_required
@hx_request_required
def quick_create_task(request, stage_id):
    project_stage = ProjectStage.objects.get(id=stage_id)
    hx_target = request.META.get("HTTP_HX_TARGET")
    if (
        request.user.employee_get in project_stage.project.managers.all()
        or request.user.has_perm("project.add_task")
    ):
        form = QuickTaskForm(
            initial={
                "stage": project_stage,
                "project": project_stage.project,
                "end_date": project_stage.project.end_date,
            }
        )
        if request.method == "POST":
            form = QuickTaskForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _("The task has been created successfully!"))
                return HttpResponse(
                    f"<span hx-get='/project/task-filter/{project_stage.project.id}/?view=card' hx-trigger='load' hx-target='#viewContainer'></span>"
                )
        return render(
            request,
            "task/new/forms/quick_create_task_form.html",
            context={
                "form": form,
                "stage_id": stage_id,
                "project_id": project_stage.project.id,
                "hx_target": hx_target,
            },
        )
    messages.info(request, "You dont have permission.")
    return HttpResponse("<script>window.location.reload()</script>")


@login_required
def create_task(request, stage_id):
    """
    For creating new task in project view
    """
    project_stage = ProjectStage.objects.get(id=stage_id)
    project = project_stage.project
    if request.user.employee_get in project.managers.all() or request.user.has_perm(
        "project.delete_project"
    ):
        form = TaskForm(initial={"project": project})
        if request.method == "POST":
            form = TaskForm(request.POST, request.FILES)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.stage = project_stage
                instance.save()

                messages.success(request, _("New task created"))
                response = render(
                    request,
                    "task/new/forms/create_task.html",
                    context={"form": form, "stage_id": stage_id},
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )
        return render(
            request,
            "task/new/forms/create_task.html",
            context={"form": form, "stage_id": stage_id},
        )
    messages.info(request, "You dont have permission.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def create_task_in_project(request, project_id):
    """
    For creating new task in project view
    """
    project = Project.objects.get(id=project_id)
    stages = project.project_stages.all()

    # Serialize the queryset to JSON

    serialized_data = serializers.serialize("json", stages)
    if request.user.employee_get in project.managers.all() or request.user.has_perm(
        "project.delete_project"
    ):
        form = TaskFormCreate(initial={"project": project})
        if request.method == "POST":
            form = TaskFormCreate(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, _("New task created"))
                response = render(
                    request,
                    "task/new/forms/create_task_project.html",
                    context={"form": form, "project_id": project_id},
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )
        context = {
            "form": form,
            "project_id": project_id,
            "stages": serialized_data,
        }
        return render(
            request, "task/new/forms/create_task_project.html", context=context
        )
    messages.info(request, "You dont have permission.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@task_update_permission()
def update_task(request, task_id):
    """
    For updating task in project view
    """

    task = Task.objects.get(id=task_id)
    project = task.project
    task_form = TaskForm(instance=task)
    if request.method == "POST":
        task_form = TaskForm(request.POST, request.FILES, instance=task)
        if task_form.is_valid():
            task_form.save()
            messages.success(request, _("Task updated"))
            response = render(
                request,
                "task/new/forms/update_task.html",
                {"form": task_form, "task_id": task_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "task/new/forms/update_task.html",
        {
            "form": task_form,
            "task_id": task_id,
        },
    )


@login_required
@task_delete_permission()
def delete_task(request, task_id):
    """
    For delete task
    """
    view_type = request.GET.get("view")
    path = urlparse(request.META["HTTP_REFERER"]).path
    url_after_project = path.split("project/")[1].rstrip("/")
    # Split into components
    parts = url_after_project.split("/")
    view_name = parts[0]
    object_id = parts[1] if len(parts) > 1 else None

    if not view_name == "task-all":
        task_view_url = reverse(view_name, kwargs={"project_id": object_id})
    else:
        task_view_url = reverse("task-all")
    redirected_url = f"{task_view_url}?view={view_type}"
    task = Task.objects.get(id=task_id)
    project_id = task.project.id
    task.delete()
    messages.success(request, _("The task has been deleted successfully."))
    if request.META.get("HTTP_HX_REQUEST"):
        return HttpResponse(
            f"<span hx-get='/project/task-filter/{project_id}/?view={view_type}' hx-trigger='load' hx-target='#viewContainer'></span>"
        )
    return redirect(redirected_url)


@login_required
def task_details(request, task_id):
    """
    For showing all details about task
    """
    task = Task.objects.get(id=task_id)
    return render(request, "task/new/task_details.html", context={"task": task})


@login_required
@project_update_permission()
def task_filter(request, project_id):
    """
    For filtering task
    """
    templete = "task/new/task_kanban_view.html"
    if request.GET.get("view") == "list":
        templete = "task/new/task_list_view.html"
    tasks = TaskFilter(request.GET).qs.filter(project_id=project_id)
    stages = (
        ProjectStage.objects.filter(project_id=project_id).order_by("sequence")
        # if len(request.GET) == 0 or len(request.GET) == 1
        # else ProjectStage.objects.filter(tasks__in=tasks)
        # .distinct()
        # .order_by("sequence")
    )
    previous_data = request.environ["QUERY_STRING"]
    data_dict = parse_qs(previous_data)
    get_key_instances(Task, data_dict)
    if data_dict.get("project"):
        del data_dict["project"]
    context = {
        "tasks": tasks.distinct(),
        "stages": stages,
        "pd": request.GET.urlencode(),
        "project_id": project_id,
        "filter_dict": data_dict,
    }
    return render(request, templete, context)


@login_required
def task_stage_change(request):
    """
    This method is used to change the current stage of a task
    """
    task_id = request.POST["task"]
    stage_id = request.POST["stage"]
    stage = ProjectStage.objects.get(id=stage_id)
    Task.objects.filter(id=task_id).update(stage=stage)
    return JsonResponse(
        {
            "type": "success",
            "message": _("Task stage updated"),
        }
    )


@login_required
def task_timesheet(request, task_id):
    """
    For showing all timesheet related to task
    """
    task = Task.objects.get(id=task_id)
    time_sheets = task.task_timesheet.all()
    context = {"time_sheets": time_sheets, "task_id": task_id}
    return render(
        request,
        "task/new/task_timesheet.html",
        context=context,
    )


@login_required
def create_timesheet_task(request, task_id):
    task = Task.objects.get(id=task_id)
    project = task.project
    form = TimesheetInTaskForm(initial={"project_id": project, "task_id": task})
    if request.method == "POST":
        form = TimesheetInTaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Timesheet created"))
            response = render(
                request,
                "task/new/forms/create_timesheet.html",
                {"form": form, "task_id": task_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    context = {
        "form": form,
        "task_id": task_id,
    }
    return render(request, "task/new/forms/create_timesheet.html", context=context)


@login_required
def update_timesheet_task(request, timesheet_id):
    timesheet = TimeSheet.objects.get(id=timesheet_id)
    form = TimesheetInTaskForm(instance=timesheet)
    if request.method == "POST":
        form = TimesheetInTaskForm(request.POST, instance=timesheet)
        if form.is_valid():
            form.save()
            messages.success(request, _("Timesheet updated"))
            response = render(
                request,
                "task/new/forms/update_timesheet.html",
                {"form": form, "timesheet_id": timesheet_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    context = {
        "form": form,
        "timesheet_id": timesheet_id,
    }
    return render(request, "task/new/forms/update_timesheet.html", context=context)


@login_required
def drag_and_drop_task(request):
    """
    For drag and drop task into new stage
    """
    updated_stage_id = request.POST["updated_stage_id"]
    previous_task_id = request.POST["previous_task_id"]
    previous_stage_id = request.POST["previous_stage_id"]
    change = False
    task = Task.objects.get(id=previous_task_id)
    project = task.project
    if (
        request.user.has_perm("project.change_task")
        or request.user.has_perm("project.change_project")
        or request.user.employee_get in task.task_managers.all()
        or request.user.employee_get in task.task_members.all()
        or request.user.employee_get in project.managers.all()
        or request.user.employee_get in project.members.all()
    ):
        if previous_stage_id != updated_stage_id:
            task.stage = ProjectStage.objects.get(id=updated_stage_id)
            task.save()
            change = True
        sequence = json.loads(request.POST["sequence"])
        for key, val in sequence.items():
            if Task.objects.get(id=key).sequence != val:
                Task.objects.filter(id=key).update(sequence=val)
                change = True
        message = (
            _("Task stage has been successfully updated.")
            if previous_stage_id != updated_stage_id
            else _("Tasks order has been successfully updated.")
        )
        messages.success(request, message)
        return JsonResponse({"change": change})
    change = True
    messages.info(request, _("You dont have permission."))
    return JsonResponse({"change": change})


# Task all views


@login_required
def task_all(request):
    """
    For showing all task
    """
    form = TaskAllFilter()
    view_type = "card"
    tasks = TaskAllFilter(request.GET).qs
    if request.GET.get("view") == "list":
        view_type = "list"
    context = {
        "tasks": paginator_qry(tasks, request.GET.get("page")),
        "pd": request.GET.urlencode(),
        "f": form,
        "view_type": view_type,
    }
    return render(request, "task_all/task_all_overall.html", context=context)


@login_required
def task_all_create(request):
    """
    For creating new task in task all view
    """
    form = TaskAllForm()
    if request.method == "POST":
        form = TaskAllForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("New task created"))
            response = render(
                request,
                "task_all/forms/create_taskall.html",
                context={
                    "form": form,
                },
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "task_all/forms/create_taskall.html",
        context={
            "form": form,
        },
    )


@login_required
def update_project_task_status(request, task_id):
    status = request.GET.get("status")

    task = get_object_or_404(Task, id=task_id)
    task.status = status
    task.save()

    messages.success(request, _("Task status has been updated successfully"))
    return HttpResponse("<script>$('#reloadMessagesButton').click();</script>")


@login_required
def update_task_all(request, task_id):
    task = Task.objects.get(id=task_id)
    form = TaskAllForm(instance=task)
    if request.method == "POST":
        form = TaskAllForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save()
            messages.success(request, _("Task updated successfully"))
            response = render(
                request,
                "task_all/forms/update_taskall.html",
                context={"form": form, "task_id": task_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "task_all/forms/update_taskall.html",
        context={"form": form, "task_id": task_id},
    )


@login_required
def task_all_filter(request):
    """
    For filtering tasks in task all view
    """
    view_type = "card"
    templete = "task_all/task_all_card.html"
    if request.GET.get("view") == "list":
        view_type = "list"
        templete = "task_all/task_all_list.html"

    tasks = TaskAllFilter(request.GET).qs
    page_number = request.GET.get("page")
    previous_data = request.environ["QUERY_STRING"]
    data_dict = parse_qs(previous_data)
    get_key_instances(Task, data_dict)
    # tasks = tasks.filter(project_id=project_id)

    context = {
        "tasks": paginator_qry(tasks, page_number),
        "view_type": view_type,
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, templete, context)


@login_required
# @permission_required("employee.delete_employee")
# @require_http_methods(["POST"])
def task_all_bulk_archive(request):
    """
    This method is used to archive bulk of Task instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = False
    if request.GET.get("is_active") == "True":
        is_active = True
    for task_id in ids:
        task = Task.objects.get(id=task_id)
        task.is_active = is_active
        task.save()
        message = _("archived")
        if is_active:
            message = _("un-archived")
        messages.success(request, f"{task} is {message}")
    return JsonResponse({"message": "Success"})


@login_required
# @permission_required("employee.delete_employee")
def task_all_bulk_delete(request):
    """
    This method is used to delete set of Task instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    del_ids = []
    for task_id in ids:
        task = Task.objects.get(id=task_id)
        try:
            task.delete()
            del_ids.append(task)
        except Exception as error:
            messages.error(request, error)
            messages.error(request, _("You cannot delete %(task)s.") % {"task": task})
    messages.success(request, _("{} tasks.".format(len(del_ids))))
    return JsonResponse({"message": "Success"})


@login_required
# @permission_required("employee.delete_employee")
def task_all_archive(request, task_id):
    """
    This method is used to archive project instance
    Args:
            task_id : Task instance id
    """
    task = Task.objects.get(id=task_id)
    task.is_active = not task.is_active
    task.save()
    message = _(f"{task} un-archived")
    if not task.is_active:
        message = _(f"{task} archived")
    messages.success(request, message)
    # return HttpResponse("<script>$('.oh-btn--view').click();</script>")
    # return HttpResponse("<script>$('#hiddenbutton').click();</script>")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


# Project stage views
@login_required
@project_delete_permission()
@hx_request_required
def create_project_stage(request, project_id):
    """
    For create project stage
    """
    project = Project.objects.get(id=project_id)
    form = ProjectStageForm(initial={"project": project})
    if request.method == "POST":
        form = ProjectStageForm(
            request.POST,
        )
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            context = {"form": form, "project_id": project_id}

            messages.success(request, _("New project stage created"))
            response = render(
                request,
                "project_stage/forms/create_project_stage.html",
                context,
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    context = {"form": form, "project_id": project_id}
    return render(request, "project_stage/forms/create_project_stage.html", context)


@login_required
@project_stage_update_permission()
def update_project_stage(request, stage_id):
    """
    For update project stage
    """
    stage = ProjectStage.objects.get(id=stage_id)
    form = ProjectStageForm(instance=stage)
    if request.method == "POST":
        form = ProjectStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, _("Project stage updated successfully"))
            response = render(
                request,
                "project_stage/forms/update_project_stage.html",
                context={"form": form, "stage_id": stage_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "project_stage/forms/update_project_stage.html",
        context={"form": form, "stage_id": stage_id},
    )


@login_required
@project_stage_delete_permission()
def delete_project_stage(request, stage_id):
    """
    For delete project stage
    """
    view_type = request.GET.get("view")
    stage = ProjectStage.objects.get(id=stage_id)
    tasks = Task.objects.filter(stage=stage)
    project_id = stage.project.id
    if not tasks:
        stage.delete()
        messages.success(request, _("Stage deleted successfully"))
    else:
        messages.warning(request, _("Can't Delete. This stage contain some tasks"))
    if request.META.get("HTTP_HX_REQUEST"):
        return HttpResponse(
            f"<span hx-get='/project/task-filter/{project_id}/?view={view_type}' hx-trigger='load' hx-target='#viewContainer'></span>"
        )
    task_view_url = reverse("task-view", args=[project_id])
    redirected_url = f"{task_view_url}?view={view_type}"

    return redirect(redirected_url)


@login_required
def get_stages(request):
    """
    This is an ajax method to return json response to take only stages related
    to the project in the task-all form fields
    """
    project_id = request.GET.get("project_id")
    form = TaskAllForm()
    form.fields["stage"].choices = []
    if project_id:
        stages = ProjectStage.objects.filter(project=project_id)
        form.fields["stage"].choices = (
            [("", _("Select Stage"))]
            + [(stage.id, stage.title) for stage in stages]
            + [("dynamic_create", _("Dynamic Create"))]
        )
        # project = Project.objects.filter(id = project_id).first()
        # if (
        #     request.user.is_superuser or
        #     request.user.employee_get in project.managers.all()
        # ):
        #     form.fields['stage'].choices.append(('dynamic_create','Dynamic create'))
    return render(
        request, "cbv/tasks/task_form.html", {"request": request, "form": form}
    )


@login_required
def create_stage_taskall(request):
    """
    This is an ajax method to return json response to create stage related
    to the project in the task-all form fields
    """
    if request.method == "GET":
        project_id = request.GET["project_id"]
        project = Project.objects.get(id=project_id)
        form = ProjectStageForm(initial={"project": project})
    if request.method == "POST":
        form = ProjectStageForm(request.POST)
        if form.is_valid():
            instance = form.save()
            return JsonResponse({"id": instance.id, "name": instance.title})
        errors = form.errors.as_json()
        return JsonResponse({"errors": errors})
    return render(
        request,
        "task_all/forms/create_project_stage_taskall.html",
        context={"form": form},
    )


@login_required
def drag_and_drop_stage(request):
    """
    For drag and drop project stage into new sequence
    """
    sequence = request.POST["sequence"]
    sequence = json.loads(sequence)
    stage_id = list(sequence.keys())[0]
    project = ProjectStage.objects.get(id=stage_id).project
    change = False
    if (
        request.user.has_perm("project.change_project")
        or request.user.employee_get in project.managers.all()
        or request.user.employee_get in project.members.all()
    ):
        for key, val in sequence.items():
            if val != ProjectStage.objects.get(id=key).sequence:
                change = True
                ProjectStage.objects.filter(id=key).update(sequence=val)
        if change:
            messages.success(
                request, _("The project stage sequence has been successfully updated.")
            )
        return JsonResponse(
            {
                "change": change,
            }
        )
    messages.warning(request, _("You don't have permission."))
    return JsonResponse({"type": change})


# Time sheet views


# @permission_required(perm='project.view_timesheet')
@login_required
def time_sheet_view(request):
    """
    View function to display time sheets based on user permissions.

    If the user is a superuser, all time sheets will be shown.
    Otherwise, only the time sheets for the current user will be displayed.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered HTTP response displaying the time sheets.
    """
    form = TimeSheetFilter()
    view_type = "card"
    if request.GET.get("view") == "list":
        view_type = "list"
    time_sheet_filter = TimeSheetFilter(request.GET).qs
    time_sheet_filter = filtersubordinates(
        request, time_sheet_filter, "project.view_timesheet"
    )
    time_sheet_filter = list(time_sheet_filter)
    for item in TimeSheet.objects.filter(employee_id=request.user.employee_get):
        if item not in time_sheet_filter:
            time_sheet_filter.append(item)

    time_sheets = paginator_qry(time_sheet_filter, request.GET.get("page"))
    context = {"time_sheets": time_sheets, "f": form, "view_type": view_type}
    return render(
        request,
        "time_sheet/time_sheet_view.html",
        context=context,
    )


def time_sheet_initial(request):
    """
    This is an ajax method to return json response to take only tasks related
    to the project in the timesheet form fields
    """
    project_id = request.GET["project_id"]
    tasks = Task.objects.filter(project=project_id).values("title", "id")
    return JsonResponse({"data": list(tasks)})


# def get_members(request):
#     project_id = request.GET.get("project_id")
#     project = Project.objects.get(id=project_id)
#     user_employee = request.user.employee_get
#     members = project.members.all().values_list("employee_first_name", "id")
#     members = list(members)

#     # Include the user if not already a member
#     # if user_employee.id not in [member[1] for member in members]:
#     #     members.append((user_employee.first_name, user_employee.id))

#     return JsonResponse({'data': list(members)})


def get_members(request):
    project_id = request.GET.get("project_id")
    task_id = request.GET.get("task_id")
    form = TimeSheetForm()
    if project_id and task_id:
        if task_id != "dynamic_create" and project_id != "dynamic_create":
            project = Project.objects.filter(id=project_id).first()
            task = Task.objects.filter(id=task_id).first()
            employee = Employee.objects.filter(id=request.user.employee_get.id)
            if employee.first() in project.managers.all():
                members = (
                    employee
                    | project.members.all()
                    | task.task_managers.all()
                    | task.task_members.all()
                ).distinct()
            elif employee.first() in task.task_managers.all():
                members = (employee | task.task_members.all()).distinct()
            else:
                members = employee
            form.fields["employee_id"].queryset = members
    else:
        form.fields["employee_id"].queryset = Employee.objects.none()

    employee_field_html = render_to_string(
        "cbv/timesheet/employee_field.html",
        {
            "form": form,
            "field_name": "employee_id",
            "field": form.fields["employee_id"],
            "task_id": task_id,
            "project_id": project_id,
        },
    )
    return HttpResponse(employee_field_html)


def get_tasks_in_timesheet(request):
    project_id = request.GET.get("project_id")
    form = TimeSheetForm()
    if project_id and project_id != "dynamic_create":
        project = Project.objects.get(id=project_id)
        employee = request.user.employee_get
        all_tasks = Task.objects.filter(project=project)
        # ie the employee is a project manager return all tasks
        if (
            employee in project.managers.all()
            or employee in project.members.all()
            or request.user.has_perm("project.add_timesheet")
        ):
            tasks = all_tasks
        # if the employee is a task manager and task member
        elif (
            Task.objects.filter(project=project_id, task_managers=employee).exists()
            and Task.objects.filter(project=project_id, task_members=employee).exists()
        ):
            tasks = (
                Task.objects.filter(project=project_id, task_managers=employee)
                | Task.objects.filter(project=project_id, task_members=employee)
            ).distinct()
        # if the employee is manager of a task under the project
        elif Task.objects.filter(project=project_id, task_managers=employee).exists():
            tasks = Task.objects.filter(project=project_id, task_managers=employee)
        # if the employee ids a member of task under the project
        elif Task.objects.filter(project=project_id, task_members=employee).exists():
            tasks = Task.objects.filter(project=project_id, task_members=employee)
        form.fields["task_id"].queryset = tasks
        form.fields["task_id"].choices = list(form.fields["task_id"].choices)
        if employee in project.managers.all() or request.user.is_superuser:
            form.fields["task_id"].choices.append(("dynamic_create", "Dynamic create"))
        task_id = request.GET.get("task_id")
        if task_id:
            form.fields["task_id"].initial = task_id
    else:
        form.fields["task_id"].queryset = Task.objects.none()

    task_field_html = render_to_string(
        "cbv/timesheet/task_field.html",
        {
            "form": form,
            "field_name": "task_id",
            "field": form.fields["task_id"],
        },
    )
    return HttpResponse(task_field_html)


@login_required
def time_sheet_creation(request):
    """
    View function to handle the creation of a new time sheet.

    If the request method is POST and the submitted form is valid,
    a new time sheet will be created and saved.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered HTTP response displaying the form or
        redirecting to a new page after successful time sheet creation.
    """
    user = request.user.employee_get
    form = TimeSheetForm(initial={"employee_id": user}, request=request)
    # form = TimeSheetForm(initial={"employee_id": user})
    if request.method == "POST":
        form = TimeSheetForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, _("Time sheet created"))
            response = render(
                request, "time_sheet/form-create.html", context={"form": form}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "time_sheet/form-create.html", context={"form": form})


@login_required
def time_sheet_project_creation(request):
    """
    View function to handle the creation of a new project from time sheet form.

    If the request method is POST and the submitted form is valid,
    a new project will be created and saved.

    Returns:
        HttpResponse or JsonResponse: Depending on the request type, it returns
        either an HTTP response rendering the form or a JSON response with the
        created project ID and name in case of successful creation,
        or the validation errors in case of an invalid form submission.
    """
    form = ProjectTimeSheetForm()
    if request.method == "POST":
        form = ProjectTimeSheetForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            return JsonResponse({"id": instance.id, "name": instance.title})
        errors = form.errors.as_json()
        return JsonResponse({"errors": errors})
    return render(
        request, "time_sheet/form_project_time_sheet.html", context={"form": form}
    )


@login_required
def time_sheet_task_creation(request):
    """
    View function to handle the creation of a new task from time sheet form.

    If the request method is GET, it initializes the task form with the
    provided project ID as an initial value.
    If the request method is POST and the submitted form is valid,
    a new task time sheet will be created and saved.

    Returns:
        HttpResponse or JsonResponse: Depending on the request type, it returns
        either an HTTP response rendering the form or a JSON response with the
        created task time sheet's ID and name in case of successful creation,
        or the validation errors in case of an invalid form submission.
    """
    if request.method == "GET":
        project_id = request.GET["project_id"]
        project = Project.objects.get(id=project_id)
        stages = ProjectStage.objects.filter(project__id=project_id)
        task_form = TaskTimeSheetForm(initial={"project": project})
        task_form.fields["stage"].queryset = stages

    if request.method == "POST":
        task_form = TaskTimeSheetForm(request.POST, request.FILES)
        if task_form.is_valid():
            instance = task_form.save()
            return JsonResponse({"id": instance.id, "name": instance.title})
        errors = task_form.errors.as_json()
        return JsonResponse({"errors": errors})
    return render(
        request,
        "time_sheet/form_task_time_sheet.html",
        context={"form": task_form, "project_id": project_id},
    )


@login_required
def time_sheet_update(request, time_sheet_id):
    """
    Update an existing time sheet.

    Args:
        request: The HTTP request object.
        time sheet_id: The ID of the time sheet to update.

    Returns:
        If the request method is POST and the form is valid, redirects to the time sheet view.
        Otherwise, renders the time sheet update form.

    """
    if time_sheet_update_permissions(request, time_sheet_id):
        time_sheet = TimeSheet.objects.get(id=time_sheet_id)
        update_form = TimeSheetForm(instance=time_sheet, request=request)
        update_form.fields["task_id"].queryset = time_sheet.project_id.task_set.all()

        if request.method == "POST":
            update_form = TimeSheetForm(request.POST, instance=time_sheet)

            if update_form.is_valid():
                update_form.save()
                messages.success(request, _("Time sheet updated"))
                form = TimeSheetForm()
                response = render(
                    request, "./time_sheet/form-create.html", context={"form": form}
                )
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )
        return render(
            request,
            "./time_sheet/form-update.html",
            {
                "form": update_form,
            },
        )
    else:
        return render(request, "error.html")


@login_required
def time_sheet_delete(request, time_sheet_id):
    """
    View function to handle the deletion of a time sheet.

    Parameters:
        request (HttpRequest): The HTTP request object.
        time_sheet_id (int): The ID of the time sheet to be deleted.

    Returns:
        HttpResponseRedirect: A redirect response to the time sheet view page.
    """
    if time_sheet_delete_permissions(request, time_sheet_id):
        TimeSheet.objects.get(id=time_sheet_id).delete()
        messages.success(request, _("The time sheet has been deleted successfully"))
        view_type = "card"
        if request.GET.get("view") == "list":
            view_type = "list"
        task_id = request.GET.get("task_id")
        if task_id:
            return redirect(f"/project/task-timesheet/{task_id}/")
        return redirect("/project/view-time-sheet" + "?view=" + view_type)
    else:
        return you_dont_have_permission(request)


def time_sheet_filter(request):
    """
    Filter Time sheet based on the provided query parameters.

    Args:
        request: The HTTP request object containing the query parameters.

    Returns:
        Renders the Time sheet list template with the filtered Time sheet.

    """
    emp_id = request.user.employee_get.id
    filtered_time_sheet = TimeSheetFilter(request.GET).qs

    time_sheet_filter = filtersubordinates(
        request, filtered_time_sheet, "project.view_timesheet"
    )
    if filtered_time_sheet.filter(employee_id__id=emp_id).exists():
        time_sheet_filter = list(time_sheet_filter)
        for item in TimeSheet.objects.filter(employee_id=request.user.employee_get):
            if item not in time_sheet_filter:
                time_sheet_filter.append(item)
    time_sheets = paginator_qry(time_sheet_filter, request.GET.get("page"))
    previous_data = request.environ["QUERY_STRING"]
    data_dict = parse_qs(previous_data)
    get_key_instances(TimeSheet, data_dict)
    view_type = request.GET.get("view")
    template = "time_sheet/time_sheet_list_view.html"
    if view_type == "card":
        template = "time_sheet/time_sheet_card_view.html"
    elif view_type == "chart":
        return redirect("personal-time-sheet-view" + "?view=" + emp_id)
    return render(
        request,
        template,
        {
            "time_sheets": time_sheets,
            "filter_dict": data_dict,
        },
    )


@login_required
def time_sheet_initial(request):
    """
    This is an ajax method to return json response to take only tasks related
    to the project in the timesheet form fields
    """
    project_id = request.GET["project_id"]
    tasks = Task.objects.filter(project=project_id).values("title", "id")
    return JsonResponse({"data": list(tasks)})


def personal_time_sheet(request):
    """
    This is an ajax method to return json response for generating bar charts to employees.
    """
    emp_id = request.GET["emp_id"]
    selected = request.GET["selected"]
    month_number = request.GET["month"]
    year = request.GET["year"]
    week_number = request.GET["week"]

    time_spent = []
    dataset = []

    projects = Project.objects.filter(project_timesheet__employee_id=emp_id).distinct()

    time_sheets = TimeSheet.objects.filter(employee_id=emp_id).order_by("date")

    time_sheets = time_sheets.filter(date__week=week_number)

    # check for labels to be genarated weeky or monthly
    if selected == "week":
        start_date = datetime.date.fromisocalendar(int(year), int(week_number), 1)

        date_list = []
        labels = []
        for i in range(7):
            day = start_date + datetime.timedelta(days=i)
            date_list.append(day)
            day = day.strftime("%d-%m-%Y %A")
            labels.append(day)

    elif selected == "month":
        days_in_month = calendar.monthrange(int(year), int(month_number) + 1)[1]
        start_date = datetime.datetime(int(year), int(month_number) + 1, 1).date()
        labels = []
        date_list = []
        for i in range(days_in_month):
            day = start_date + datetime.timedelta(days=i)
            date_list.append(day)
            day = day.strftime("%d-%m-%Y")
            labels.append(day)
    colors = generate_colors(len(projects))

    for project, color in zip(projects, colors):
        dataset.append(
            {
                "label": project.title,
                "data": [],
                "backgroundColor": color,
            }
        )

    # Calculate total hours for each project on each date
    total_hours_by_project_and_date = defaultdict(lambda: defaultdict(float))

    # addding values to the response
    for label in date_list:
        time_sheets = TimeSheet.objects.filter(employee_id=emp_id, date=label)
        for time in time_sheets:
            time_spent = strtime_seconds(time.time_spent) / 3600
            total_hours_by_project_and_date[time.project_id.title][label] += time_spent
    for data in dataset:
        project_title = data["label"]
        data["data"] = [
            total_hours_by_project_and_date[project_title][label] for label in date_list
        ]

    response = {
        "dataSet": dataset,
        "labels": labels,
    }
    return JsonResponse(response)


def personal_time_sheet_view(request, emp_id):
    """
    Function for viewing the barcharts for timesheet of a specific employee.

    Args:
        emp_id: id of the employee whose barchat to be rendered.

    Returns:
        Renders the chart.html template containing barchat of the specific employee.

    """
    try:
        Employee.objects.get(id=emp_id)
    except:
        return render(request, "error.html")
    emp_last_name = (
        Employee.objects.get(id=emp_id).employee_last_name
        if Employee.objects.get(id=emp_id).employee_last_name != None
        else ""
    )
    employee_name = (
        f"{Employee.objects.get(id=emp_id).employee_first_name}  {emp_last_name}"
    )
    context = {
        "emp_id": emp_id,
        "emp_name": employee_name,
    }

    return render(request, "time_sheet/chart.html", context=context)


def time_sheet_single_view(request, time_sheet_id):
    """
    Renders a single timesheet view page.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - time_sheet_id (int): The ID of the timesheet to view.

    Returns:
        The rendered timesheet single view page.

    """
    timesheet = TimeSheet.objects.get(id=time_sheet_id)
    context = {"time_sheet": timesheet}
    return render(request, "time_sheet/time_sheet_single_view.html", context)


def time_sheet_bulk_delete(request):
    """
    This method is used to delete set of Task instances
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for timesheet_id in ids:
        timesheet = TimeSheet.objects.get(id=timesheet_id)
        try:
            timesheet.delete()
            messages.success(
                request, _("%(timesheet)s deleted.") % {"timesheet": timesheet}
            )
        except Exception as error:
            messages.error(request, error)
            messages.error(
                request,
                _("You cannot delete %(timesheet)s.") % {"timesheet": timesheet},
            )
    return JsonResponse({"message": "Success"})
