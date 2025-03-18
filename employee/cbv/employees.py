"""
employee view page
"""

from typing import Any
from django.dispatch import receiver
from django.urls import reverse, reverse_lazy
from django import forms
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from accessibility.cbv_decorators import enter_if_accessible
from horilla.signals import post_generic_delete
from base.methods import is_reportingmanager
from employee.views import _check_reporting_manager
from horilla_views.cbv_methods import login_required
from horilla_views.forms import DynamicBulkUpdateForm
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from employee.filters import EmployeeFilter
from employee.forms import BulkUpdateFieldForm, EmployeeExportExcelForm
from employee.models import Employee


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="employee_view",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class EmployeesView(TemplateView):
    """
    Employees view

    """

    template_name = "cbv/employees_view/view_employees.html"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        update_fields = BulkUpdateFieldForm()
        context["update_fields_form"] = update_fields
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="employee_view",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class EmployeesList(HorillaListView):
    """
    List view of employees
    """

    model = Employee
    filter_class = EmployeeFilter
    view_id = "view-container"
    bulk_template = "cbv/employees_view/bulk_update_page.html"
    bulk_update_fields = [
        "experience",
        "gender",
        "country",
        "state",
        "city",
        "zip",
        "marital_status",
        "children",
        "employee_work_info__department_id",
        "employee_work_info__job_position_id",
        "employee_work_info__job_role_id",
        "employee_work_info__shift_id",
        "employee_work_info__work_type_id",
        "employee_work_info__reporting_manager_id",
        "employee_work_info__employee_type_id",
        "employee_work_info__location",
        "employee_work_info__date_joining",
        "employee_work_info__company_id",
    ]

    def get_bulk_form(self):
        """
        Bulk from generating method
        """

        form = DynamicBulkUpdateForm(
            root_model=Employee, bulk_update_fields=self.bulk_update_fields
        )

        form.fields["country"] = forms.ChoiceField(
            required=False,
            widget=forms.Select(
                attrs={
                    "class": "oh-select oh-select-2",
                    "style": "width: 100%; height:45px;",
                }
            ),
        )

        form.fields["state"] = forms.ChoiceField(
            required=False,
            widget=forms.Select(
                attrs={
                    "class": "oh-select oh-select-2",
                    "style": "width: 100%; height:45px;",
                }
            ),
        )

        return form

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employees-list")

    columns = [
        (_("Employee"), "employee_name_with_badge_id", "get_avatar"),
        (_("Email"), "email"),
        (_("Phone"), "phone"),
        (_("Badge Id"), "badge_id"),
        (_("Job Position"), "employee_work_info__job_position_id"),
        (_("Department"), "employee_work_info__department_id"),
        (_("Shift"), "employee_work_info__shift_id"),
        (_("Work Type"), "employee_work_info__work_type_id"),
        (_("Job Role"), "employee_work_info__job_role_id"),
        (_("Reporting Manager"), "employee_work_info__reporting_manager_id"),
        (_("Company"), "employee_work_info__company_id"),
        (_("Work Email"), "employee_work_info__email"),
        (_("Date of Joining"), "employee_work_info__date_joining"),
    ]

    action_method = "employee_actions"
    records_per_page = 20

    header_attrs = {
        "action": """
                   style="width:300px !important;" 
                   """
    }

    row_attrs = """
                {diff_cell}
                onclick="window.location.href='{get_individual_url}?instance_ids={ordered_ids}'"
                """
    sortby_mapping = [
        ("Employee", "get_full_name", "get_avatar"),
        ("Badge Id", "badge_id"),
        (
            "Reporting Manager",
            "employee_work_info__reporting_manager_id__get_full_name",
        ),
        ("Date of Joining", "employee_work_info__date_joining"),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="employee_view",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class EmployeeNav(HorillaNavView):
    """
    For nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employees-list")
        self.search_in = [
            ("employee_work_info__reporting_manager_id", _("Reporting Manager")),
            (
                "employee_work_info__department_id",
                "Department",
            ),
            ("employee_work_info__job_position_id", _("Job Position")),
            ("employee_work_info__job_role_id", _("Job Role")),
            ("employee_work_info__shift_id", _("Shift")),
            ("employee_work_info__work_type_id", _("Work Type")),
            ("employee_work_info__company_id", _("Company")),
        ]
        if self.request.user.has_perm("employee.add_employee"):
            self.create_attrs = f"""
                                href="{reverse_lazy('employee-view-new')}"
                                """
        else:
            self.create_attrs = None

        if self.request.user.has_perm("employee.change_employee"):
            self.actions = [
                {
                    "action": _("Import"),
                    "attrs": """
                    id="work-info-import"
                    data-toggle="oh-modal-toggle"
                    data-target="#workInfoImport"
                    style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Export"),
                    "attrs": f"""
                    data-toggle="oh-modal-toggle"
                    data-target="#employeeExport"
                    hx-get="{reverse('employees-export')}"
                    hx-target="#employeeExportForm"
                    style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Archive"),
                    "attrs": """
                    id="archiveEmployees"
                    style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Un-archive"),
                    "attrs": """
                    id="unArchiveEmployees"
                    style="cursor: pointer;" 
                    """,
                },
                {
                    "action": _("Bulk mail"),
                    "attrs": f"""
                    data-toggle="oh-modal-toggle"
                    data-target="#sendMailModal"
                    hx-get="{reverse('employee-bulk-mail')}"
                    hx-target="#mail-content"
                    style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Bulk Update"),
                    "attrs": """
                    id="employeeBulkUpdateId"
                    style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                    class="oh-dropdown__link--danger"
                    data-action ="delete"
                    id="deleteEmployees"
                    style="cursor: pointer; color:red !important"
                    """,
                },
            ]
        else:
            self.actions = None

        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("employees-list"),
                "attrs": """
                            title ='List'
                            """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("employees-card"),
                "attrs": """
                          title ='Card'
                          """,
            },
        ]

    nav_title = _("Employees")
    filter_body_template = "cbv/employees_view/filter_employee.html"
    filter_instance = EmployeeFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"
    group_by_fields = [
        ("employee_work_info__job_position_id", _("Job Position")),
        (
            "employee_work_info__department_id",
            "Department",
        ),
        ("employee_work_info__shift_id", _("Shift")),
        ("employee_work_info__work_type_id", _("Work Type")),
        ("employee_work_info__job_role_id", _("Job Role")),
        ("employee_work_info__reporting_manager_id", _("Reporting Manager")),
        ("employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="employee_view",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class ExportView(TemplateView):
    """
    For candidate export
    """

    template_name = "cbv/employees_view/employee_export.html"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        employee = Employee.objects.filter(is_active=True)
        export_form = EmployeeExportExcelForm()
        export_filter = EmployeeFilter(queryset=employee)
        context["export_form"] = export_form
        context["export_filter"] = export_filter
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="employee_view",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class EmployeeCard(HorillaCardView):
    """
    For card view
    """

    model = Employee
    filter_class = EmployeeFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employees-card")
        if self.request.user.has_perm(
            "employee.change_employee"
        ) or is_reportingmanager(self.request):
            self.actions = [
                {
                    "action": "Edit",
                    "accessibility": "employee.cbv.accessibility.edit_accessibility",
                    "attrs": """
                    onclick="event.stopPropagation()
                    window.location.href='{get_update_url}' "
                    class="oh-dropdown__link"
                    
                """,
                },
                {
                    "action": "archive_status",
                    "accessibility": "employee.cbv.accessibility.action_accessible",
                    "attrs": """
                    hx-confirm="Do you want to {archive_status} this employee?"
                    hx-post="{get_archive_url}"
                    class="oh-dropdown__link"
                    hx-target="#relatedModel"  
                    """,
                },
                {
                    "action": _("Delete"),
                    "accessibility": "employee.cbv.accessibility.action_accessible",
                    "attrs": """
                        onclick="event.stopPropagation()"
                        hx-get="{get_delete_url}?model=employee.Employee&pk={pk}"
                        data-toggle="oh-modal-toggle" 
                        data-target="#deleteConfirmation"
                        hx-target="#deleteConfirmationBody"
                        class="oh-dropdown__link"
                        style="cursor: pointer;"
                    """,
                },
            ]
        else:
            self.actions = None

    details = {
        "image_src": "get_avatar",
        "title": "{employee_name_with_badge_id}",
        "subtitle": "<span class='oh-kanban-card__subtitle'>{email}</span><span class='oh-kanban-card__subtitle'>{employee_work_info__job_position_id}</span><span class='oh-kanban-card__subtitle'>{offline_online}</span>",
    }

    card_attrs = """
                {diff_cell}
                onclick="window.location.href='{get_individual_url}?instance_ids={ordered_ids}'"
                """

@receiver(post_generic_delete, sender=Employee)
def employee_generic_post_delete(sender, instance, *args, view_instance=None, **kwargs):
    """
    Employee genric post delete signal to handle the deletion of user instance
    """
    if instance.employee_user_id:
        instance.employee_user_id.delete()