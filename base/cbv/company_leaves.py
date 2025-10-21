"""
this page is handling the cbv methods of company leaves page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import CompanyLeaveFilter
from base.forms import CompanyLeaveForm
from base.models import CompanyLeaves
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
class CompanyLeavesView(TemplateView):
    """
    for page view
    """

    template_name = "cbv/company_leaves/company_leave_home.html"


@method_decorator(login_required, name="dispatch")
class CompanyleaveListView(HorillaListView):
    """
    list view
    """

    filter_class = CompanyLeaveFilter
    model = CompanyLeaves

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("company-leave-filter")
        self.view_id = "companyleavedelete"

        if self.request.user.has_perm("base.view_companyleave"):
            self.action_method = "company_leave_actions"

        if self.request.user.has_perm("base.view_company"):
            if (_("Company"), "company_id") not in self.columns:
                self.columns.append((_("Company"), "company_id"))

    columns = [
        (_("Based On Week"), "custom_based_on_week"),
        (_("Based On Week Day"), "based_on_week_day_col"),
    ]

    header_attrs = {
        "action": """ style="width:200px !important;" """,
    }

    sortby_mapping = [
        ("Based On Week", "custom_based_on_week"),
        ("Based On Week Day", "based_on_week_day_col"),
    ]

    row_attrs = """
        hx-get='{detail_view}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


@method_decorator(login_required, name="dispatch")
class CompanyLeaveNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("company-leave-filter")
        if self.request.user.has_perm("add_companyleave"):
            self.create_attrs = f"""
                hx-get="{reverse_lazy('company-leave-creation')}"
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
            """

    nav_title = _("Company Leaves")
    filter_body_template = "cbv/company_leaves/company_leave_filter.html"
    filter_form_context_name = "form"
    filter_instance = CompanyLeaveFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
class CompanyLeaveDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    model = CompanyLeaves
    title = _("Details")
    header = {"title": "get_detail_title", "subtitle": "", "avatar": "get_avatar"}
    body = [
        (_("Based On Week"), "custom_based_on_week"),
        (_("Based On Week Day"), "based_on_week_day_col"),
        (_("Company"), "company_id"),
    ]
    action_method = "detail_view_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("leave.add_companyleave"), name="dispatch")
class CompanyleaveFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = CompanyLeaveForm
    model = CompanyLeaves
    new_display_title = _("Create Company Leaves")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Company Leaves")

        return context

    def form_valid(self, form: CompanyLeaveForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Company Leave Updated Successfully")
            else:
                message = _("New Company Leave Created Successfully")
            form.save()

            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
