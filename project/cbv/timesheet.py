"""
CBV of time sheet page
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from project.cbv.cbv_decorators import is_projectmanager_or_member_or_perms
from project.cbv.projects import DynamicProjectCreationFormView
from project.filters import TimeSheetFilter
from project.forms import TimeSheetForm
from project.models import Project, TimeSheet


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetView(TemplateView):
    """
    for time sheet page
    """

    template_name = "cbv/timesheet/timesheet.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetNavView(HorillaNavView):
    """
    Nav bar
    """

    filter_form_context_name = "form"
    filter_instance = TimeSheetFilter()
    search_swap_target = "#listContainer"
    template_name = "cbv/timesheet/timesheet_nav.html"
    filter_body_template = "cbv/timesheet/filter.html"
    group_by_fields = [
        "employee_id",
        "project_id",
        "date",
        "status",
        "employee_id__employee_work_info__reporting_manager_id",
        "employee_id__employee_work_info__department_id",
        "employee_id__employee_work_info__job_position_id",
        "employee_id__employee_work_info__employee_type_id",
        "employee_id__employee_work_info__company_id",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("time-sheet-list")
        url = f"{reverse('personal-time-sheet-view',kwargs={'emp_id': self.request.user.employee_get.id})}"
        self.actions = [
            {
                "action": _("Delete"),
                "attrs": """
                    class="oh-dropdown__link--danger"
                    data-action ="delete"
                    onclick="deleteTimeSheet();"
                    style="cursor: pointer; color:red !important"
                    """,
            },
        ]
        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("time-sheet-list"),
                "attrs": """
                        title ='List'
                        """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("time-sheet-card"),
                "attrs": """
                          title ='Card'
                          """,
            },
            {
                "type": "graph",
                "icon": "bar-chart",
                "attrs": f"""
                          onclick="event.stopPropagation();
                          window.location.href='{url}'"
                          title ='Graph'
                          """,
            },
        ]

        self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('create-time-sheet')}"
                                """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetList(HorillaListView):
    """
    Time sheet list view
    """

    model = TimeSheet
    filter_class = TimeSheetFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_timesheet"):
            employee = self.request.user.employee_get
            queryset = queryset.filter(
                Q(project_id__managers=employee)
                | Q(project_id__members=employee)
                | Q(employee_id=employee)
            ).distinct()
        return queryset.order_by("-date")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.search_url = reverse("time-sheet-list")
        self.action_method = "actions"

    @cached_property
    def columns(self):
        get_field = self.model()._meta.get_field
        return [
            (
                get_field("employee_id").verbose_name,
                "employee_id",
                "employee_id__get_avatar",
            ),
            (get_field("project_id").verbose_name, "project_id"),
            (get_field("task_name").verbose_name, "task_name"),
            (get_field("date").verbose_name, "date"),
            (get_field("time_spent").verbose_name, "time_spent"),
            (get_field("status").verbose_name, "get_status_display"),
            (get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def sortby_mapping(self):
        get_field = self.model()._meta.get_field
        return [
            (
                get_field("employee_id").verbose_name,
                "employee_id__employee_first_name",
                "employee_id__get_avatar",
            ),
            (get_field("project_id").verbose_name, "project_id__title"),
            (get_field("task_name").verbose_name, "task_name"),
            (get_field("time_spent").verbose_name, "time_spent"),
            (get_field("date").verbose_name, "date"),
        ]

    row_status_indications = [
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_Progress');
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
    ]
    row_attrs = """
                hx-get='{detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    row_status_class = "status-{status}"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetFormView(HorillaFormView):
    """Form view for creating or updating a timesheet."""

    form_class = TimeSheetForm
    model = TimeSheet
    new_display_title = _("Create") + " " + model._meta.verbose_name

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dynamic_create_fields = []
        if self.request.user.has_perm("project.add_project"):
            self.dynamic_create_fields.append(("project_id", DynamicProjectCreationFormView))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = (
            self.request.GET.get("project_id")
            or self.form.initial.get("project_id")
            or (self.form.instance.project_id_id if self.form.instance.pk else None)
        )
        if project_id:
            project = Project.objects.filter(id=project_id).first()
            if project:
                members = (project.managers.all() | project.members.all()).distinct()
                self.form.fields["employee_id"].queryset = members
        else:
            if not self.request.user.has_perm("project.add_timesheet"):
                emp = self.request.user.employee_get
                self.form.fields["employee_id"].queryset = Employee.objects.filter(id=emp.id)

        if not self.request.user.has_perm("project.add_timesheet"):
            employee = self.request.user.employee_get
            projects = Project.objects.filter(
                Q(managers=employee) | Q(members=employee)
            ).distinct()
            self.form.fields["project_id"].queryset = projects
        return context

    def form_valid(self, form: TimeSheetForm) -> HttpResponse:
        if form.is_valid():
            message = _(
                f"{self.form.instance} Updated" if form.instance.pk else "New time sheet created"
            )
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)

@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetCardView(HorillaCardView):
    """
    For card view
    """

    model = TimeSheet
    filter_class = TimeSheetFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_timesheet"):
            employee = self.request.user.employee_get
            queryset = queryset.filter(
                Q(project_id__managers=employee)
                | Q(project_id__members=employee)
                | Q(employee_id=employee)
            ).distinct()
        return queryset

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("time-sheet-card")
        self.actions = [
            {
                "action": "Edit",
                "attrs": """
                         hx-get='{get_update_url}'
                         hx-target='#genericModalBody'
                         data-toggle="oh-modal-toggle"
                         data-target="#genericModal"
                         class="oh-dropdown__link"
                         """,
            },
            {
                "action": "Delete",
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
        "image_src": "employee_id__get_avatar",
        "title": "{employee_id}",
        "subtitle": " <b>{date}</b> <br>Project : <b>{project_id}</b> <br><b>{task_name}</b> |  Time Spent : <b>{time_spent}</b>",
    }

    card_status_class = "status-{status}"

    card_status_indications = [
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_Progress');
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
    ]

    card_attrs = """
                hx-get='{detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_timesheet"), name="dispatch"
)
class TimeSheetDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    model = TimeSheet
    title = _("Details")
    header = {
        "title": "employee_id",
        "subtitle": "project_id",
        "avatar": "employee_id__get_avatar",
    }
    action_method = "detail_actions"

    @cached_property
    def body(self):
        get_field = self.model()._meta.get_field
        return [
            (get_field("task_name").verbose_name, "task_name"),
            (get_field("date").verbose_name, "date"),
            (get_field("time_spent").verbose_name, "time_spent"),
            (get_field("status").verbose_name, "get_status_display"),
            (get_field("description").verbose_name, "description"),
        ]
