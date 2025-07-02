"""
Leave allocation request page
"""

import contextlib
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import choosesubordinates, filtersubordinates, is_reportingmanager
from employee.cbv.employee_profile import EmployeeProfileView
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from leave.cbv.leave_tab import IndividualLeaveTab
from leave.filters import LeaveAllocationRequestFilter
from leave.forms import LeaveAllocationRequestForm
from leave.models import LeaveAllocationRequest
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestView(TemplateView):
    """
    for leave allocation  request page view
    """

    template_name = "cbv/leave_allocation_request/leave_allocation_request.html"


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestList(HorillaListView):
    """
    List view of the page
    """

    model = LeaveAllocationRequest
    filter_class = LeaveAllocationRequestFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-allocation-request-filter")
        self.view_id = "view-container"

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Leave Type"), "leave_type_id"),
        (_("Requested Days"), "requested_days"),
        (_("Created By"), "created_by__employee_get"),
        (_("Status"), "get_status"),
        (_("Description"), "description"),
        (_("Comment"), "comment"),
    ]

    header_attrs = {
        "action": """
                    style="width:180px !important;"
                    """,
        "description": """
                    style="width:180px !important;"
                    """,
    }

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name"),
        ("Leave Type", "leave_type_id__name"),
        ("Requested Days", "requested_days"),
        ("Created By", "created_by__get_full_name"),
        ("Status", "get_status"),
    ]

    option_method = "action_col"

    row_status_indications = [
        (
            "rejected--dot",
            _("Rejected"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('rejected');
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "requested--dot",
            _("Requested"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('requested');
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "approved--dot",
            _("Approved"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('approved');
            $('#applyFilter').click();
            "

            """,
        ),
    ]

    row_status_class = "status-{status}"


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestTab(HorillaTabView):
    """
    Tab View
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "leave-allocation"
        self.tabs = [
            {
                "title": _("My Leave allocation request"),
                "url": f"{reverse('my-leave-allocation-request-tab')}",
            },
        ]
        if self.request.user.has_perm(
            "leave.view_leaveallocationrequest"
        ) or is_reportingmanager(self.request):

            self.tabs.append(
                {
                    "title": _("Leave allocation requests"),
                    "url": f"{reverse('leave-allocation-requests-tab-view')}",
                },
            )


@method_decorator(login_required, name="dispatch")
class MyLeaveAllocationRequest(LeaveAllocationRequestList):
    """
    My leave allocations
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-allocation-request-filter")
        self.view_id = "my-leave-container"

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(employee_id=employee).order_by("-id")
        return queryset

    row_attrs = """
                {diff_cell}
                hx-get='{leave_request_allocation_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    option_method = None
    action_method = "action_col"


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequests(LeaveAllocationRequestList):
    """
    Leave allocation request
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-allocation-requests-tab-view")
        self.view_id = "all-leave-container"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = filtersubordinates(
            self.request, queryset, "leave.view_leaveallocationrequest"
        )
        return queryset

    action_method = "confirm_col"

    row_attrs = """
                {diff_cell}
                hx-get='{detail_view_leave_request_allocation}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-allocation-request-filter")
        self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#objectCreateModal"
                            hx-target="#objectCreateModalTarget"
                            hx-get="{reverse_lazy('leave-allocation-request-create')}"
                            """

    nav_title = _("Leave Allocation Requests")
    filter_instance = LeaveAllocationRequestFilter()
    filter_body_template = "cbv/leave_allocation_request/filter.html"
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("status", _("Status")),
        ("requested_days", _("Requested Days")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        (
            "employee_id__employee_work_info__employee_type_id",
            _("Employment Type"),
        ),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestDetailView(HorillaDetailedView):
    """
    detail view of page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Requested Days"), "requested_days"),
            (_("Leave Type"), "leave_type_id"),
            (_("Created Date"), "requested_date"),
            (_("Created By"), "created_by__employee_get"),
            (_("Description"), "description"),
            (_("History"), "history_col", True),
            (_("Reject Reason"), "reject_col", True),
            (_("Attachment"), "attachment_col", True),
        ]

    action_method = "detail_action"

    model = LeaveAllocationRequest
    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "leave_request_allocation_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }


@method_decorator(login_required, name="dispatch")
class LeaveAllocationsRequestsTabDetailView(LeaveAllocationRequestDetailView):
    """
    Detail view
    """

    action_method = "leave_detail_action"


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestFormView(HorillaFormView):
    """
    Form View
    """

    model = LeaveAllocationRequest
    form_class = LeaveAllocationRequestForm
    new_display_title = _("Create Leave Allocation Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_get
        self.form_class(initial={"employee_id": employee})
        if self.form.instance.pk:
            self.form_class.verbose_name = "Update Request"
            self.form_class(instance=self.form.instance)
        self.form = choosesubordinates(
            self.request, self.form, "leave.add_leaveallocationrequest"
        )
        self.form.fields["employee_id"].queryset = self.form.fields[
            "employee_id"
        ].queryset | Employee.objects.filter(employee_user_id=self.request.user)
        context["form"] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: LeaveAllocationRequestForm) -> HttpResponse:
        if form.is_valid():
            self.form_class(self.request.FILES)
            instance = form.save()
            instance.skip_history = False
            if form.instance.pk:
                message = _("Leave allocation request updated")
                with contextlib.suppress(Exception):
                    notify.send(
                        self.request.user.employee_get,
                        recipient=instance.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"Leave allocation request updated for {instance.employee_id}.",
                        verb_ar=f"تم تحديث طلب تخصيص الإجازة لـ {instance.employee_id}.",
                        verb_de=f"Urlaubszuteilungsanforderung aktualisiert für {instance.employee_id}.",
                        verb_es=f"Solicitud de asignación de licencia actualizada para {instance.employee_id}.",
                        verb_fr=f"Demande d'allocation de congé mise à jour pour {instance.employee_id}.",
                        icon="people-cicle",
                        redirect=reverse("leave-allocation-request-view")
                        + f"?id={instance.id}",
                    )
            else:
                message = _("New leave allocation request created")
                with contextlib.suppress(Exception):
                    notify.send(
                        self.request.user.employee_get,
                        recipient=instance.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"New leave allocation request created for {instance.employee_id}.",
                        verb_ar=f"تم إنشاء طلب تخصيص إجازة جديد لـ {instance.employee_id}.",
                        verb_de=f"Neue Anfrage zur Urlaubszuweisung erstellt für {instance.employee_id}.",
                        verb_es=f"Nueva solicitud de asignación de permisos creada para {instance.employee_id}.",
                        verb_fr=f"Nouvelle demande d'allocation de congé créée pour {instance.employee_id}.",
                        icon="people-cicle",
                        redirect=reverse("leave-allocation-request-view")
                        + f"?id={instance.id}",
                    )
            instance.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Leave",
            # "view": views.employee_view_individual_leave_tab,
            "view": IndividualLeaveTab.as_view(),
            "accessibility": "leave.cbv.accessibility.leave_accessibility",
        },
    ]
)
