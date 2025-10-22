"""
this page is handling the cbv methods for Rotating work type in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.filters import RotatingWorkTypeFilter
from base.forms import RotatingWorkTypeForm
from base.models import RotatingWorkType
from horilla.decorators import permission_required
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_rotatingworktype"), name="dispatch")
class RotatingWorkTypeList(HorillaListView):
    """
    list view of Rotating work types in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-list")
        self.actions = []
        if self.request.user.has_perm("base.change_rotatingworktype"):
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
                },
            )
        if self.request.user.has_perm("base.delete_rotatingworktype"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.rotatingworktype&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = RotatingWorkType
    filter_class = RotatingWorkTypeFilter

    row_attrs = """
                id="rotatingWorkTypeTr{get_delete_instance}"
                """

    columns = [
        (_("Title"), "name"),
        (_("Work Type 1"), "work_type1"),
        (_("Work Type 2"), "work_type2"),
        (_("Additional Work Types"), "get_additional_worktytpes"),
    ]

    sortby_mapping = [
        ("Title", "name"),
        ("Work Type 1", "work_type1__work_type"),
        ("Work Type 2", "work_type2__work_type"),
        ("Additional Work Types", "get_additional_worktytpes"),
    ]

    header_attrs = {
        "name": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_rotatingworktype"), name="dispatch")
class RotatingWorkTypeNav(HorillaNavView):
    """
    navbar of Rotating worktype
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-list")
        if self.request.user.has_perm("base.add_rotatingworktype"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('rotating-work-type-create-form')}"
                                """

    nav_title = _("Rotating Work Type")
    search_swap_target = "#listContainer"
    filter_instance = RotatingWorkTypeFilter()


@method_decorator(manager_can_enter("base.add_rotatingworktype"), name="dispatch")
@method_decorator(login_required, name="dispatch")
class DynamicRotatingWorkTypeCreate(HorillaFormView):
    """
    form view for creating dynamic rotating work type
    """

    model = RotatingWorkType
    form_class = RotatingWorkTypeForm
    template_name = "cbv/rotating_work_type/forms/inherit.html"
    new_display_title = _("Create Rotating Work Type")
    is_dynamic_create_view = True

    def form_valid(self, form: RotatingWorkTypeForm) -> HttpResponse:
        if form.is_valid():
            form.save()
            messages.success(self.request, _("Rotating Work Type Created"))
            return self.HttpResponse("<script>$('#reloadMessagesbutton').click();")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.add_rotatingworktype"), name="dispatch")
class RotatingWorkTypesCreateForm(DynamicRotatingWorkTypeCreate):
    """
    form view for creating rotating work types in settings
    """

    is_dynamic_create_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class()

        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Rotating Work Type")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Work Type")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: RotatingWorkTypeForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Rotating Work Type Updated"))
            else:
                messages.success(self.request, _("Rotating Work Type Created"))
            form.save()
            return self.HttpResponse("")
        return super().form_valid(form)
