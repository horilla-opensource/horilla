"""
This page is handling the cbv methods of leave tab in employee profile page.
"""

from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.methods import is_reportingmanager
from employee.models import Employee
from leave.cbv.my_leave_request import MainParentListView, MyLeaveRequestListView


class IndividualLeaveTab(MainParentListView):
    """
    class for rendering leave tab in employee profile
    """

    template_name = "cbv/employee_individual/leave_tab.html"

    def get_context_data(self, **kwargs: Any):
        """
        context data
        """
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        employee = Employee.objects.get(id=pk)
        user_leave = employee.available_leave.all()

        if self.request.user.employee_get == employee:
            context["user_leaves"] = user_leave
        else:
            context["employee_leaves"] = user_leave
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "leave-tab"
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("individual-leave-tab-list", kwargs={"pk": pk})
        if self.request.user.has_perm(
            "leave.change_leaverequest"
        ) or is_reportingmanager(self.request):
            self.action_method = "confirmation_col"
        else:
            self.action_method = None

    columns = [
        col for col in MyLeaveRequestListView.columns if col[1] != "comment_action"
    ]

    # option_method = None
    # row_status_indications = None
