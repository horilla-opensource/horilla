"""
This page handles action type of disciplinary action.
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from employee.cbv.disciplinary_actions import DynamicActionTypeFormView
from employee.filters import ActionTypeFilter
from employee.forms import ActiontypeForm
from employee.models import Actiontype
from horilla_audit.models import AccountBlockUnblock
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="employee.view_actiontype"), name="dispatch")
class ActionTypeListView(HorillaListView):
    """
    List view of the Action Type page.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "action_type"
        self.search_url = reverse("action-type-list")
        self.actions = []
        if self.request.user.has_perm("employee.change_actiontype"):
            self.actions.append(
                {
                    "action": "Edit",
                    "icon": "create-outline",
                    "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100"
                        hx-get="{get_update_url}?instance_ids={ordered_ids}"
                        hx-target="#genericModalBody"
                        data-toggle="oh-modal-toggle"
                        data-target="#genericModal"
                        """,
                }
            )
        if self.request.user.has_perm("employee.delete_actiontype"):
            self.actions.append(
                {
                    "action": "Delete",
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=employee.actiontype&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = Actiontype
    filter_class = ActionTypeFilter

    columns = [
        (_("Title"), "title"),
        (_("Type"), "get_action_type_display"),
        (_("Login Block"), "get_block_option"),
    ]

    sortby_mapping = [
        ("Title", "title"),
        ("Type", "get_action_type_display"),
    ]

    row_attrs = """
                id = "actionTr{get_instance_id}"
                """

    header_attrs = {
        "title": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="employee.view_actiontype"), name="dispatch")
class ActionTypeNav(HorillaNavView):
    """
    Navigation bar for Action Type.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("action-type-list")
        if self.request.user.has_perm("employee.add_actiontype"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('create-action-type')}"
                                """

    nav_title = _("Action Type")
    filter_instance = ActionTypeFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="employee.add_actiontype"), name="dispatch")
class ActionTypeFormView(DynamicActionTypeFormView):
    """
    Create and edit form for Action Type.
    """

    is_dynamic_create_view = False

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            if self.form.instance.action_type == "warning":
                self.form.fields["block_option"].widget = forms.HiddenInput()
            self.form_class.verbose_name = _("Update Action Type")
        context["form"] = self.form
        return context

    def form_valid(self, form: ActiontypeForm) -> HttpResponse:
        """
        Handle a valid form submission.

        If the form is valid, save the instance and display a success message.
        """
        if form.is_valid():
            if form.instance.pk:
                message = _("The action type updated successfully.")
            else:
                message = _("The action type created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
