"""
Attendance requests
"""

import json
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.filters import AttendanceFilters
from attendance.forms import (
    AttendanceRequestForm,
    BulkAttendanceRequestForm,
    NewRequestForm,
)
from attendance.methods.utils import get_employee_last_name
from attendance.models import Attendance
from base.methods import choosesubordinates, filtersubordinates, is_reportingmanager
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
class AttendancesRequestView(TemplateView):
    """
    for attendance request page
    """

    template_name = "cbv/attendance_request/attendance_request.html"


@method_decorator(login_required, name="dispatch")
class AttendancesRequestTabView(HorillaTabView):
    """
    tabview of attendance request page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendance-container"
        self.tabs = [
            {
                "title": _("Requested Attendances"),
                "url": f"{reverse('attendance-request-list-tab')}",
            },
            {
                "title": _("All Attendances"),
                "url": f"{reverse('attendance-list-tab')}",
            },
        ]


def request_approved_by(self):
    """
    Approve the attendance request
    """
    return self.approved_by if self.approved_by else "-"


Attendance.request_approved_by = request_approved_by


@method_decorator(login_required, name="dispatch")
class AttendancesRequestListView(HorillaListView):
    """
    list view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendance-request-tab")

    filter_class = AttendanceFilters
    model = Attendance
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
        (_("Overtime"), "attendance_overtime"),
        (_("Approved By"), "request_approved_by"),
    ]
    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "attendance_date"),
        ("In Date", "attendance_clock_in_date"),
        ("Out Date", "attendance_clock_out_date"),
        ("At Work", "attendance_worked_hour"),
        ("Overtime", "attendance_overtime"),
    ]
    row_status_indications = [
        (
            "bulk-request--dot",
            _("Bulk-Requests"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_bulk_request]').val('true');
                $('[name=attendance_validated]').val('unknown').change();
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
                $('[name=is_bulk_request]').val('unknown').change();
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
                $('[name=is_bulk_request]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    row_status_class = "validated-{attendance_validated}"


@method_decorator(login_required, name="dispatch")
class AttendanceRequestListTab(AttendancesRequestListView):
    """
    Attendance request tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendance-requests-container"

    template_name = "cbv/attendance_request/attendance_request_tab.html"

    columns = [
        col for col in AttendancesRequestListView.columns if col[1] != "status_col"
    ]

    action_method = "request_actions"
    row_attrs = """
                id = "requestedattendanceTr{get_instance_id}"
                data-attendance-id="{get_instance_id}"
                data-toggle="oh-modal-toggle"
                data-target="#validateAttendanceRequest"
                hx-get = "{detail_view}?instance_ids={ordered_ids}"
                hx-trigger ="click"
                hx-target="#validateAttendanceRequestModalBody"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        self_data = queryset
        queryset = queryset.filter(
            is_validate_request=True,
        )
        queryset = filtersubordinates(
            request=self.request,
            perm="attendance.view_attendance",
            queryset=queryset,
        )
        queryset = queryset | self_data.filter(
            employee_id__employee_user_id=self.request.user,
            is_validate_request=True,
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class AttendanceListTab(AttendancesRequestListView):
    """
    Attendance tab
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        data = queryset
        attendances = filtersubordinates(
            request=self.request,
            perm="attendance.view_attendance",
            queryset=queryset,
        )
        queryset = attendances | data.filter(
            employee_id__employee_user_id=self.request.user
        )
        queryset = queryset.filter(
            employee_id__is_active=True,
        )
        return queryset

    actions = [
        {
            "action": _("Edit"),
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-100"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{change_attendance}"
                hx-target="#genericModalBody"

                """,
        }
    ]

    row_attrs = """
                {diff_cell}
                id = "allattendanceTr{get_instance_id}"
                hx-get='{attendance_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                hx-trigger ="click"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
class AttendanceRequestNav(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendance-request-tab")
        self.create_attrs = f"""
                        data-toggle="oh-modal-toggle"
                        data-target="#genericModal"
                        hx-get="{reverse('request-new-attendance')}"
                        hx-target="#genericModalBody"
                        """
        if self.request.user.has_perm(
            "attendance.add_attendanceovertime"
        ) or is_reportingmanager(self.request):

            self.actions = [
                {
                    "action": _("Bulk Approve"),
                    "attrs": """
                        onclick="
                        reqAttendanceBulkApprove();
                        "
                        style="cursor: pointer;"
                    """,
                },
                {
                    "action": _("Bulk Reject"),
                    "attrs": """
                        onclick="reqAttendanceBulkReject();"
                        style="color:red !important"
                    """,
                },
            ]
        else:
            self.actions = None

    nav_title = _("Attendances")
    filter_body_template = "cbv/attendances/attendances_filter_page.html"
    filter_instance = AttendanceFilters()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", "Employee"),
        ("attendance_date", "Attendance Date"),
        ("attendance_clock_in_date", "In Date"),
        ("attendance_clock_out_date", "Out Date"),
        ("employee_id__country", "Country"),
        ("employee_id__employee_work_info__reporting_manager_id", "Reporting Manager"),
        ("shift_id", "Shift"),
        ("work_type_id", "Work Type"),
        ("minimum_hour", " Min Hour"),
        ("employee_id__employee_work_info__department_id", "Department"),
        ("employee_id__employee_work_info__job_position_id", "Job Position"),
        ("employee_id__employee_work_info__employee_type_id", "Employement Type"),
        ("employee_id__employee_work_info__company_id", "Company"),
    ]


@method_decorator(login_required, name="dispatch")
class AttendanceListTabDetailView(HorillaDetailedView):
    """
    Detail view of page
    """

    model = Attendance

    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "attendances_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    body = [
        (_("Date"), "attendance_date"),
        (_("Day"), "attendance_day"),
        (_("Check-In"), "attendance_clock_in"),
        (_("Check In Date"), "attendance_clock_in_date"),
        (_("Check-Out"), "attendance_clock_out"),
        (_("Check Out Date"), "attendance_clock_out_date"),
        (_("Shift"), "shift_id"),
        (_("Work Type"), "work_type_id"),
        (_("Min Hour"), "minimum_hour"),
        (_("At Work"), "attendance_worked_hour"),
        (_("Overtime"), "attendance_overtime"),
        (_("Approved By"), "request_approved_by"),
        (_("Activities"), "attendance_detail_activity_col", True),
    ]

    actions = [
        {
            "action": _("Edit"),
            "icon": "create-outline",
            "attrs": """
                    onclick="event.stopPropagation();"
                    class="oh-btn oh-btn--info w-100"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModalEdit"
                    hx-get="{change_attendance}?all_attendance=true"
                    hx-target="#genericModalEditBody"

                """,
        }
    ]


class NewAttendanceRequestFormView(HorillaFormView):
    """
    form view for create  attendance request
    """

    form_class = NewRequestForm
    model = Attendance
    new_display_title = _("New Attendance Request")
    template_name = "requests/attendance/request_form.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendanceRequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form = choosesubordinates(
            self.request, self.form, "attendance.change_attendance"
        )
        self.form.fields["employee_id"].queryset = (
            self.form.fields["employee_id"].queryset
        ).distinct() | (
            Employee.objects.filter(employee_user_id=self.request.user)
        ).distinct()
        self.form.fields["employee_id"].initial = self.request.user.employee_get.id
        if self.request.GET.get("emp_id"):
            emp_id = self.request.GET.get("emp_id")
            self.form.fields["employee_id"].queryset = Employee.objects.filter(
                id=emp_id
            )
            self.form.fields["employee_id"].initial = emp_id
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Attendance Request")
        return context

    def form_valid(self, form: NewRequestForm) -> HttpResponse:
        if form.is_valid():
            message = _("New Attendance request created")
            if form.new_instance is not None:
                form.new_instance.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


class BulkAttendanceRequestFormView(HorillaFormView):
    """
    form view for create bulk  attendance request
    """

    form_class = BulkAttendanceRequestForm
    model = Attendance
    new_display_title = _("New Attendance Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form = choosesubordinates(
            self.request, self.form, "attendance.change_attendance"
        )
        self.form.fields["employee_id"].queryset = self.form.fields[
            "employee_id"
        ].queryset | Employee.objects.filter(employee_user_id=self.request.user)
        self.form.fields["employee_id"].initial = self.request.user.employee_get.id
        return context

    def post(self, request, *args, pk=None, **kwargs):
        self.get_form()
        form = self.form
        form.instance.attendance_clock_in_date = self.request.POST.get("from_date")
        form.instance.attendance_date = self.request.POST.get("from_date")
        if form.is_valid():
            if form.instance.pk:
                message = _("New Attendance request updated")
            else:
                message = _("New Attendance request created")
                instance = form.save(commit=False)
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().post(request, *args, pk=pk, **kwargs)

    def form_valid(self, form: BulkAttendanceRequestForm) -> HttpResponse:
        form.instance.attendance_clock_in_date = self.request.POST.get("from_date")
        form.instance.attendance_date = self.request.POST.get("from_date")
        if form.is_valid():
            if form.instance.pk:
                message = _("New Attendance request updated")
            else:
                message = _("New Attendance request created")
                instance = form.save(commit=False)
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


class UpdateAttendanceRequestFormView(HorillaFormView):
    """
    form view for update attendance request
    """

    form_class = AttendanceRequestForm
    model = Attendance

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendanceRequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Attendance Request")
        return context

    def form_valid(self, form: AttendanceRequestForm) -> HttpResponse:
        if form.is_valid():
            attendance = Attendance.objects.get(id=self.form.instance.pk)
            instance = form.save()
            instance.employee_id = attendance.employee_id
            instance.id = attendance.id
            if attendance.request_type != "create_request":
                attendance.requested_data = json.dumps(instance.serialize())
                attendance.request_description = instance.request_description
                # set the user level validation here
                attendance.is_validate_request = True
                attendance.save()
            else:
                instance.is_validate_request_approved = False
                instance.is_validate_request = True
                instance.save()
            messages.success(self.request, _("Attendance update request created."))
            employee = attendance.employee_id
            if attendance.employee_id.employee_work_info.reporting_manager_id:
                reporting_manager = (
                    attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                )
                user_last_name = get_employee_last_name(attendance)
                notify.send(
                    self.request.user,
                    recipient=reporting_manager,
                    verb=f"{employee.employee_first_name} {user_last_name}'s\
                          attendance update request for {attendance.attendance_date} is created",
                    verb_ar=f"تم إنشاء طلب تحديث الحضور لـ {employee.employee_first_name} \
                        {user_last_name }في {attendance.attendance_date}",
                    verb_de=f"Die Anfrage zur Aktualisierung der Anwesenheit von \
                        {employee.employee_first_name} {user_last_name} \
                            für den {attendance.attendance_date} wurde erstellt",
                    verb_es=f"Se ha creado la solicitud de actualización de asistencia para {employee.employee_first_name}\
                          {user_last_name} el {attendance.attendance_date}",
                    verb_fr=f"La demande de mise à jour de présence de {employee.employee_first_name}\
                          {user_last_name} pour le {attendance.attendance_date} a été créée",
                    redirect=reverse("request-attendance-view")
                    + f"?id={attendance.id}",
                    icon="checkmark-circle-outline",
                )
            detail_view = self.request.GET.get("detail_view")
            all_attendance = self.request.GET.get("all_attendance")
            if detail_view == "true":
                return HttpResponse(
                    f"""<script>
                                            var reqModal = $('#requestedattendanceTr{form.instance.pk}');
                                            reqModal[0].click();
                                            $('#genericModalEdit').removeClass('oh-modal--show');
                                            $('.reload-record').click();
                                            $('#reloadMessagesButton').click();
                                        </script>
                                    """
                )
            elif all_attendance == "true":
                return HttpResponse(
                    f"""<script>
                                            var attendaceModal = $('#allattendanceTr{form.instance.pk}');
                                            attendaceModal[0].click();
                                            $('#genericModalEdit').removeClass('oh-modal--show');
                                            $('.reload-record').click();
                                            $('#reloadMessagesButton').click();
                                        </script>
                                    """
                )

            return self.HttpResponse()
        return super().form_valid(form)
