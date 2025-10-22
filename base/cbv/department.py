"""
this page is handling the cbv methods for department in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import DepartmentViewFilter
from base.forms import DepartmentForm
from base.models import Department
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_department"), name="dispatch")
class DepartmentListView(HorillaListView):
    """
    list view for department in settings
    """

    model = Department
    filter_class = DepartmentViewFilter
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("department-list")
        self.actions = []
        if self.request.user.has_perm("base.change_department"):
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

        if self.request.user.has_perm("base.delete_department"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    hx-get="{get_delete_url}?model=base.Department&pk={pk}"
                    data-toggle="oh-modal-toggle"
                    data-target="#deleteConfirmation"
                    hx-target="#deleteConfirmationBody"
                """,
                }
            )

    row_attrs = """ id="departmentTr{get_delete_instance}" """

    columns = [
        (_("Department"), "department"),
    ]
    sortby_mapping = [
        (_("Department"), "department"),
    ]

    records_per_page = 7


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_department"), name="dispatch")
class DepartmentNavView(HorillaNavView):
    """
    nav bar of the department view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("department-list")
        if self.request.user.has_perm("base.add_department"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('settings-department-creation')}"
                                """

    nav_title = _("Department")
    search_swap_target = "#listContainer"
    filter_instance = DepartmentViewFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.add_department"), name="dispatch")
class DepartmentCreateForm(HorillaFormView):
    """
    form view for creating and editing departments in settings
    """

    model = Department
    form_class = DepartmentForm
    new_display_title = _("Create Department")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Department")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Department")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: DepartmentForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Department updated"))
            else:
                messages.success(
                    self.request, _("Department has been created successfully!")
                )
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)
