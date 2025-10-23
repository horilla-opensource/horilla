"""
this page is handling the cbv methods for Audit tags in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import AuditTagForm
from horilla.decorators import permission_required
from horilla_audit.filters import AudiTagFilter
from horilla_audit.models import AuditTag
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("horilla_audit.view_audittag"), name="dispatch")
class AudiTagsList(HorillaListView):
    """
    list view of the audit tags in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("audit-tag-list")

    model = AuditTag
    filter_class = AudiTagFilter
    show_toggle_form = False

    bulk_update_fields = ["highlight"]

    columns = [
        (_("Title"), "title"),
        (_("Highlight"), "custom_highlight_col"),
    ]

    row_attrs = """ id="auditTagTr{get_delete_instance}" """

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
                hx-confirm="Are you sure you want to delete this history tag ?"
                hx-post="{get_delete_url}"
                hx-target="#auditTagTr{get_delete_instance}"
                hx-swap="delete"
            """,
        },
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("horilla_audit.view_audittag"), name="dispatch")
class AuditTagsNavView(HorillaNavView):
    """
    navbar of audit tags view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("audit-tag-list")
        self.create_attrs = f"""
            onclick = "event.stopPropagation();"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            hx-target="#genericModalBody"
            hx-get="{reverse('settings-audit-tag-create')}"
        """

    nav_title = _("History Tags")
    search_swap_target = "#listContainer"
    filter_instance = AudiTagFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("horilla_audit.add_audittag"), name="dispatch")
class AuditTagCreateForm(HorillaFormView):
    """
    form view for creating and update Audit Tag in settings
    """

    model = AuditTag
    form_class = AuditTagForm
    new_display_title = _("Create Audit Tag")

    def get_context_data(self, **kwargs):
        """
        Add form to context, initializing with instance if it exists.
        """
        context = super().get_context_data(**kwargs)
        form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Audit Tag Update")
        context[form] = form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        """
        Handles and renders form errors or defers to superclass.
        """
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Audit Tag Update")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: AuditTagForm) -> HttpResponse:
        """
        Handle valid form submission.
        """
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("Tag has been updated successfully!"))
            else:
                messages.success(self.request, _("Tag has been created successfully!"))
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)
