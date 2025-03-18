"""
CBV of projects page
"""

from typing import Any

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from employee.cbv.employee_profile import EmployeeProfileView
from employee.models import Employee
from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from project.cbv.cbv_decorators import is_projectmanager_or_member_or_perms
from project.filters import ProjectFilter
from project.forms import ProjectForm
from project.methods import (
    any_project_manager,
    any_project_member,
    is_project_manager_or_super_user,
    you_dont_have_permission,
)
from project.models import Project


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_project"), name="dispatch"
)
class ProjectsView(TemplateView):
    """
    for projects page
    """

    template_name = "cbv/projects/projects.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_project"), name="dispatch"
)
class ProjectsNavView(HorillaNavView):
    """
    Nav bar
    """

    template_name = "cbv/projects/project_nav.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("project-list-view")
        # self.search_in = [
        #     ("status", _("Managers")),
        #     ("members", _("Members")),
        # ]
        if self.request.user.has_perm("project.view_project"):
            self.actions = [
                {
                    "action": _("Import"),
                    "attrs": """
                        id="importProject"
                        data-toggle="oh-modal-toggle"
                        data-target="#projectImport"
                        style="cursor: pointer;"
                        """,
                },
                {
                    "action": _("Export"),
                    "attrs": """
                        id="exportProject"
                        style="cursor: pointer;"
                        """,
                },
                {
                    "action": _("Archive"),
                    "attrs": """
                        id="archiveProject"
                        style="cursor: pointer;"
                        """,
                },
                {
                    "action": _("Un-archive"),
                    "attrs": """
                        id="unArchiveProject"
                        style="cursor: pointer;"
                        """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                        class="oh-dropdown__link--danger"
                        data-action ="delete"
                        id="deleteProject"
                        style="cursor: pointer; color:red !important"
                        """,
                },
            ]
        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("project-list-view"),
                "attrs": """
                        title ='List'
                        """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("project-card-view"),
                "attrs": """
                          title ='Card'
                          """,
            },
        ]
        if self.request.user.has_perm("project.add_project"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('create-project')}"
                                """

    group_by_fields = [
        ("status", _("Status")),
        ("is_active", _("Is active")),
    ]
    nav_title = _("Projects")
    filter_instance = ProjectFilter()
    filter_form_context_name = "form"
    filter_body_template = "cbv/projects/filter.html"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_project"), name="dispatch"
)
class ProjectsList(HorillaListView):
    """
    Projects list view
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_project"):
            employee = self.request.user.employee_get
            task_filter = queryset.filter(
                Q(task__task_members=employee) | Q(task__task_managers=employee)
            )
            project_filter = queryset.filter(Q(managers=employee) | Q(members=employee))
            queryset = task_filter | project_filter
        return queryset.distinct()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("project-list-view")
        if self.request.user.is_superuser:
            self.action_method = "actions"

    model = Project
    filter_class = ProjectFilter

    columns = [
        (_("Project"), "title"),
        (_("Project Managers"), "get_managers"),
        (_("Project Members"), "get_members"),
        (_("Status"), "status_column"),
        (_("Start Date"), "start_date"),
        (_("End Date"), "end_date"),
        (_("File"), "get_document_html"),
        (_("Description"), "get_description"),
    ]

    sortby_mapping = [
        ("Project", "title"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
    ]

    row_status_indications = [
        (
            "new--dot",
            _("New"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('new');
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
            "on-hold--dot",
            _("On Hold"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('on_hold');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "cancelled--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('cancelled');
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
                {redirect}
                """


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("project.add_project"), name="dispatch")
class ProjectFormView(HorillaFormView):
    """
    form view for create project
    """

    form_class = ProjectForm
    model = Project
    new_display_title = _("Create Project")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        user = self.request.user

        if not user.is_superuser and not user.has_perm("project.add_project"):
            self.template_name = "decorator_404.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update project")
        return context

    def form_valid(self, form: ProjectForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _(f"{self.form.instance} Updated")
                HTTP_REFERER = self.request.META.get("HTTP_REFERER", None)
                if HTTP_REFERER and "task-view/" in HTTP_REFERER:
                    form.save()
                    messages.success(self.request, message)
                    return self.HttpResponse(
                        "<script>window.location.reload()</script>"
                    )
            else:
                message = _("New project created")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)


class DynamicProjectCreationFormView(ProjectFormView):

    is_dynamic_create_view = True


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_project"), name="dispatch"
)
class ProjectCardView(HorillaCardView):
    """
    For card view
    """

    model = Project
    filter_class = ProjectFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_project"):
            employee = self.request.user.employee_get
            task_filter = queryset.filter(
                Q(task__task_members=employee) | Q(task__task_managers=employee)
            )
            project_filter = queryset.filter(Q(managers=employee) | Q(members=employee))
            queryset = task_filter | project_filter
        return queryset.distinct()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("project-card-view")
        if (
            self.request.user.has_perm("project.change_project")
            or self.request.user.has_perm("project.delete_project")
            or any_project_manager(self.request.user)
            or any_project_member(self.request.user)
        ):
            self.actions = [
                {
                    "action": "Edit",
                    "accessibility": "project.cbv.accessibility.project_manager_accessibility",
                    "attrs": """
                            hx-get='{get_update_url}'
                            hx-target='#genericModalBody'
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            class="oh-dropdown__link"
                            """,
                },
                {
                    "action": "archive_status",
                    "accessibility": "project.cbv.accessibility.project_manager_accessibility",
                    "attrs": """
                    href="{get_archive_url}"
                    onclick="return confirm('Do you want to {archive_status} this project?')"
                    class="oh-dropdown__link"
                    """,
                },
                {
                    "action": "Delete",
                    "accessibility": "project.cbv.accessibility.project_manager_accessibility",
                    "attrs": """
                    onclick="
                                event.stopPropagation()
                                deleteItem({get_delete_url});
                                "
                    class="oh-dropdown__link oh-dropdown__link--danger"
                    """,
                },
            ]

    details = {
        "image_src": "get_avatar",
        "title": "{get_task_badge_html}",
        "subtitle": "Status : {status_column} <br> Start date : {start_date} <br>End date : {end_date}",
    }
    card_status_class = "status-{status}"

    card_status_indications = [
        (
            "new--dot",
            _("New"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('new');
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
            "on-hold--dot",
            _("On Hold"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('on_hold');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "cancelled--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('cancelled');
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
    card_attrs = """
                 {redirect}
                 """


# def projects_tab(request, pk=None):
#     """
#     This method is used to projects tab
#     """

#     projects = Project.objects.filter(
#         Q(manager=pk)
#         | Q(members=pk)
#         | Q(task__task_members=pk)
#         | Q(task__task_manager=pk)
#     )
#     context = {"projects": projects}
#     if pk:
#         template = "cbv/projects/project_tab.html"
#         employees = Employee.objects.filter(id=pk).distinct()
#         emoloyee = employees.first()
#         context["employee"] = emoloyee
#     return render(
#         request,
#         template,
#         context,
#     )


class ProjectsTabView(ListView):
    model = Project
    template_name = "cbv/projects/project_tab.html"
    context_object_name = "projects"

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        queryset = Project.objects.filter(
            Q(manager=pk)
            | Q(members=pk)
            | Q(task__task_members=pk)
            | Q(task__task_manager=pk)
        )
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        if pk:
            employees = Employee.objects.filter(id=pk).distinct()
            employee = employees.first()
            context["employee"] = employee
        return context


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Projects",
            # "view": projects_tab,
            "view": ProjectsTabView.as_view(),
            "accessibility": "employee.cbv.accessibility.workshift_accessibility",
        },
    ]
)
