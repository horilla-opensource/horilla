"""
This page is handling the cbv methods of work type and shift tab in employee profile page.
"""

import json
from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.cbv.attendance_request import AttendanceRequestListTab
from attendance.cbv.hour_account import HourAccountList
from attendance.cbv.my_attendances import MyAttendancesListView
from attendance.filters import AttendanceFilters
from attendance.models import Attendance
from base.cbv.work_shift_tab import ProfileTabShellView
from base.methods import filtersubordinates
from base.request_and_approve import paginator_qry
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
)


@method_decorator(login_required, name="dispatch")
class AttendanceTabView(HorillaTabView):
    """
    generic tab view for attendance
    """

    # template_name = "cbv/work_shift_tab/extended_work-shift.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendance-container"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["emp_id"] = pk
        employee = Employee.objects.get(id=pk)
        context["instance"] = employee
        context["tabs"] = [
            {
                "title": _("Requested Attendances"),
                "url": f"{reverse('attendance-request-individual-tab-shell',kwargs={'pk': pk})}",
            },
            {
                "title": _("Validate Attendances"),
                "url": f"{reverse('validate-attendance-individual-tab',kwargs={'pk': pk})}",
            },
            {
                "title": _("All Attendances"),
                "url": f"{reverse('all-attendances-individual-tab',kwargs={'pk': pk})}",
            },
        ]
        return context


@method_decorator(login_required, name="dispatch")
class RequestedAttendanceIndividualView(AttendanceRequestListTab):
    """
    list view for requested attendance tab view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "attendance-request-individual-tab", kwargs={"pk": pk}
        )
        self.view_id = "attendance-requests-container"

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.request.resolver_match.kwargs.get("pk")
        queryset = self.model.objects.filter(
            employee_id=pk,
        )
        return queryset


class RequestedAttendanceIndividualTabShell(ProfileTabShellView):
    """
    Shell for the Requested Attendances profile tab.
    """

    shell_target_id = "attendance-requests-shell"
    nav_url_name = "attendance-request-individual-tab-nav"


@method_decorator(login_required, name="dispatch")
class RequestedAttendanceIndividualNav(HorillaNavView):
    """
    Minimal nav (Create button only) for the Requested Attendances profile
    tab - "Create Attendance Request" is self-service only, matching the
    original create_attendance_request_accessibility check (only the
    employee whose profile this is can raise a request from here).
    """

    template_name = "generic/inline_nav.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "attendance-request-individual-tab", kwargs={"pk": pk}
        )
        self.search_swap_target = "#attendance-requests-shell"
        employee = Employee.objects.filter(pk=pk).first()
        if employee and self.request.user == employee.employee_user_id:
            self.create_attrs = f"""
                hx-get="{reverse('request-new-attendance')}?emp_id={pk}"
                hx-target="#genericModalBody"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
            """

    nav_title = _("Requested Attendances")


@method_decorator(login_required, name="dispatch")
class HourAccountIndividualTabView(HourAccountList):
    """
    list view for hour account tab
    """

    template_name = "cbv/hour_account/hour_account_main.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "attendance-overtime-individual-tab", kwargs={"pk": pk}
        )
        self.view_id = "ot-table"

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = self.model.objects.filter(employee_id=pk)
        return queryset


@method_decorator(login_required, name="dispatch")
class AllAttendancesList(MyAttendancesListView):

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["search_url"] = (
            f"{reverse('all-attendances-individual-tab',kwargs={'pk': pk})}"
        )
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = self.model.objects.filter(employee_id=pk)
        return queryset
