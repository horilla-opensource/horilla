"""
My attendances
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.filters import AttendanceFilters
from attendance.models import Attendance
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
class MyAttendances(TemplateView):
    """
    My attendances
    """

    template_name = "cbv/my_attendances/my_attendances.html"


class MyAttendancesListView(HorillaListView):

    model = Attendance
    filter_class = AttendanceFilters
    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Date"), "attendance_date"),
        (_("Day"), "attendance_day"),
        (_("Check-In"), "attendance_clock_in"),
        (_("In Date"), "attendance_clock_in_date"),
        (_("Check-Out"), "attendance_clock_out"),
        (_("Out Date"), "attendance_clock_out_date"),
        (_("Shift"), "shift_id"),
        (_("Work Type"), "work_type_id"),
        (_("Min Hour"), "minimum_hour"),
        (_("At Work"), "attendance_worked_hour"),
        (_("Pending Hour"), "hours_pending"),
        (_("Overtime"), "attendance_overtime"),
    ]

    row_attrs = """
                hx-get='{my_attendance_detail}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    records_per_page = 20

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "attendance_date"),
        ("Day", "attendance_day__day"),
        ("Check-In", "attendance_clock_in"),
        ("Shift", "shift_id__employee_shift"),
        ("Work Type", "work_type_id__work_type"),
        ("Min Hour", "minimum_hour"),
        ("Pending Hour", "hours_pending"),
        ("In Date", "attendance_clock_in_date"),
        ("Check-Out", "attendance_clock_out"),
        ("Out Date", "attendance_clock_out_date"),
        ("At Work", "attendance_worked_hour"),
        ("Overtime", "attendance_overtime"),
    ]


@method_decorator(login_required, name="dispatch")
class MyAttendanceList(MyAttendancesListView):
    """
    List view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("my-attendance-list")

    row_status_indications = [
        (
            "approved-request--dot",
            _("Approved Request"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_validate_request_approved]').val('true');
                $('[name=attendance_validated]').val('unknown').change();
                $('[name=is_validate_request]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "requested--dot",
            _("Requested"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_validate_request]').val('true');
                $('[name=attendance_validated]').val('unknown').change();
                $('[name=is_validate_request_approved]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "not-validated--dot",
            _("Not Validated"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=attendance_validated]').val('false');
                $('[name=is_validate_request]').val('unknown').change();
                $('[name=is_validate_request_approved]').val('unknown').change();
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "validated--dot",
            _("Validated"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=attendance_validated]').val('true');
                $('[name=is_validate_request]').val('unknown').change();
                $('[name=is_validate_request_approved]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    row_status_class = "validated-{attendance_validated}  requested-{is_validate_request} approved-request-{is_validate_request_approved}"

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(employee_id=employee)
        return queryset


@method_decorator(login_required, name="dispatch")
class MyAttendancestNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("my-attendance-list")
        self.search_in = [
            ("shift_id__employee_shift", "Shift"),
            ("work_type_id__work_type", "Work Type"),
        ]

    nav_title = _("My Attendances")
    filter_body_template = "cbv/my_attendances/my_attendance_filter.html"
    filter_instance = AttendanceFilters()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"
    search_input_attrs = """ hidden """


@method_decorator(login_required, name="dispatch")
class MyAttendancesDetailView(HorillaDetailedView):
    """
    Detail View
    """

    model = Attendance

    title = _("Details")

    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "my_attendance_subtitle",
        "avatar": "employee_id__get_avatar",
    }

    body = [
        (_("Date"), "attendance_date"),
        (_("Day"), "attendance_day"),
        (_("Check-In"), "attendance_clock_in"),
        (_("Check-in Date"), "attendance_clock_in_date"),
        (_("Check-Out"), "attendance_clock_out"),
        (_("Check-out Date"), "attendance_clock_out_date"),
        (_("Shift"), "shift_id"),
        (_("Work Type"), "work_type_id"),
        (_("Min Hour"), "minimum_hour"),
        (_("At Work"), "attendance_worked_hour"),
        (_("Pending Hour"), "hours_pending"),
        (_("Overtime"), "attendance_overtime"),
    ]
