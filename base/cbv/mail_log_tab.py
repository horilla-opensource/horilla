"""
This page is handling the cbv methods of mail log tab in employee individual page.
"""

from typing import Any

from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from accessibility.cbv_decorators import enter_if_accessible
from base.filters import MailLogFilter
from base.models import EmailLog
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaListView


def _check_reporting_manager(request, *args, **kwargs):
    return request.user.employee_get.reporting_manager.exists()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="view_mail_log",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class MailLogTabList(HorillaListView):
    """
    list view for mail log  tab
    """

    model = EmailLog
    records_per_page = 5
    filter_class = MailLogFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "maillog"

        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("individual-email-log-list", kwargs={"pk": pk})

    # def get_context_data(self, **kwargs: Any):
    #     context = super().get_context_data(**kwargs)
    #     pk = self.kwargs.get('pk')
    #     context["search_url"] = f"{reverse('individual-email-log-list',kwargs={'pk': pk})}"
    #     return context

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        employee = Employee.objects.get(id=pk)
        query_filter = Q(to__icontains=employee.email)
        queryset = queryset.filter(to__icontains=employee.email)
        if employee.employee_work_info and employee.employee_work_info.email:
            query_filter |= Q(to__icontains=employee.employee_work_info.email)
            queryset = queryset.filter(query_filter)
            queryset = queryset.order_by("-created_at")

        return queryset

    columns = [
        (_("Subject"), "subject"),
        (_("Date"), "created_at"),
        (_("Status"), "status_display"),
    ]

    sortby_mapping = [
        (_("Subject"), "subject"),
        (_("Date"), "created_at"),
    ]

    row_attrs = """
                hx-get='{mail_log_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    enter_if_accessible(
        feature="view_mail_log",
        perm="employee.view_employee",
        method=_check_reporting_manager,
    ),
    name="dispatch",
)
class MailLogDetailView(HorillaDetailedView):
    """
    detail view for mail log tab
    """

    template_name = "cbv/mail_log_tab/iframe.html"
    model = EmailLog

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        log = EmailLog.objects.filter(id=pk).first()
        context["log"] = log
        return context

    header = {"title": "", "subtitle": "", "avatar": ""}
