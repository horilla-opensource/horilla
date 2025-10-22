"""
this page is handling the cbv methods for employee tags in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import EmployeeTagForm
from employee.filters import EmployeeTagFilter
from employee.models import EmployeeTag
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="employee.view_employeetag"), name="dispatch"
)
class EmployeeTagListView(HorillaListView):
    """
    list view for employee tag in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employee-tag-list")
        self.actions = []
        if self.request.user.has_perm("employee.change_employeetag"):
            self.actions.append(
                {
                    "action": _("Edit"),
                    "icon": "create-outline",
                    "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100"
                        hx-get='{get_update_url}?instance_ids={ordered_ids}'
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                }
            )
        if self.request.user.has_perm("employee.delete_employeetag"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100 text-danger"
                        hx-confirm="Are you sure you want to delete this employee tag?"
                        hx-swap="outerHTML"
                        hx-post="{get_delete_url}"
                        hx-target="#employeeTagTr{get_instance_id}"
                      """,
                }
            )

    model = EmployeeTag
    filter_class = EmployeeTagFilter
    show_toggle_form = False

    row_attrs = """ id="employeeTagTr{get_instance_id}" """

    columns = [
        (_("Title"), "title"),
        (_("Color"), "color_span"),
    ]

    header_attrs = {
        "action": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="employee.view_employeetag"), name="dispatch"
)
class EmployeetagNavView(HorillaNavView):
    """
    nav bar of the department view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employee-tag-list")
        if self.request.user.has_perm("employee.add_employeetag"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('employee-tag-create-form')}"
                                """

    nav_title = _("Employee Tags")
    search_swap_target = "#listContainer"
    filter_instance = EmployeeTagFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="employee.add_employeetag"), name="dispatch")
class EmployeeTagCreateForm(HorillaFormView):
    """
    form view for creating and update employee tags in settings
    """

    model = EmployeeTag
    form_class = EmployeeTagForm
    new_display_title = _("Create Employee Tag")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Employee Tag Update")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Employee Tag Update")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: EmployeeTagForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Tag has been updated successfully!"))
            else:
                messages.success(self.request, _("Tag has been created successfully!"))
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)
