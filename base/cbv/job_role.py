"""
this page is handling the cbv methods for Job role in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import JobRoleFilter
from base.forms import JobRoleForm
from base.models import JobPosition, JobRole
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_jobrole"), name="dispatch")
class JobRoleListView(HorillaListView):
    """
    List view of the page
    """

    columns = [
        (_("Job Position"), "job_position_col"),
        (_("Job Role"), "job_role_col"),
    ]
    header_attrs = {
        "job_position_col": 'style="width:300px !important;"',
        "job_role_col": 'style="width:300px !important;"',
    }

    row_attrs = """
        class = "oh-sticky-table__tr oh-permission-table__tr oh-permission-table--collapsed"
        data-count="{get_data_count}"
        data-label="Job Role"
    """

    model = JobPosition
    filter_class = JobRoleFilter
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "job_role"
        self.search_url = reverse("job-role-list")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_jobrole"), name="dispatch")
class JobRoleNav(HorillaNavView):
    """
    Nav bar
    """

    nav_title = _("Job Role")
    filter_instance = JobRoleFilter()
    search_swap_target = "#listContainer"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("job-role-list")
        if self.request.user.has_perm("base.add_jobrole"):
            self.create_attrs = f"""
                onclick = "event.stopPropagation();"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                hx-get="{reverse('create-job-role')}"
            """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.add_jobrole"), name="dispatch")
class JobRoleFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = JobRole
    form_class = JobRoleForm
    new_display_title = _("Create Job Role")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Job Role")
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: JobRoleForm) -> HttpResponse:
        if self.form.instance.pk and form.is_valid():
            instance = form.instance
            job_position = form.cleaned_data.get("job_position_id")
            instance.job_position_id = job_position
            instance.save()
            messages.success(self.request, _("Job role has been updated successfully!"))
        elif (
            not self.form.instance.pk
            and self.form.data.getlist("job_position_id")
            and self.form.data.get("job_role")
        ):
            form.save(commit=True)
        return self.HttpResponse()
