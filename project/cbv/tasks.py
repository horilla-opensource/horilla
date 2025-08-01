"""
This page handles the cbv methods for task page
"""

import logging
from typing import Any

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from base.methods import get_subordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from project.cbv.project_stage import StageDynamicCreateForm
from project.cbv.projects import DynamicProjectCreationFormView
from project.filters import TaskAllFilter
from project.forms import TaskAllForm
from project.methods import you_dont_have_permission
from project.models import Project, ProjectStage, Task
from project.templatetags.taskfilters import task_crud_perm

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class TasksTemplateView(TemplateView):
    """
    view page of the task page
    """

    template_name = "cbv/tasks/task_template_view.html"


@method_decorator(login_required, name="dispatch")
class TaskListView(HorillaListView):
    """
    list view of the page
    """

    model = Task
    filter_class = TaskAllFilter
    action_method = "actions"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "task-list-container"
        self.search_url = reverse("tasks-list-view")

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_task"):
            employee_id = self.request.user.employee_get
            subordinates = get_subordinates(self.request)
            subordinate_ids = [subordinate.id for subordinate in subordinates]
            project = queryset.filter(
                Q(project__managers=employee_id)
                | Q(project__members=employee_id)
                | Q(project__managers__in=subordinate_ids)
                | Q(project__members__in=subordinate_ids)
            )
            queryset = (
                queryset.filter(
                    Q(task_members=employee_id)
                    | Q(task_managers=employee_id)
                    | Q(task_members__in=subordinate_ids)
                    | Q(task_managers__in=subordinate_ids)
                )
                | project
            )
        return queryset.distinct()

    @cached_property
    def columns(self):
        get_field = self.model()._meta.get_field
        return [
            (get_field("title").verbose_name, "title"),
            (get_field("project").verbose_name, "project"),
            (get_field("stage").verbose_name, "stage"),
            (get_field("task_managers").verbose_name, "get_managers"),
            (get_field("task_members").verbose_name, "get_members"),
            (get_field("end_date").verbose_name, "end_date"),
            (get_field("status").verbose_name, "get_status_display"),
            (get_field("description").verbose_name, "get_description"),
        ]

    @cached_property
    def sortby_mapping(self):
        get_field = self.model()._meta.get_field
        return [
            (get_field("title").verbose_name, "title"),
            (get_field("project").verbose_name, "project__title"),
            (get_field("stage").verbose_name, "stage"),
            (get_field("end_date").verbose_name, "end_date"),
            (get_field("status").verbose_name, "status"),
        ]

    row_status_indications = [
        (
            "todo--dot",
            _("To Do"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('to_do');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_progress');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "completed--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('completed');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "expired--dot",
            _("Expired"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('expired');
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    row_status_class = "status-{status}"

    row_attrs = """
                hx-get='{task_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
class TasksNavBar(HorillaNavView):
    """
    navbar of teh page
    """

    group_by_fields = [
        "project",
        "stage",
        "status",
    ]
    filter_form_context_name = "form"
    filter_instance = TaskAllFilter()
    search_swap_target = "#listContainer"
    filter_body_template = "cbv/tasks/task_filter.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        employee = self.request.user.employee_get
        projects = Project.objects.all()
        managers = [
            manager for project in projects for manager in project.managers.all()
        ]
        self.search_url = reverse("tasks-list-view")
        if employee in managers or self.request.user.has_perm("project.add_task"):
            self.create_attrs = f"""
                                    onclick = "event.stopPropagation();"
                                    data-toggle="oh-modal-toggle"
                                    data-target="#genericModal"
                                    hx-target="#genericModalBody"
                                    hx-get="{reverse('create-task-all')}"
                                    """

        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("tasks-list-view"),
                "attrs": """
                        title ='List'
                        """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("tasks-card-view"),
                "attrs": """
                          title ='Card'
                          """,
            },
        ]

        if self.request.user.has_perm("project.view_task"):
            self.actions = [
                {
                    "action": _("Archive"),
                    "attrs": """
                            id="archiveTask",
                            style="cursor: pointer;"
                            """,
                },
                {
                    "action": _("Un-Archive"),
                    "attrs": """
                            id="unArchiveTask",
                            style="cursor: pointer;"
                            """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                                class="oh-dropdown__link--danger"
                                data-action = "delete"
                                id="deleteTask"
                                style="cursor: pointer; color:red !important"

                                """,
                },
            ]


@method_decorator(login_required, name="dispatch")
class TaskCreateForm(HorillaFormView):
    """
    Form view for create and update tasks
    """

    model = Task
    form_class = TaskAllForm
    template_name = "cbv/tasks/task_form.html"
    new_display_title = _("Create") + " " + model._meta.verbose_name

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.request.user.has_perm("project.view_task"):
            self.dynamic_create_fields = [
                ("project", DynamicProjectCreationFormView),
                ("stage", StageDynamicCreateForm, ["project"]),
            ]

    def get(self, request, *args, pk=None, **kwargs):
        project_id = self.kwargs.get("project_id")
        stage_id = self.kwargs.get("stage_id")
        task_id = self.kwargs.get("pk")
        # try:
        if project_id:
            project = Project.objects.filter(id=project_id).first()
        elif stage_id:
            project = ProjectStage.objects.filter(id=stage_id).first().project
        elif task_id:
            task = Task.objects.filter(id=task_id).first()
            project = task.project
        elif not task_id:
            return super().get(request, *args, pk=pk, **kwargs)
        if (
            request.user.employee_get in project.managers.all()
            or request.user.is_superuser
            or request.user.has_perm("project.add_task")
        ):
            self.dynamic_create_fields = [
                ("project", DynamicProjectCreationFormView),
                ("stage", StageDynamicCreateForm),
            ]
            return super().get(request, *args, pk=pk, **kwargs)
        elif task_id:
            if request.user.employee_get in task.task_managers.all():
                return super().get(request, *args, pk=pk, **kwargs)

        else:
            return you_dont_have_permission(request)
        # except Exception as e:
        #     logger.error(e)
        #     messages.error(request, _("Something went wrong!"))
        #     return HttpResponse("<script>window.location.reload()</script>")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get("project_id")
        stage_id = self.kwargs.get("stage_id")
        task_id = self.kwargs.get("pk")

        dynamic_project_id = self.request.GET.get("dynamic_project")

        if dynamic_project_id and dynamic_project_id != "dynamic_create":
            stages = ProjectStage.objects.filter(project=dynamic_project_id)
            attrs = self.form.fields["stage"].widget.attrs
            attrs["style"] = "width:100% !important;"
            self.form.fields["stage"].choices = (
                [("", _("Select Stage"))]
                + [(stage.pk, stage) for stage in stages]
                + [("dynamic_create", _("Dynamic Create"))]
            )

        if task_id and not dynamic_project_id:
            task = self.form.instance
            stages = task.project.project_stages.all()
            self.form.fields["stage"].choices = (
                [("", _("Select Stage"))]
                + [(stage.pk, stage) for stage in stages]
                + [("dynamic_create", _("Dynamic Create"))]
            )

        if stage_id:
            stage = ProjectStage.objects.filter(id=stage_id).first()
            project = stage.project
            self.form.fields["stage"].initial = stage
            self.form.fields["stage"].choices = [(stage.id, stage.title)]
            self.form.fields["project"].initial = project
            self.form.fields["project"].choices = [(project.id, project.title)]
        elif project_id:
            project = Project.objects.get(id=project_id)
            self.form.fields["project"].initial = project
            self.form.fields["project"].choices = [(project.id, project.title)]
            stages = ProjectStage.objects.filter(project=project)
            self.form.fields["stage"].choices = [
                (stage.id, stage.title) for stage in stages
            ]
        elif self.form.instance.pk:
            self.form_class.verbose_name = _("Update Task")
            if self.request.GET.get("project_task"):
                self.form.fields["project"].widget = forms.HiddenInput()
                self.form.fields["stage"].widget = forms.HiddenInput()
        else:
            if self.request.user.is_superuser:
                self.dynamic_create_fields = [
                    ("project", DynamicProjectCreationFormView),
                    ("stage", StageDynamicCreateForm, ["project"]),
                ]

        if project_id or stage_id:
            if (
                self.request.user.employee_get in project.managers.all()
                or self.request.user.is_superuser
            ):

                self.form.fields["project"].choices.append(
                    ("dynamic_create", "Dynamic create")
                )
                self.form.fields["stage"].choices.append(
                    ("dynamic_create", "Dynamic create")
                )

        return context

    def form_valid(self, form: TaskAllForm) -> HttpResponse:
        stage_id = self.kwargs.get("stage_id")
        if form.is_valid():
            if form.instance.pk:
                message = _(f"{self.form.instance} Updated")
            else:
                message = _("New Task created")
            form.save()
            messages.success(self.request, _(message))
            if stage_id or self.request.GET.get("project_task"):
                return HttpResponse("<script>location.reload();</script>")
            return self.HttpResponse("<script>$('#taskFilterButton').click();</script>")
        return super().form_valid(form)


class DynamicTaskCreateFormView(TaskCreateForm):

    is_dynamic_create_view = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET:
            project_id = self.request.GET.get("project_id")
            if project_id:
                project = Project.objects.get(id=project_id)
                stages = ProjectStage.objects.filter(project__id=project_id)
                self.form.fields["project"].initial = project
                self.form.fields["project"].choices = [(project.id, project.title)]
                self.form.fields["stage"].queryset = stages
                # self.form.fields["project"].widget = forms.HiddenInput()
        return context


@method_decorator(login_required, name="dispatch")
class TaskDetailView(HorillaDetailedView):
    """
    detail view of the task page
    """

    model = Task
    title = _("Task Details")
    action_method = "detail_view_actions"
    header = {"title": "title", "subtitle": "project", "avatar": "get_avatar"}

    @cached_property
    def body(self):
        get_field = self.model()._meta.get_field
        return [
            (get_field("title").verbose_name, "title"),
            (get_field("project").verbose_name, "project"),
            (get_field("stage").verbose_name, "stage"),
            (get_field("task_managers").verbose_name, "get_managers"),
            (get_field("task_members").verbose_name, "get_members"),
            (get_field("status").verbose_name, "get_status_display"),
            (get_field("end_date").verbose_name, "end_date"),
            (get_field("description").verbose_name, "description"),
            (get_field("document").verbose_name, "document_col", True),
        ]


@method_decorator(login_required, name="dispatch")
class TaskCardView(HorillaCardView):
    """
    card view of the page
    """

    model = Task
    filter_class = TaskAllFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "task-card"
        self.search_url = reverse("tasks-card-view")
        self.actions = [
            {
                "action": _("Edit"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                        data-toggle = "oh-modal-toggle"
                        data-target = "#genericModal"
                        hx-target="#genericModalBody"
                        hx-get ='{get_update_url}'
                        class="oh-dropdown__link"
                        style="cursor: pointer;"
                        """,
            },
            {
                "action": _("archive_status"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                href="{get_archive_url}"
                        onclick="return confirm('Do you want to {archive_status} this task?')"
                        class="oh-dropdown__link"
                        """,
            },
            {
                "action": _("Delete"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                    onclick="
                                event.stopPropagation()
                                deleteItem({get_delete_url});
                                "
                    class="oh-dropdown__link oh-dropdown__link--danger"
                    """,
            },
        ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_task"):
            employee_id = self.request.user.employee_get
            subordinates = get_subordinates(self.request)
            subordinate_ids = [subordinate.id for subordinate in subordinates]
            project = queryset.filter(
                Q(project__managers=employee_id)
                | Q(project__members=employee_id)
                | Q(project__managers__in=subordinate_ids)
                | Q(project__members__in=subordinate_ids)
            )
            queryset = (
                queryset.filter(
                    Q(task_members=employee_id)
                    | Q(task_managers=employee_id)
                    | Q(task_members__in=subordinate_ids)
                    | Q(task_managers__in=subordinate_ids)
                )
                | project
            )
        return queryset.distinct()

    details = {
        "image_src": "get_avatar",
        "title": "{title}",
        "subtitle": "Project Name : {if_project} <br> Stage Name : {stage}<br> End Date : {end_date}",
    }

    card_attrs = """
                hx-get='{task_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    card_status_indications = [
        (
            "todo--dot",
            _("To Do"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('to_do');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_progress');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "completed--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('completed');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "expired--dot",
            _("Expired"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('expired');
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    card_status_class = "status-{status}"


class TasksInIndividualView(TaskListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        employee_id = self.request.GET.get("employee_id")
        self.row_attrs = f"""
                hx-get='{{task_detail_view}}?instance_ids={{ordered_ids}}&employee_id={employee_id}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        employee_id = self.request.GET.get("employee_id")
        project_id = self.request.GET.get("project_id")
        queryset = queryset.filter(
            Q(task_members=employee_id) | Q(task_manager=employee_id)
        )
        queryset = queryset.filter(project=project_id)
        return queryset

    row_status_indications = None
    bulk_select_option = None
    action_method = None
