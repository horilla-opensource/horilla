"""
This page  handles rotating shift types page in settings.
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.filters import RotatingShiftFilter
from base.forms import RotatingShiftForm
from base.models import RotatingShift
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_rotatingshift"), name="dispatch")
class RotatingShiftTypeListView(HorillaListView):
    """
    List view of the employee shift page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "shift_view"
        self.search_url = reverse("rotating-shift-list")
        self.actions = []
        if self.request.user.has_perm("base.change_rotatingshift"):
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
        if self.request.user.has_perm("base.delete_rotatingshift"):
            self.actions.append(
                {
                    "action": "Delete",
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.rotatingshift&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = RotatingShift
    filter_class = RotatingShiftFilter

    columns = [
        (_("Title"), "name"),
        (_("Shift 1"), "shift1"),
        (_("Shift 2"), "shift2"),
        (_("Additional Shifts"), "get_additional_shifts"),
    ]

    sortby_mapping = [
        ("Title", "name"),
        ("Shift 1", "shift1__employee_shift"),
        ("Shift 2", "shift2__employee_shift"),
        ("Additional Shifts", "get_additional_shifts"),
    ]

    row_attrs = """
                id = "rotatingShiftTr{get_instance_id}"
                """

    header_attrs = {
        "name": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_rotatingshift"), name="dispatch")
class RotatingShiftTypeNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-shift-list")
        if self.request.user.has_perm("base.add_rotatingshift"):
            self.create_attrs = f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('rotating-shift-create')}"
                                """

    nav_title = _("Rotating Shift")
    filter_instance = RotatingShiftFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("base.add_rotatingshift"), name="dispatch")
class DynamicRotatingShiftTypeFormView(HorillaFormView):
    """
    form view
    """

    model = RotatingShift
    form_class = RotatingShiftForm
    new_display_title = "Create Rotating Shift"
    is_dynamic_create_view = True
    template_name = "cbv/rotating_shift/rot_shift_form.html"

    def form_valid(self, form: RotatingShiftForm) -> HttpResponse:
        if form.is_valid():
            form.save()
            message = _("Rotating Shift Created")
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("base.add_rotatingshift"), name="dispatch")
class RotatingShiftTypeCreateFormView(DynamicRotatingShiftTypeFormView):
    """
    form view
    """

    is_dynamic_create_view = False
    template_name = "cbv/rotating_shift/rot_shift_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Rotating Shift Type")
        context[form] = form
        return context

    def form_valid(self, form: RotatingShiftForm) -> HttpResponse:
        if form.is_valid():
            form.save()
            if self.form.instance.pk:
                message = _("Rotating Shift Updated")
            else:
                message = _("Rotating Shift Created")
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
