"""
this page is handling the cbv methods of  attendance activity page
"""

from typing import Any

from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.filters import AttendanceActivityFilter
from attendance.forms import AttendanceActivityExportForm
from attendance.models import AttendanceActivity
from base.methods import filtersubordinates, is_reportingmanager
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
class AttendanceActivityView(TemplateView):
    """
    for my attendance page view
    """

    template_name = "cbv/attendance_activity/attendance_activity_home.html"


@method_decorator(login_required, name="dispatch")
class AttendanceActivityListView(HorillaListView):
    """
    list view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendance-activity-search")
        self.action_method = None
        self.view_id = "deleteview"
        if self.request.user.has_perm("attendance.delete_attendanceactivity"):
            self.action_method = "get_delete_attendance"

    def get_queryset(self):
        queryset = super().get_queryset()
        self_attendance_activities = queryset.filter(
            employee_id__employee_user_id=self.request.user
        )
        queryset = filtersubordinates(
            self.request, queryset, "attendance.view_attendanceactivity"
        )
        return queryset | self_attendance_activities

    filter_class = AttendanceActivityFilter
    model = AttendanceActivity
    records_per_page = 10
    template_name = "cbv/attendance_activity/delete_inherit.html"

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Attendance Date"), "attendance_date"),
        (_("In Date"), "clock_in_date"),
        (_("Check In"), "clock_in"),
        (_("Check Out"), "clock_out"),
        (_("Out Date"), "clock_out_date"),
        (_("Duration (HH:MM:SS)"), "duration_format"),
    ]

    row_attrs = """
                {diff_cell}
                hx-get='{attendance_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Attendance Date", "attendance_date"),
        ("Check In", "clock_in"),
        ("In Date", "clock_in_date"),
        ("Check Out", "clock_out"),
        ("Out Date", "clock_out_date"),
        ("Duration (HH:MM:SS)", "duration_format"),
    ]


@method_decorator(login_required, name="dispatch")
class AttendanceActivityNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendance-activity-search")

        actions = [
            {
                "action": _("Import"),
                "attrs": f"""
                    "id"="activityInfoImport"
                    data-toggle = "oh-modal-toggle"
                    data-target = "#objectCreateModal"
                    hx-target="#objectCreateModalTarget"
                    hx-get ="{reverse_lazy('attendance-activity-import')}"
                    style="cursor: pointer;"
                """,
            },
            {
                "action": _("Export"),
                "attrs": f"""
                    data-toggle = "oh-modal-toggle"
                    data-target = "#genericModal"
                    hx-target="#genericModalBody"
                    hx-get ="{reverse_lazy('attendance-bulk-export')}"
                    style="cursor: pointer;"
                """,
            },
        ]

        if self.request.user.has_perm("attendance.delete_attendanceactivity"):
            actions.append(
                {
                    "action": _("Delete"),
                    "attrs": """
                    onclick="
                    deleteAttendanceNav();
                    "
                    data-action ="delete"
                    style="cursor: pointer; color:red !important"
                """,
                }
            )
        if not self.request.user.has_perm(
            "attendance.delete_attendanceactivity"
        ) and not is_reportingmanager(self.request):
            actions = None
        self.actions = actions

    nav_title = _("Attendance Activity")
    filter_body_template = "cbv/attendance_activity/filter.html"
    filter_instance = AttendanceActivityFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", _("Employee")),
        ("attendance_date", _("Attendance Date")),
        ("clock_in_date", _("In Date")),
        ("clock_out_date", _("Out Date")),
        ("shift_day", _("Shift Day")),
        ("employee_id__country", _("Country")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__shift_id", _("Shift")),
        ("employee_id__employee_work_info__work_type_id", _("Work Type")),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employement Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
class AttendanceDetailView(HorillaDetailedView):
    """
    Detail view of page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendance-activity-search")

    model = AttendanceActivity

    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "attendance_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    body = [
        (_("Attendance Date"), "attendance_date"),
        (_("Day"), "get_status"),
        (_("Check In"), "clock_in"),
        (_("Check In Date"), "clock_in_date"),
        (_("Check Out"), "clock_out"),
        (_("Check Out Date"), "clock_out_date"),
        (_("Duration"), "duration_format"),
        (_("Shift"), "employee_id__employee_work_info__shift_id"),
        (_("Work Type"), "employee_id__employee_work_info__work_type_id"),
    ]
    action_method = "detail_view_delete_attendance"


@method_decorator(login_required, name="dispatch")
class AttendanceBulkExport(TemplateView):
    """
    for bulk export
    """

    template_name = "cbv/attendance_activity/attendance_export.html"

    def get_context_data(self, **kwargs: Any):
        """
        get data for export
        """
        attendances = AttendanceActivity.objects.all()
        export_form = AttendanceActivityExportForm
        export = AttendanceActivityFilter(queryset=attendances)
        context = super().get_context_data(**kwargs)
        context["export_form"] = export_form
        context["export"] = export
        return context
