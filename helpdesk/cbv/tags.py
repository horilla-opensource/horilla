"""
This page is handling the cbv methods for Ticket types in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import TagsForm
from base.models import Tags
from helpdesk.filter import TagsFilter
from helpdesk.forms import TicketTypeForm
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.view_tag"), name="dispatch")
class TagsListView(HorillaListView):
    """
    list view for tickets in settings
    """

    model = Tags
    filter_class = TagsFilter
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "tagContainer"
        self.search_url = reverse("helpdesk-tag-list")
        self.actions = [
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
                        hx-confirm="Are you sure you want to delete this tag ?"
                        hx-post="{get_delete_url}"
                        hx-target="#tagTr{get_instance_id}"
                        hx-swap="delete"
                        """,
            },
        ]

    columns = [(_("Title"), "title"), (_("Color"), "get_color")]

    header_attrs = {
        "title": """
                   style = "width:200px !important"
                   """,
    }

    sortby_mapping = [("Title", "title")]

    row_attrs = """
                id = "tagTr{get_instance_id}"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.view_tag"), name="dispatch")
class TagsNavView(HorillaNavView):
    """
    nav bar of the department view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("helpdesk-tag-list")
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('create-helpdesk-tag')}"
                            """

    nav_title = _("Helpdesk Tags")
    search_swap_target = "#listContainer"
    filter_instance = TagsFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="helpdesk.add_tag"), name="dispatch")
class TagsFormView(HorillaFormView):
    """
    Form view for creating and updating Helpdesk Tags.
    """

    model = Tags
    form_class = TagsForm
    new_display_title = _("Create Helpdesk Tag")

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Helpdesk Tag")
        context["form"] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        """
        Handle an invalid form submission.

        If the form is invalid, render the form with error messages.
        """
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Helpdesk Tag")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: TicketTypeForm) -> HttpResponse:
        """
        Handle a valid form submission.

        If the form is valid, save the instance and display a success message.
        """
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Tag has been updated successfully!"))
            else:
                messages.success(self.request, _("Tag has been created successfully!"))
            form.save()
            return self.HttpResponse()
            # return HttpResponse("<script>$(document).ready(function(e) { $('#addTagModal').toggleClass('oh-modal--show')});</script>")
            # return HttpResponse("<script>$('#addTagModal').find('.oh-modal--show').first().removeClass('.oh-modal--show');</script>")
        return super().form_valid(form)


class DynamicTagsCreateFormView(TagsFormView):

    is_dynamic_create_view = True
