"""
This page handles employee type in settings page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import EmployeeTypeFilter
from base.forms import EmployeeTypeForm
from base.models import EmployeeType
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_employeetype"), name="dispatch")
class EmployeeTypeListView(HorillaListView):
    """
    List view of the resticted days page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "employee_type"
        self.search_url = reverse("employee-type-list")
        self.actions = []
        if self.request.user.has_perm("base.change_employeetype"):
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
        if self.request.user.has_perm("base.delete_employeetype"):
            self.actions.append(
                {
                    "action": "Delete",
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.employeetype&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = EmployeeType
    filter_class = EmployeeTypeFilter
    show_toggle_form = False

    columns = [
        (_("Employee Type"), "employee_type"),
    ]
    header_attrs = {"employee_type": """ style="width:400px !important;" """}

    row_attrs = """ id = "employeeTypeTr{get_instance_id}" """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_employeetype"), name="dispatch")
class EmployeeTypeNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employee-type-list")
        if self.request.user.has_perm("base.add_employeetype"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('employee-type-create-view')}"
                                """

    nav_title = _("Employee Type")
    filter_instance = EmployeeTypeFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.add_employeetype"), name="dispatch")
class EmployeeTypeFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = EmployeeType
    form_class = EmployeeTypeForm
    new_display_title = _("Create Employee Type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Employee Type")
        return context

    def form_valid(self, form: EmployeeTypeForm) -> HttpResponse:

        if form.is_valid():
            if form.instance.pk:
                message = _("The employee type updated successfully.")
            else:
                message = _("The employee type created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
