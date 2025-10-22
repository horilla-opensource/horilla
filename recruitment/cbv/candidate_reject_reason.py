"""
This page handles reject reason in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from recruitment.filters import RejectReasonFilter
from recruitment.forms import RejectReasonForm
from recruitment.models import RejectReason


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_rejectreason"), name="dispatch"
)
class RejectReasonListView(HorillaListView):
    """
    List view of the rejected reason page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "reje_reason"
        self.search_url = reverse("candidate-reject-reasons-list")

    model = RejectReason
    filter_class = RejectReasonFilter
    show_toggle_form = False

    columns = [
        (_("Reject Reasons"), "title"),
        (_("Description"), "description"),
    ]

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                    class="oh-btn oh-btn--light-bkg w-50"
                    hx-get="{get_update_url}?instance_ids={ordered_ids}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
                    id = "delete-reject"
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-50"
                    hx-confirm="Are you sure want to delete this reason?"
                    hx-target="#rejectReasonTr{get_instance_id}"
                    hx-post="{get_delete_url}"
                    hx-swap="delete"
                    """,
        },
    ]

    header_attrs = {
        "title": """ style="width:200px !important" """,
        "description": """ style="width:200px !important" """,
        "action": """ style="width:200px !important" """,
    }

    row_attrs = """ id = "rejectReasonTr{get_instance_id}" """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_rejectreason"), name="dispatch"
)
class RejectReasonNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("candidate-reject-reasons-list")
        self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('create-reject-reason-view')}"
                            """

    nav_title = _("Reject Reasons")
    filter_instance = RejectReasonFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.add_rejectreason"), name="dispatch"
)
class RejectReasonFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = RejectReason
    form_class = RejectReasonForm
    new_display_title = _("Create reject reason")

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update reject reason")
        return context

    def form_valid(self, form: RejectReasonForm) -> HttpResponse:
        """
        Handle a valid form submission.

        If the form is valid, save the instance and display a success message.
        """
        if form.is_valid():
            if form.instance.pk:
                message = _("Reject reason updated successfully.")
            else:
                message = _("Reject reason created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)


class DynamicRejectReasonFormView(HorillaFormView):

    model = RejectReason
    form_class = RejectReasonForm
    new_display_title = _("Create reject reason")
    is_dynamic_create_view = True

    def form_valid(self, form: RejectReasonForm) -> HttpResponse:

        if form.is_valid():
            message = _("Reject reason created successfully.")
            messages.success(self.request, _(message))
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)
