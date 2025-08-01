"""
this page handles the cbv methods for online and offline employee list in dashboard
"""

from datetime import date
from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.cbv.attendances import OTAttendancesList, ValidateAttendancesList
from base.decorators import manager_can_enter
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class DashboardOfflineEmployees(HorillaListView):
    """
    list view for offline employees in dashboard
    """

    model = Employee
    filter_class = EmployeeFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("not-in-yet")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            EmployeeFilter({"not_in_yet": date.today()})
            .qs.exclude(employee_work_info__isnull=True)
            .filter(is_active=True)
        )

        return queryset

    columns = [
        ("Employee", "get_full_name", "get_avatar"),
        ("Work Status", "get_leave_status"),
        ("Actions", "send_mail_button"),
    ]
    header_attrs = {
        "get_full_name": """
        style="width:200px !important;"
        """,
        "send_mail_button": """
        style="width:80px !important;"
        """,
    }
    records_per_page = 7
    show_toggle_form = False
    bulk_select_option = False


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class DashboardOnlineEmployees(HorillaListView):
    """
    list view for online employees in dashboard
    """

    model = Employee
    filter_class = EmployeeFilter
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("not-out-yet")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            EmployeeFilter({"not_out_yet": date.today()})
            .qs.exclude(employee_work_info__isnull=True)
            .filter(is_active=True)
        )

        return queryset

    columns = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Work Status", "get_custom_forecasted_info_col"),
    ]

    header_attrs = {
        "employee_id__get_full_name": """ style="width:200px !important" """,
        "get_custom_forecasted_info_col": """ style="width:180px !important" """,
    }

    records_per_page = 8
    bulk_select_option = False
