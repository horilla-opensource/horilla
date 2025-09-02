"""
This page handles the cbv methods for leave types page
"""

import contextlib
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from leave.filters import LeaveTypeFilter
from leave.forms import AssignLeaveForm, LeaveOneAssignForm
from leave.models import AvailableLeave, LeaveType
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeView(TemplateView):
    """
    template view
    """

    template_name = "cbv/leave_types/leave_type_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeListView(HorillaListView):
    """
    list view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-type-list")

    filter_class = LeaveTypeFilter
    model = LeaveType

    columns = [
        (_("Leave Type"), "name", "get_avatar"),
        (_("Payment"), "payment"),
        (_("Total Days"), "count"),
    ]

    action_method = "leave_list_actions"

    sortby_mapping = [
        ("Leave Type", "name", "get_avatar"),
        ("Total Days", "count"),
    ]

    row_status_indications = [
        (
            "paid--dot",
            _("Paid"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=payment]').val('paid');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "unpaid--dot",
            _("Un Paid"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=payment]').val('unpaid');
                $('#applyFilter').click();
            "
            """,
        ),
    ]

    header_attrs = {
        "action": """
                   style = "width:180px !important"
                   """
    }

    row_status_class = "payment-{payment}"

    row_attrs = """
                hx-get='{leave_detail_view}?instance_ids={ordered_ids}'
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"

                """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeNavView(HorillaNavView):
    """
    navbar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-type-list")
        if self.request.user.has_perm("leave.add_leavetype"):
            self.create_attrs = f"""
                                    href="{reverse_lazy('type-creation')}"
                                """
            self.view_types = [
                {
                    "type": "list",
                    "icon": "list-outline",
                    "url": reverse("leave-type-list"),
                    "attrs": """
                            title='List'
                            """,
                },
                {
                    "type": "card",
                    "icon": "grid-outline",
                    "url": reverse("leave-type-card-view"),
                    "attrs": """
                            title='Card'
                            """,
                },
            ]

    nav_title = _("Leave Types")
    filter_body_template = "cbv/leave_types/leave_type_filter.html"
    filter_form_context_name = "form"
    filter_instance = LeaveTypeFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeDetailView(HorillaDetailedView):
    """
    detail view
    """

    model = LeaveType
    title = _("Details")
    header = {"title": "name", "subtitle": "", "avatar": "get_avatar"}

    body = [
        (_("Period In"), "period_in"),
        (_("Total Days"), "count"),
        (_("Reset"), "reset"),
        (_("Carryforward Type"), "carryforward_type"),
        (_("Is paid"), "payment"),
        (_("Require Approval"), "require_approval"),
        (_("Require Attachment"), "require_attachment"),
        (_("Exclude company Leaves"), "exclude_company_leave"),
        (_("Exclude Holidays"), "exclude_holiday"),
        (_("Is Encashable"), "encashable"),
    ]
    action_method = "detail_view_actions"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.instance
        body = list(self.body)

        # Function to insert item after a specific key
        def insert_after(target_key, item):
            for i, (_, key) in enumerate(body):
                if key == target_key:
                    body.insert(i + 1, item)
                    break
            return body

        # Conditionally insert fields
        if instance.reset_based:
            body = insert_after("reset", (_("Reset Based"), "reset_based"))

        if instance.reset_month:
            body = insert_after("reset_based", (_("Reset Month"), "reset_month"))

        if instance.reset_day:
            body = insert_after("reset_based", (_("Reset Day"), "reset_day"))

        if instance.reset_weekend:
            body = insert_after("reset_based", (_("Reset weekend"), "reset_weekend"))

        if instance.carryforward_max:
            body = insert_after(
                "carryforward_type", (_("Maximum Carryforward"), "carryforward_max")
            )

        if instance.carryforward_expire_in:
            body = insert_after(
                "carryforward_max",
                (_("Carryforward Expires In"), "carryforward_expire_in"),
            )

        if instance.carryforward_expire_period:
            body = insert_after(
                "carryforward_expire_in",
                (_("Carryforward Expires In"), "carryforward_expire_period"),
            )

        context["body"] = body
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeCardView(HorillaCardView):
    """
    card view
    """

    model = LeaveType
    filter_class = LeaveTypeFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-type-card-view")

    details = {
        "image_src": "get_avatar",
        "title": "{name}",
        "subtitle": "Payment : {payment} <br> Total Days : {count}",
    }

    card_status_indications = [
        (
            "paid--dot",
            _("Paid"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=payment]').val('paid');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "unpaid--dot",
            _("Un Paid"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=payment]').val('unpaid');
                $('#applyFilter').click();
            "
            """,
        ),
    ]

    card_status_class = "payment-{payment}"

    card_attrs = """
                hx-get='{leave_detail_view}?instance_ids={ordered_ids}'
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                """

    actions = [
        {
            "action": _("Assign Leave"),
            "accessibility": "leave.cbv.accessibility.assign_leave",
            "attrs": """
                    data-toggle = "oh-modal-toggle"
                    data-target = "#genericModal"
                    hx-target="#genericModalBody"
                    hx-get ='{get_assign_url}'
                    class="oh-dropdown__link"
                    style="cursor: pointer;"
                    """,
        },
        {
            "action": _("Edit"),
            "attrs": """
            class="oh-dropdown__link"
            onclick="window.location.href='{get_update_url}' "
            """,
        },
        {
            "action": _("Delete"),
            "attrs": """
            class="oh-dropdown__link"
            hx-get="{get_delete_url}?model=leave.LeaveType&pk={pk}"
            data-toggle="oh-modal-toggle"
            data-target="#deleteConfirmation"
            hx-target="#deleteConfirmationBody"
            style="cursor: pointer; color:red !important"

            """,
        },
    ]

    records_per_page = 10


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leavetype"), name="dispatch")
class LeaveTypeAssignForm(HorillaFormView):
    """
    form view
    """

    form_class = LeaveOneAssignForm
    model = LeaveType
    template_name = "cbv/leave_types/inherit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Assign Leave")

        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Assign Leave")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: AssignLeaveForm) -> HttpResponse:
        form = self.form_class(self.request.POST, instance=self.form.instance)
        if form.is_valid():
            if form.instance.pk:
                leave_type = LeaveType.objects.get(id=form.instance.pk)
                if not leave_type.is_compensatory_leave:
                    employee_ids = self.request.POST.getlist("employee_id")
                    for employee_id in employee_ids:
                        employee = Employee.objects.get(id=employee_id)
                        if not AvailableLeave.objects.filter(
                            leave_type_id=leave_type, employee_id=employee
                        ).exists():
                            AvailableLeave(
                                leave_type_id=leave_type,
                                employee_id=employee,
                                available_days=leave_type.total_days,
                            ).save()
                            messages.success(
                                self.request,
                                _("Leave type assign is successfull"),
                            )
                            with contextlib.suppress(Exception):
                                notify.send(
                                    self.request.user.employee_get,
                                    recipient=employee.employee_user_id,
                                    verb="New leave type is assigned to you",
                                    verb_ar="تم تعيين نوع إجازة جديد لك",
                                    verb_de="Ihnen wurde ein neuer Urlaubstyp zugewiesen",
                                    verb_es="Se le ha asignado un nuevo tipo de permiso",
                                    verb_fr="Un nouveau type de congé vous a été attribué",
                                    icon="people-circle",
                                    redirect=reverse("user-request-view"),
                                )
                        else:
                            messages.info(
                                self.request,
                                _("leave type is already assigned to the employee"),
                            )
                else:
                    messages.info(
                        self.request,
                        _("Compensatory leave type cant assigned manually"),
                    )
            form.save()

            # messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
