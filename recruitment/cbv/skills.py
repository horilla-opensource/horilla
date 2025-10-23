"""
this page is handling the cbv methods for skills in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from recruitment.filters import SkillsFilter
from recruitment.forms import SkillsForm
from recruitment.models import Skill


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class SkillsListView(HorillaListView):
    """
    list view of the skills in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("skills-list-view")

    model = Skill
    filter_class = SkillsFilter
    show_toggle_form = False

    columns = [(_("Skill"), "title")]

    row_attrs = """ id="skillsTr{get_delete_instance}" """

    actions = [
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
        {
            "action": _("Delete"),
            "icon": "trash-outline",
            "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100 text-danger"
                        hx-post="{get_delete_url}"
                        hx-swap="delete"
                        hx-confirm="Are you sure want to delete this skill?"
                        hx-target="#skillsTr{get_delete_instance}"
                      """,
        },
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class SkillsNavView(HorillaNavView):
    """
    navbar of skills view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("skills-list-view")
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('settings-create-skills')}"
                            """

    nav_title = _("Skills")
    search_swap_target = "#listContainer"
    filter_instance = SkillsFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.add_recruitment"), name="dispatch"
)
class SkillsCreateForm(HorillaFormView):
    """
    form view for creating and update skills in settings
    """

    model = Skill
    form_class = SkillsForm
    new_display_title = _("Skills")

    def get_context_data(self, **kwargs):
        """
        Add form to context, initializing with instance if it exists.
        """
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Skills")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        """
        Handles and renders form errors or defers to superclass.
        """
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Skills")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: SkillsForm) -> HttpResponse:
        """
        Handle valid form submission.
        """
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Skill updated"))
            else:
                messages.success(self.request, _("Skill created successfully!"))
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)
