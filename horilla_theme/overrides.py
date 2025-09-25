from django.apps import apps
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import render_template


class DummyModel:
    """A dummy fallback class that behaves like a model placeholder."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        # if you try to access any attribute, just return another dummy
        return DummyModel()

    def __call__(self, *args, **kwargs):
        # acts callable (like a model manager/queryset)
        return DummyModel()


def get_horilla_model_class(app_label, model):
    try:
        return apps.get_model(app_label, model)
    except LookupError:
        return DummyModel


Recruitment = get_horilla_model_class(app_label="recruitment", model="recruitment")
AttendanceLateComeEarlyOut = get_horilla_model_class(
    app_label="attendance", model="attendancelatecomeearlyOut"
)
Attendance = get_horilla_model_class(app_label="attendance", model="attendance")
LeaveRequest = get_horilla_model_class(app_label="leave", model="leaverequest")
Meetings = get_horilla_model_class(app_label="pms", model="Meetings")
ResignationLetter = get_horilla_model_class(
    app_label="offboarding", model="ResignationLetter"
)
AssetAssignment = get_horilla_model_class(app_label="asset", model="AssetAssignment")
TimeSheet = get_horilla_model_class(app_label="project", model="TimeSheet")


def tot_hires(self):
    """
    This method for get custom column for Total hires.
    """

    col = f"""
        {self.total_hires()} Hired of {self.candidate.all().count()} Candidates
    """

    return col


def managers_detail(self):
    """
    manager in detail view
    """
    employees = self.recruitment_managers.all()
    employee_names_string = ""
    if employees:
        employee_names_string = ",<br />".join(
            [str(employee) for employee in employees]
        )

    return employee_names_string


def open_job_detail(self):
    """
    open jobs in detail view
    """
    jobs = self.open_positions.all()
    jobs_names_string = ""

    if jobs:
        jobs_names_string = ",<br />".join([str(job) for job in jobs])

    return jobs_names_string


def penalities_column(self):
    """
    Returns an HTML snippet showing penalty status with Tailwind styling.
    """

    penalties_count = self.get_penalties_count()

    if penalties_count:
        url = reverse("view-penalties") + f"?late_early_id={self.id}"
        return format_html(
            '<div class="bg-red-100/10 border-2 border-red-300 rounded-xl px-4 py-2 w-32 text-xs text-center text-red-700 font-semibold" '
            'data-target="#penaltyViewModal" data-toggle="oh-modal-toggle" '
            'onclick="event.stopPropagation();"'
            'hx-get="{}" hx-target="#penaltyViewModalBody" align="center">'
            "Penalties :{}</div>",
            url,
            penalties_count,
        )
    else:
        return format_html(
            '<div class="bg-green-100/10 border-2 border-green-300 rounded-xl px-4 py-2 w-32 text-xs text-center text-green-700 font-semibold">'
            "No Penalties</div>"
        )


def rejected_action(self):
    if self.reject_reason:
        if self.status == "cancelled":
            label = _("Reason for Cancellation")
        else:
            label = _("Reason for Rejection")
        return format_html(
            """
                <div class="w-full p-4 rounded-lg bg-orange-100/20 border border-orange-300 rounded-md">
                    <div>
                        <span class="block text-xs font-medium text-gray-700 mb-1">{}</span>
                        <div class="text-sm text-gray-800 italic">{}</div>
                    </div>
                </div>
            """,
            label,
            self.reject_reason,
        )
    return ""


def attachment_action(self):
    if self.attachment:
        return format_html(
            """
            <a href="{}" target="_blank" class="w-50 bg-gray-100 p-4 flex items-center text-gray-700 text-sm font-medium">
                <ion-icon name="download-outline" class="me-1 text-lg"></ion-icon>
                <span class="ml-1">{}</span>
            </a>
            """,
            self.attachment.url,
            _("View attachment"),
        )
    return ""


def attendance_detail_activity_col(self):
    activity_count = self.activities().get("count", 0)

    if activity_count == 0:
        return ""

    label = _("Activities:")
    view_label = _("View Activities")
    count_label = _("Activity") if activity_count == 1 else _("Activities")

    url = reverse("get-attendance-activities", args=[self.id])

    col = format_html(
        """
        <div class="mb-2 flex gap-5 items-center">
            <span class="font-medium text-xs text-[#565E6C] w-32">
                {}
            </span>
            <p class="text-xs font-semibold flex items-center gap-5">
                : <span>
                    <button
                        data-target="#activityViewModal"
                        data-toggle="oh-modal-toggle"
                        hx-get="{}"
                        hx-target="#activityViewModalBody"
                        title="{}"
                        class="flex items-center text-primary-600 text-sm font-semibold transition-colors"
                    >
                        <span>{} {}</span>
                        <ion-icon name="eye-outline" class="text-lg ml-2 mt-[2px]"></ion-icon>
                    </button>
                </span>
            </p>
        </div>
        """,
        label,
        url,
        view_label,
        activity_count,
        count_label,
    )

    return col


def leave_clash_col(self):
    count = self.leave_clashes_count

    label = _("View Clashes")
    url = reverse("view-clashes", args=[self.id])

    col = format_html(
        """
            <div onclick="event.stopPropagation();">
                <div class="flex "
                    data-target="#clashModal"
                    data-toggle="oh-modal-toggle"
                    hx-get="{}"
                    hx-target="#clashModalBody"
                    title="{}">

                    <i class="material-icons text-4xl" >groups</i>
                    <span class="w-5 h-5 bg-[#e54f38] rounded-full text-white text-xs font-semibold flex items-center justify-center">{}</span>
                </div>
            </div>
        """,
        url,
        label,
        count,
    )

    return col


def mom_detail_col(self):

    return render_template(
        path="cbv/meetings/mom_detail_col.html",
        context={"instance": self},
    )


def detail_description_col(self):

    return render_template(
        path="cbv/exit_process/detail_page_description.html",
        context={"instance": self},
    )


def assign_condition_img(self):
    images = self.assign_images.all()

    if not images:
        return ""

    label = _("Assign Condition Images")

    links_html = format_html_join(
        "",
        """
        <a href="{}" rel="noopener noreferrer" target="_blank">
            <span
                class="oh-file-icon oh-file-icon--pdf"
                onmouseover="enlargeattachment('{}')"
                style="width:40px;height:40px"
            ></span>
        </a>
        """,
        ((doc.image.url, doc.image.url) for doc in images),
    )

    col = format_html(
        """
        <div class="mb-2">
            <span class="font-medium text-xs text-[#565E6C] w-32">
                {}
            </span>
            <div class="d-flex mt-2 mb-2 gap-2">
                {}
            </div>
        </div>
        """,
        label,
        links_html,
    )

    return col


def return_condition_img(self):
    images = self.return_images.all()

    if not images:
        return ""

    label = _("Return Condition Images")

    links_html = format_html_join(
        "",
        """
        <a href="{}" rel="noopener noreferrer" target="_blank">
            <span
                class="oh-file-icon oh-file-icon--pdf"
                onmouseover="enlargeattachment('{}')"
                style="width:40px;height:40px"
            ></span>
        </a>
        """,
        ((doc.image.url, doc.image.url) for doc in images),
    )

    col = format_html(
        """
        <div class="mb-2 ">
            <span class="font-medium text-xs text-[#565E6C] w-32">
                {}
            </span>
            <div class="d-flex mt-2 mb-2 gap-2">
                {}
            </div>
        </div>
        """,
        label,
        links_html,
    )

    return col


def detail_view_subtitle(self):
    """
    for subtitle in detail view
    """
    col = format_html(
        """
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 rounded-md bg-white text-sm text-gray-700">

                    <div>
                        <span class="text-gray-500 mb-2">Date</span><br />
                        <span class="font-semibold">{}</span>
                    </div>

                    <div>
                        <span class="text-gray-500 mb-2">Time Spent</span><br />
                        <span class="font-semibold">{}</span>
                    </div>

                    <div>
                        <span class="text-gray-500 mb-2">Project</span><br />
                        <span class="font-semibold">{}</span>
                    </div>

                    <div>
                        <span class="text-gray-500 mb-2">Task</span><br />
                        <span class="font-semibold">{}</span>
                    </div>


                </div>
            """,
        self.date,
        self.time_spent,
        self.project_id,
        self.task_id,
    )

    return col


def detail_view_title(self):

    col = format_html(
        """
            <div class="flex items-center gap-5 mb-5">

                <div>
                    <img src="{}" alt="" class="w-[50px] h-[50px] rounded-full">
                </div>

                <div>
                    <p class="mb-1 text-sm font-semibold">
                        {}
                    </p>
                </div>
            </div>
        """,
        self.employee_id.get_avatar(),
        self.employee_id.get_full_name(),
    )

    return col


Recruitment.managers_detail = managers_detail
Recruitment.open_job_detail = open_job_detail
Recruitment.tot_hires = tot_hires

AttendanceLateComeEarlyOut.penalities_column = penalities_column
Attendance.attendance_detail_activity_col = attendance_detail_activity_col

LeaveRequest.rejected_action = rejected_action
LeaveRequest.attachment_action = attachment_action
LeaveRequest.penality_col = penalities_column
LeaveRequest.leave_clash_col = leave_clash_col

Meetings.mom_detail_col = mom_detail_col

ResignationLetter.detail_description_col = detail_description_col

AssetAssignment.assign_condition_img = assign_condition_img
AssetAssignment.return_condition_img = return_condition_img

TimeSheet.detail_view_subtitle = detail_view_subtitle
TimeSheet.detail_view_title = detail_view_title


from base.cbv.dashboard.dashboard import DashboardWorkTypeRequest, ShiftRequestToApprove
from employee.cbv.disciplinary_actions import DisciplinaryActionsList

_shift_request_to_approve_init_orig = ShiftRequestToApprove.__init__


def _shift_request_to_approve_init(self, **kwargs):
    _shift_request_to_approve_init_orig(self, **kwargs)
    self.header_attrs = {}


_work_type_request_to_approve_init_orig = DashboardWorkTypeRequest.__init__


def _work_type_request_to_approve_init(self, **kwargs):
    _work_type_request_to_approve_init_orig(self, **kwargs)
    self.header_attrs = {}


_disciplinary_action_list_init_orig = DisciplinaryActionsList.__init__


def _disciplinary_action_list_init(self, **kwargs):
    _disciplinary_action_list_init_orig(self, **kwargs)
    self.row_attrs = """
        class ="oh-sticky-table__tr oh-permission-table--collapsed"
        hx-get='{dis_action_detail_view}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


ShiftRequestToApprove.__init__ = _shift_request_to_approve_init
DashboardWorkTypeRequest.__init__ = _work_type_request_to_approve_init
DisciplinaryActionsList.__init__ = _disciplinary_action_list_init


if apps.is_installed("pms"):
    from pms.cbv.meetings import MeetingsDetailedView

    _meeting_detailed_init_orig = MeetingsDetailedView.__init__

    def _meeting_detailed_init(self, **kwargs):
        _meeting_detailed_init_orig(self, **kwargs)
        self.body = [
            (_("Date"), "date"),
            (_("Question Template"), "question_template"),
            (_("Employees"), "employ_detail_col"),
            (_("Managers"), "manager_detail_col"),
            (_("Answerable employees"), "answerable_col"),
            (_("Minutes of Meeting"), "mom_detail_col", True),
        ]

    MeetingsDetailedView.__init__ = _meeting_detailed_init


if apps.is_installed("offboarding"):
    from offboarding.cbv.resignation import ResignationLetterDetailView

    _resignation_detailed_init_orig = ResignationLetterDetailView.__init__

    def _resignation_detailed_init(self, **kwargs):
        _resignation_detailed_init_orig(self, **kwargs)
        self.body = [
            (_("Planned To Leave"), "planned_to_leave_on"),
            (_("Status"), "get_status"),
            (_("Description"), "detail_description_col", True),
        ]
        self.cols = {
            "detail_description_col": 12,
        }

    ResignationLetterDetailView.__init__ = _resignation_detailed_init


if apps.is_installed("project"):
    from project.cbv.timesheet import (
        TimeSheetCardView,
        TimeSheetDetailView,
        TimeSheetList,
        TimeSheetNavView,
    )

    _timesheet_nav_init_orig = TimeSheetNavView.__init__

    def _timesheet_nav_init(self, **kwargs):
        _timesheet_nav_init_orig(self, **kwargs)
        url = f"{reverse('personal-time-sheet-view',kwargs={'emp_id': self.request.user.employee_get.id})}"
        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("time-sheet-list"),
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("time-sheet-card"),
            },
            {
                "type": "graph",
                "icon": "bar-chart",
                "url": url,
            },
        ]

    _timesheet_list_init_orig = TimeSheetList.__init__

    def _timesheet_list_init(self, **kwargs):
        _timesheet_list_init_orig(self, **kwargs)
        self.row_attrs = """
            hx-get='{detail_view}?instance_ids={ordered_ids}'
            hx-target="#objectDetailsModalTarget"
            data-target="#objectDetailsModal"
            data-toggle="oh-modal-toggle"
        """

    _timesheet_card_init_orig = TimeSheetCardView.__init__

    def _timesheet_card_init(self, **kwargs):
        _timesheet_card_init_orig(self, **kwargs)
        self.card_attrs = """
            hx-get='{detail_view}?instance_ids={ordered_ids}'
            hx-target="#objectDetailsModalTarget"
            data-target="#objectDetailsModal"
            data-toggle="oh-modal-toggle"
        """

        self.details = {
            "title": "{detail_view_title}",
            "subtitle": "{detail_view_subtitle}",
        }

    _timesheet_detail_init_orig = TimeSheetDetailView.__init__

    def _timesheet_detail_init(self, **kwargs):
        _timesheet_detail_init_orig(self, **kwargs)
        self.cols = {
            "description": 12,
        }

    TimeSheetNavView.__init__ = _timesheet_nav_init
    TimeSheetList.__init__ = _timesheet_list_init
    TimeSheetCardView.__init__ = _timesheet_card_init
    TimeSheetDetailView.__init__ = _timesheet_detail_init


if apps.is_installed("attendance"):
    from attendance.cbv.dashboard import (
        DashboardaAttendanceOT,
        DashboardAttendanceToValidate,
    )

    _overtime_attendance_init_orig = DashboardaAttendanceOT.__init__

    def _overtime_attendance_init(self, **kwargs):
        _overtime_attendance_init_orig(self, **kwargs)
        self.header_attrs = {}

    _validate_attendance_init_orig = DashboardAttendanceToValidate.__init__

    def _validate_attendance_init(self, **kwargs):
        _validate_attendance_init_orig(self, **kwargs)
        self.header_attrs = {}

    DashboardaAttendanceOT.__init__ = _overtime_attendance_init
    DashboardAttendanceToValidate.__init__ = _validate_attendance_init


if apps.is_installed("leave"):
    from leave.cbv.dashboard import LeaveRequestsToApprove

    _leave_request_to_approve_init_orig = LeaveRequestsToApprove.__init__

    def _leave_request_to_approve_init(self, **kwargs):
        _leave_request_to_approve_init_orig(self, **kwargs)
        self.header_attrs = {}

    LeaveRequestsToApprove.__init__ = _leave_request_to_approve_init
