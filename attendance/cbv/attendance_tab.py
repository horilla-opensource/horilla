"""
This page is handling the cbv methods of work type and shift tab in employee profile page.
"""

import json
from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from attendance.cbv.attendance_request import AttendanceRequestListTab
from attendance.cbv.hour_account import HourAccountList
from attendance.cbv.my_attendances import MyAttendancesListView
from attendance.filters import AttendanceFilters
from attendance.models import Attendance
from base.methods import filtersubordinates
from base.request_and_approve import paginator_qry
from employee.models import Employee
from horilla_views.generic.cbv.views import HorillaListView, HorillaTabView


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
                "url": f"{reverse('attendance-request-individual-tab',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Create Attendance Request",
                        "accessibility": "attendance.cbv.accessibility.create_attendance_request_accessibility",
                        "attrs": f"""
                                hx-get="{reverse('request-new-attendance')}?emp_id={pk}",
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                    }
                ],
            },
            {
                "title": _("Validate Attendances"),
                "url": f"{reverse('validate-attendance-individual-tab',kwargs={'pk': pk})}",
            },
            {
                "title": _("Hour Account"),
                "url": f"{reverse('attendance-overtime-individual-tab',kwargs={'pk': pk})}",
            },
            {
                "title": _("All Attendances"),
                "url": f"{reverse('all-attendances-individual-tab',kwargs={'pk': pk})}",
            },
        ]
        return context


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
        queryset = HorillaListView.get_queryset(self)
        pk = self.request.resolver_match.kwargs.get("pk")
        queryset = queryset.filter(
            employee_id__employee_user_id=pk,
            is_validate_request=True,
        )
        return queryset


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
        queryset = queryset.filter(employee_id=pk)
        return queryset


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
        queryset = queryset.filter(employee_id=pk)
        return queryset
