from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import filter_own_records
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from payroll.filters import ReimbursementFilter
from payroll.forms.component_forms import ReimbursementForm
from payroll.models.models import Reimbursement


@method_decorator(login_required, name="dispatch")
class ReimbursementsView(TemplateView):
    """
    for reimbursements and encashments page
    """

    template_name = "cbv/reimbursements/reimbursements.html"


@method_decorator(login_required, name="dispatch")
class ReimbursementsAndEncashmentsTabView(HorillaTabView):
    """
    Tab View
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "reimbursmentContainer"
        self.tabs = [
            {
                "title": _("Reimbursements"),
                "url": f"{reverse('list-reimbursement')}",
            },
            {
                "title": _("Leave Encashments"),
                "url": f"{reverse('list-leave-encash')}",
            },
            {
                "title": _("Bonus Encashments"),
                "url": f"{reverse('list-bonus-encash')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
class ReimbursementsAndEncashmentsListView(HorillaListView):
    """
    list view
    """

    model = Reimbursement
    filter_class = ReimbursementFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.request.user.has_perm("payroll.change_reimbursement"):
            self.action_method = "actions_col"

    records_per_page = 5
    option_method = "options_col"

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
            "approved--dot",
            _("Approved"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('approved');
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
    ]

    row_status_class = "status-{status}"

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Date"), "created_at"),
        (_("Title"), "title"),
        (_("Amount"), "amount"),
        (_("Status"), "get_status_display"),
        (_("Description"), "description"),
        (_("Comment"), "comment_col"),
    ]

    header_attrs = {
        "description": """
                        style="width:250px !important;"
                        """,
        "action": """
                        style="width:200px !important;"
                        """,
    }


@method_decorator(login_required, name="dispatch")
class ReimbursementsListView(ReimbursementsAndEncashmentsListView):

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "created_at"),
        ("Amount", "amount"),
        ("Status", "get_status_display"),
    ]

    row_attrs = """
                hx-get='{reimbursements_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-reimbursement")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type="reimbursement")
        queryset = filter_own_records(
            self.request, queryset, "payroll.view_reimbursement"
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class LeaveEncashmentsListView(ReimbursementsAndEncashmentsListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-leave-encash")

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "created_at"),
        ("Amount", "amount"),
        ("Available days to encash", "ad_to_encash"),
        ("Carryforward to encash", "cfd_to_encash"),
    ]

    columns = [
        column
        for column in ReimbursementsAndEncashmentsListView.columns
        if column[1] != "amount"
    ] + [
        (_("Amount"), "amount_col"),
        (_("Leave type"), "leave_type_id"),
        (_("Available days to encash"), "ad_to_encash"),
        (_("Carryforward to encash"), "cfd_to_encash"),
    ]

    row_attrs = """
                hx-get='{leave_encash_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type="leave_encashment")
        queryset = filter_own_records(
            self.request, queryset, "payroll.view_reimbursement"
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class BonusEncashmentsListView(ReimbursementsAndEncashmentsListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-bonus-encash")

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "created_at"),
        ("Amount", "amount"),
        ("Status", "get_status_display"),
        ("Bonus to encash", "bonus_to_encash"),
    ]

    columns = [
        column
        for column in ReimbursementsAndEncashmentsListView.columns
        if column[1] != "amount"
    ] + [
        (_("Amount"), "amount_col"),
        (_("Bonus to encash"), "bonus_to_encash"),
    ]

    row_attrs = """
                hx-get='{bonus_encash_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type="bonus_encashment")
        queryset = filter_own_records(
            self.request, queryset, "payroll.view_reimbursement"
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class ReimbursementsNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("tab-reimbursement")
        self.create_attrs = f"""
                            hx-get="{reverse_lazy("reimbursement-create")}"
                            hx-target="#genericModalBody"
                            data-target="#genericModal"
                            data-toggle="oh-modal-toggle"
                            """

    nav_title = _("Reimbursements")
    filter_instance = ReimbursementFilter()
    filter_form_context_name = "form"
    filter_body_template = "cbv/reimbursements/filter.html"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
class ReimbursementsDetailView(HorillaDetailedView):
    """
    detail view of reimbursements
    """

    body = [
        (_("Date"), "created_at"),
        (_("Amount"), "amount"),
        (_("Status"), "get_status_display"),
        (_("Attachments"), "attachments_col"),
        (_("Description"), "description"),
    ]
    cols = {
        "description": 12,
    }

    action_method = "detail_action_col"

    model = Reimbursement
    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "title",
        "avatar": "employee_id__get_avatar",
    }


@method_decorator(login_required, name="dispatch")
class LeaveEncashmentsDetailedView(ReimbursementsDetailView):

    position = 3
    body = [
        body for body in ReimbursementsDetailView.body if body[1] != "attachments_col"
    ]
    body.insert(position, (_("Leave type"), "leave_type_id"))
    body.insert(position + 1, (_("Available days to encash"), "ad_to_encash"))
    body.insert(position + 2, (_("Carryforward to encash"), "cfd_to_encash"))


@method_decorator(login_required, name="dispatch")
class BonusEncashmentsDetailedView(ReimbursementsDetailView):

    body = [
        body for body in ReimbursementsDetailView.body if body[1] != "attachments_col"
    ]
    body.insert(3, (_("Bonus to encash"), "bonus_to_encash"))


@method_decorator(login_required, name="dispatch")
class ReimbursementsFormView(HorillaFormView):
    """
    Create and edit form for reimbursements
    """

    model = Reimbursement
    form_class = ReimbursementForm
    new_display_title = _("Create Reimbursement / Encashment")
    template_name = "cbv/reimbursements/forms.html"

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Reimbursement / Encashment")
        return context

    def form_valid(self, form: ReimbursementForm) -> HttpResponse:
        """
        Handle a valid form submission.
        If the form is valid, save the instance and display a success message.
        """
        if form.is_valid():
            if form.instance.pk:
                message = _("Reimbursement updated successfully")
            else:
                message = _("Reimbursement created successfully")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
