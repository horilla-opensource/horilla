"""
Question Template page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.methods import is_reportingmanager
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from pms.filters import PeriodFilter
from pms.forms import PeriodForm
from pms.models import Period


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_period"), name="dispatch")
class PeriodView(TemplateView):
    """
    for period page
    """

    template_name = "cbv/period/period.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_period"), name="dispatch")
class PeriodList(HorillaListView):
    """
    List view of the question template page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.search_url = reverse("period-hx-view")
        self.action_method = "action_col"
        self.view_id = "periodListTable"

    model = Period
    filter_class = PeriodFilter

    columns = [
        (_("Title"), "period_name"),
        (_("Start Date"), "start_date"),
        (_("End date"), "end_date"),
    ]

    header_attrs = {
        "action": """
                   style = "width:180px !important"
                   """,
        "period_name": """
                   style = "width:180px !important"
                   """,
    }

    sortby_mapping = [
        ("Start Date", "start_date"),
        ("End date", "end_date"),
    ]

    row_attrs = """
                hx-get='{detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_period"), name="dispatch")
class PeriodNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("period-hx-view")
        if self.request.user.has_perm("pms.add_period") or is_reportingmanager(
            self.request
        ):
            self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('period-create')}"
                            """

    nav_title = _("Period")
    filter_instance = PeriodFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_period"), name="dispatch")
class PeriodDetailView(HorillaDetailedView):
    """
    detail view of page
    """

    model = Period
    title = _("Details")

    header = {"title": "period_name", "subtitle": "", "avatar": ""}

    body = {
        (_("Title"), "period_name"),
        (_("Start Date"), "start_date"),
        (_("End date"), "end_date"),
        (_("Company"), "company_id_detail"),
    }
    action_method = "detail_view_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.add_period"), name="dispatch")
class PeriodFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = Period
    form_class = PeriodForm
    new_display_title = _("Create Period")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Period")
        return context

    def form_valid(self, form: PeriodForm) -> HttpResponse:

        if form.is_valid():
            if form.instance.pk:
                message = _("Period Updated Successfully")
            else:
                message = _("Period Created Successfully")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
