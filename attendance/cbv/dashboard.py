"""
this page handles the cbv methods for dashboard
"""

from datetime import datetime
from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.cbv.attendances import OTAttendancesList, ValidateAttendancesList
from attendance.filters import LateComeEarlyOutFilter
from attendance.methods.utils import strtime_seconds
from attendance.models import AttendanceLateComeEarlyOut, AttendanceValidationCondition
from base.methods import filtersubordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView


@method_decorator(login_required, name="dispatch")
class DashboardAttendanceToValidate(ValidateAttendancesList):
    """
    list view for attendance to validate in dashboard
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-attendance-validate")
        self.option_method = ""

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Attendance Date"), "attendance_date"),
        (_("Worked Hours"), "attendance_worked_hour"),
    ]

    header_attrs = {
        "attendance_worked_hour": """style="width:100px !important;" """,
        "employee_id": """ style="width:100px !important;" """,
        "action": """ style="width:100px !important;" """,
    }

    records_per_page = 5
    bulk_select_option = False
    show_toggle_form = False


@method_decorator(login_required, name="dispatch")
class DashboardaAttendanceOT(OTAttendancesList):
    """
    list view for OT attendance to validate in dashboard
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-overtime-approve")
        self.option_method = ""

    def get_queryset(self):
        queryset = super().get_queryset()
        condition = AttendanceValidationCondition.objects.first()
        minot = strtime_seconds("00:00")
        if condition is not None and condition.minimum_overtime_to_approve is not None:
            minot = strtime_seconds(condition.minimum_overtime_to_approve)
        queryset = queryset.filter(
            overtime_second__gte=minot,
            attendance_validated=True,
            employee_id__is_active=True,
            attendance_overtime_approve=False,
        )
        queryset = filtersubordinates(
            self.request, queryset, "attendance.view_attendance"
        )
        return queryset

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Attendance Date"), "attendance_date"),
        (_("Overtime"), "attendance_overtime"),
    ]
    header_attrs = {
        "action": """ style="width:100px !important;" """,
        "attendance_overtime": """ style="width:100px !important;" """,
        "employee_id": """ style="width:100px !important;" """,
    }

    show_toggle_form = False
    records_per_page = 5
    bulk_select_option = False


@method_decorator(login_required, name="dispatch")
class DashboardOnBreak(HorillaListView):
    """
    view for on break employee list
    """

    model = AttendanceLateComeEarlyOut
    filter_class = LateComeEarlyOutFilter
    show_toggle_form = False

    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-on-break")

    def get_queryset(self):
        queryset = super().get_queryset()
        today = datetime.today()
        queryset = queryset.filter(
            type="early_out", attendance_id__attendance_date=today
        )
        return queryset

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
    ]
