"""
This page handles the cbv of leave requests page
"""

import contextlib
from typing import Any

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import resolve, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.cbv.penalty import ViewPenaltyList
from base.decorators import manager_can_enter
from base.filters import PenaltyFilter
from base.methods import choosesubordinates, filtersubordinates
from base.models import PenaltyAccounts
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from leave.filters import LeaveRequestFilter
from leave.forms import LeaveRequestCreationForm, LeaveRequestExportForm
from leave.methods import filter_conditional_leave_request
from leave.models import AvailableLeave, LeaveRequest, LeaveType
from leave.threading import LeaveMailSendThread
from leave.views import multiple_approvals_check
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class LeaveRequestsView(TemplateView):
    """
    for leave requests page view
    """

    template_name = "cbv/leave_requests/leave_requests_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class LeaveRequestsListView(HorillaListView):
    """
    Lits view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("request-filter")
        self.view_id = "leaveRequest"
        if self.request.user.has_perm("leave.change_leaverequest"):
            self.bulk_update_fields = ["status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        data = queryset
        queryset = filter_conditional_leave_request(self.request)
        data = filtersubordinates(self.request, data, "leave.view_leaverequest")
        return data

    filter_class = LeaveRequestFilter
    model = LeaveRequest
    records_per_page = 10
    columns = [
        (_("Employee"), "leave_requests_custom_emp_col"),
        (_("Leave Type"), "leave_type_id"),
        (_("Start Date"), "start_date"),
        (_("End Date"), "end_date"),
        (_("Requested Days"), "requested_days"),
        (_("Leave Clash"), "leave_clash_col"),
        (_("Status"), "custom_status_col"),
        (_("Comment"), "comment_sidebar"),
        (_("Penalities"), "penality_col"),
    ]
    row_attrs = """
                {is_attendance_request_cancelled},
                hx-get='{leave_requests_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Leave Type", "leave_type_id"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Requested Days", "requested_days"),
        ("Status", "status"),
    ]

    action_method = "confirmation_col"
    option_method = "actions_col"

    header_attrs = {
        "leave_requests_custom_emp_col": """
                                style="width:200px !important;"
                                """,
        "option": """
                                style="width:200px !important;"
                                """,
    }

    row_status_indications = [
        (
            "rejected--dot",
            _("Rejected"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('rejected');
            $('[name=canceled]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "cancelled--dot",
            _("Cancelled"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('cancelled');
            $('[name=rejected]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
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
            $('[name=rejected]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
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
            $('[name=rejected]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
    ]
    row_status_class = (
        "rejected-{status} cancelled-{status} requested-{status} approved-{status}"
    )


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class LeaveRequestsNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("request-filter")
        self.search_in = [
            ("leave_type_id", "Leave Type"),
            ("status", "Status"),
            ("employe_id__employee_work_info__department_id", "Department"),
            ("employee_id__employee_work_info__job_position_id", "Job Position"),
            ("employee_id__employee_work_info__company_id", "Company"),
        ]

        self.actions = [
            {
                "action": _("Bulk Approve"),
                "attrs": """
                    onclick="
                    bulkApproveLeaveRequests();
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
                    hx-get ="{reverse('leave-requests-nav-export')}"
                    style="cursor: pointer;"
                """,
            },
            {
                "action": _("Delete"),
                "attrs": """
                    onclick="
                    bulkDeleteLeaveRequests();
                    "
                    data-action ="delete"
                    style="cursor: pointer; color:red !important"
                """,
            },
        ]

        self.create_attrs = f"""
             hx-get="{reverse_lazy("request-creation")}"
             hx-target="#genericModalBody"
             data-target="#genericModal"
             data-toggle="oh-modal-toggle"
         """

    nav_title = _("Leave Requests")
    filter_instance = LeaveRequestFilter()
    filter_body_template = "cbv/leave_requests/filter.html"
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("start_date", _("Start Date")),
        ("end_date", _("End Date")),
        ("status", _("Status")),
        ("requested_days", _("Requested Days")),
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
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class LeaveRequestsExportNav(TemplateView):
    """
    for bulk export
    """

    template_name = "cbv/leave_requests/leave_requests_export.html"

    def get_context_data(self, **kwargs: Any):
        """
        get data for export
        """
        data = LeaveRequest.objects.all()
        export_form = LeaveRequestExportForm
        export_filter = LeaveRequestFilter(queryset=data)
        context = super().get_context_data(**kwargs)
        context["export_form"] = export_form
        context["export_filter"] = export_filter
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class LeaveRequestsDetailView(HorillaDetailedView):
    """
    detail view of page
    """

    model = LeaveRequest
    title = _("Details")
    header = {
        "title": "leave_requests_detail_subtitle",
        "subtitle": "my_leave_request_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    body = [
        (_("Leave Type"), "leave_type_id"),
        (_("Days"), "requested_days"),
        (_("Start Date"), "start_date"),
        (_("End Date"), "end_date"),
        (_("Created Date"), "requested_date"),
        (_("Created By"), "created_by"),
        (_("Description"), "description"),
        (_("Status"), "get_status_display"),
        (_("View attachment"), "attachment_action", True),
        (_("Reason for Rejection"), "rejected_action", True),
        (_("Reason for Cancellation"), "cancelled_action", True),
        (_("Multiple Approvals"), "multiple_approval_action", True),
    ]
    action_method = "leave_requests_detail_view_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.add_leaverequest"), name="dispatch")
class LeaveRequestFormView(HorillaFormView):
    """
    form view
    """

    model = LeaveRequest
    form_class = LeaveRequestCreationForm
    template_name = "cbv/leave_requests/form/inherit.html"
    new_display_title = _("Leave Request")

    def get_initial(self) -> dict:
        initial = super().get_initial()
        leave_type_id = self.kwargs.get("type_id")
        employee_id = self.kwargs.get("emp_id")
        if leave_type_id and employee_id:
            initial["leave_type_id"] = leave_type_id
            initial["employee_id"] = employee_id
            return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request:
            employee = self.request.user.employee_get
            if employee:
                available_leaves = employee.available_leave.all()
                assigned_leave_types = LeaveType.objects.filter(
                    id__in=available_leaves.values_list("leave_type_id", flat=True)
                )
                self.form.fields["leave_type_id"].queryset = assigned_leave_types

        if self.form.instance.pk:
            leave_request = LeaveRequest.objects.get(id=self.form.instance.pk)
            leave_type_id = leave_request.leave_type_id
            employee = leave_request.employee_id
            self.form_class(instance=leave_request)
            if employee:
                available_leaves = employee.available_leave.all()
                assigned_leave_types = LeaveType.objects.filter(
                    id__in=available_leaves.values_list("leave_type_id", flat=True)
                )
                if leave_type_id not in assigned_leave_types.values_list(
                    "id", flat=True
                ):
                    assigned_leave_types = (
                        assigned_leave_types
                        | LeaveType.objects.filter(id=leave_type_id.id)
                    )
                self.form.fields["leave_type_id"].queryset = assigned_leave_types
                # form = self.form_class(instance = self.form.instance)
        self.form = choosesubordinates(
            self.request, self.form, "leave.add_leaverequest"
        )
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Leave Request")

        context["form"] = self.form
        context["view_id"] = "leaverequest"

        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Leave Request")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: LeaveRequestCreationForm) -> HttpResponse:
        form = self.form_class(
            self.request.POST, self.request.FILES, instance=self.form.instance
        )
        if form.is_valid():
            if form.instance.pk:
                leave_request = form.save(commit=False)
                save = True

                if save:
                    leave_request.save()
                    messages.success(
                        self.request, _("Leave request is updated successfully")
                    )
                    with contextlib.suppress(Exception):
                        notify.send(
                            self.request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"Leave request updated for {leave_request.employee_id}.",
                            verb_ar=f"تم تحديث طلب الإجازة لـ {leave_request.employee_id}.",
                            verb_de=f"Urlaubsantrag aktualisiert für {leave_request.employee_id}.",
                            verb_es=f"Solicitud de permiso actualizada para {leave_request.employee_id}.",
                            verb_fr=f"Demande de congé mise à jour pour {leave_request.employee_id}.",
                            icon="people-circle",
                            redirect=reverse("request-view")
                            + f"?id={leave_request.id}",
                        )

            else:
                leave_request = form.save(commit=False)
                save = True

                if leave_request.leave_type_id.require_approval == "no":
                    employee_id = leave_request.employee_id
                    leave_type_id = leave_request.leave_type_id
                    available_leave = AvailableLeave.objects.get(
                        leave_type_id=leave_type_id, employee_id=employee_id
                    )
                    leave_request.created_by = self.request.user.employee_get
                    leave_request.save()
                    if leave_request.requested_days > available_leave.available_days:
                        leave = (
                            leave_request.requested_days
                            - available_leave.available_days
                        )
                        leave_request.approved_available_days = (
                            available_leave.available_days
                        )
                        available_leave.available_days = 0
                        available_leave.carryforward_days = (
                            available_leave.carryforward_days - leave
                        )
                        leave_request.approved_carryforward_days = leave
                    else:
                        available_leave.available_days = (
                            available_leave.available_days
                            - leave_request.requested_days
                        )
                        leave_request.approved_available_days = (
                            leave_request.requested_days
                        )
                    leave_request.status = "approved"
                    available_leave.save()
                if save:
                    leave_request.created_by = self.request.user.employee_get
                    leave_request.save()

                    if multiple_approvals_check(leave_request.id):
                        conditional_requests = multiple_approvals_check(
                            leave_request.id
                        )
                        managers = []
                        for manager in conditional_requests["managers"]:
                            managers.append(manager.employee_user_id)
                        with contextlib.suppress(Exception):
                            notify.send(
                                self.request.user.employee_get,
                                recipient=managers[0],
                                verb="You have a new leave request to validate.",
                                verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                                verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                                verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                                verb_fr="Vous avez une nouvelle demande de congé à valider.",
                                icon="people-circle",
                                redirect=f"/leave/request-view?id={leave_request.id}",
                            )

                    mail_thread = LeaveMailSendThread(
                        self.request, leave_request, type="request"
                    )
                    mail_thread.start()
                    messages.success(
                        self.request, _("Leave request created successfully")
                    )
                    with contextlib.suppress(Exception):
                        notify.send(
                            self.request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"New leave request created for {leave_request.employee_id}.",
                            verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                            verb_de=f"Neuer Urlaubsantrag erstellt für {leave_request.employee_id}.",
                            verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                            verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                            icon="people-circle",
                            redirect=reverse("request-view")
                            + f"?id={leave_request.id}",
                        )

                leave_requests = LeaveRequest.objects.all()
                if len(leave_requests) == 1:
                    return HttpResponse("")

            return self.HttpResponse("")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class LeaveClashListView(LeaveRequestsListView):
    """
    list view of leave clash col
    """

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        pk = self.kwargs.get("pk")
        record = LeaveRequest.objects.get(id=pk)
        if record.status != "rejected" or record.status != "cancelled":
            queryset = (
                queryset.filter(
                    Q(
                        employee_id__employee_work_info__department_id=record.employee_id.employee_work_info.department_id
                    )
                    | Q(
                        employee_id__employee_work_info__job_position_id=record.employee_id.employee_work_info.job_position_id
                    ),
                    start_date__lte=record.end_date,
                    end_date__gte=record.start_date,
                )
                .exclude(id=pk)
                .exclude(Q(status="cancelled") | Q(status="rejected"))
            )

        return queryset.distinct()

    columns = [
        col
        for col in LeaveRequestsListView.columns
        if col[1] not in ["leave_clash_col", "penality_col", "actions_col"]
    ] + [(_("Clased Due To"), "clashed_due_to")]

    row_status_class = ""
    row_status_indications = None
    bulk_select_option = None
    row_attrs = ""


ViewPenaltyList.columns.extend(
    [
        (_("Leave Type"), "leave_type_id"),
        (_("Minus Days"), "minus_leaves"),
        (_("Deducted FromCFD"), "get_deduct_from_carry_forward"),
    ]
)
