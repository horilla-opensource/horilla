"""
this page handles cbv of assigned leave page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.methods import filtersubordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from leave.filters import AssignedLeaveFilter
from leave.forms import AssignLeaveForm, AvailableLeaveColumnExportForm
from leave.models import AvailableLeave


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_availableleave"), name="dispatch")
class AssignedLeaveViewPage(TemplateView):
    """
    for assigned leave page
    """

    template_name = "cbv/assigned_leave/assigned_leave_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_availableleave"), name="dispatch")
class AssignedleaveList(HorillaListView):
    """
    list view of the page
    """

    model = AvailableLeave
    filter_class = AssignedLeaveFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("assign-filter")
        self.view_id = "assignedleavedelete"

    row_attrs = """
                hx-get='{assigned_leave_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = filtersubordinates(
            self.request, queryset, "leave.view_availableleave"
        )
        return queryset

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Badge ID"), "employee_id__badge_id"),
        (_("Leave Type"), "leave_type_id"),
        (_("Available Days"), "available_days"),
        (_("Carryforward Days"), "carryforward_days"),
        (_("Total Leave Days"), "total_leave_days"),
        (_("Assigned Date"), "assigned_date"),
        (_("Taken Leaves"), "leave_taken"),
    ]

    action_method = "assigned_leave_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_availableleave"), name="dispatch")
class AssignedLeaveNavView(HorillaNavView):
    """
    navbar of the page
    """

    template_name = "cbv/assigned_leave/nav_fixed_filter.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("assign-filter")

        self.actions = [
            {
                "action": _("Import"),
                "attrs": """
                        onclick="
                        importAssignedLeave();
                        "
                        data-toggle = "oh-modal-toggle"
                        data-target = "#assignLeaveTypeImport
                        "
                        style="cursor: pointer;"
                    """,
            },
            {
                "action": _("Export"),
                "attrs": f"""
                        data-toggle = "oh-modal-toggle"
                        data-target = "#genericModal"
                        hx-target="#genericModalBody"
                        hx-get ="{reverse('assigned-leave-nav-export')}"
                        style="cursor: pointer;"
                    """,
            },
            {
                "action": _("Delete"),
                "attrs": """
                            onclick="leaveAssigBulkDelete()"
                            data-action ="delete"
                            style="cursor: pointer; color:red !important"
                             """,
            },
        ]

        self.create_attrs = f"""
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
                hx-target="#objectCreateModalTarget"
                hx-get="{reverse_lazy('assign')}"
            """

    nav_title = _("All Assigned Leaves")
    filter_instance = AssignedLeaveFilter()
    filter_form_context_name = "form"
    filter_body_template = "cbv/assigned_leave/assigned_filter.html"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("available_days", _("Available Days")),
        ("carryforward_days", _("Carryforward Days")),
        ("total_leave_days", _("Total Leave Days")),
        ("assigned_date", _("Assigned Date")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employement Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_availableleave"), name="dispatch")
class AssignedLeaveExport(TemplateView):
    """
    view for Export leave assigns
    """

    template_name = "cbv/assigned_leave/assigned_leave_export.html"

    def get_context_data(self, **kwargs: Any):
        """
        context to get data
        """
        leaves = AvailableLeave.objects.all()
        export_column = AvailableLeaveColumnExportForm()
        export_filter = AssignedLeaveFilter(queryset=leaves)
        context = super().get_context_data(**kwargs)
        context["export_column"] = export_column
        context["export_filter"] = export_filter
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_availableleave"), name="dispatch")
class AssignedLeaveDetailView(HorillaDetailedView):
    """
    detail view
    """

    model = AvailableLeave
    ttile = _("Details")
    header = {
        "title": "assigned_leave_detail_name_subtitle",
        "subtitle": "assigned_leave_detail_postion_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    body = [
        (_("Leave Type"), "leave_type_id"),
        (_("Available Days"), "available_days"),
        (_("Carryforward Days"), "carryforward_days"),
        (_("Total Leave Days"), "total_leave_days"),
        (_("Assigned Date"), "assigned_date"),
        (_("Leave Reset Date"), "reset_date"),
    ]

    action_method = "assigned_leave_detail_actions"


# not done
class AssignedLeaveFormView(HorillaFormView):
    """
    form view
    """

    form_class = AssignLeaveForm
    model = AvailableLeave
    new_display_title = _("Assign Leaves")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Available Leave")

        return context

    def form_valid(self, form: AssignLeaveForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Available Leave Updated Successfully")
            else:
                message = _("Available Leave Created Successfully")
            form.save()

            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
