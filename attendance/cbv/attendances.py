"""
this page is handling the cbv methods of  attendances page
"""

import datetime
from datetime import datetime, timedelta
from typing import Any

import django_filters
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import resolve, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.cbv.attendance_activity import AttendanceActivityListView
from attendance.cbv.attendance_tab import AttendanceTabView
from attendance.filters import AttendanceFilters
from attendance.forms import AttendanceExportForm, AttendanceForm, AttendanceUpdateForm
from attendance.models import Attendance, AttendanceValidationCondition, strtime_seconds
from base.decorators import manager_can_enter
from base.filters import PenaltyFilter
from base.methods import choosesubordinates, filtersubordinates, is_reportingmanager
from base.models import PenaltyAccounts
from employee.cbv.employee_profile import EmployeeProfileView
from employee.cbv.employees import EmployeeCard, EmployeeNav, EmployeesList
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla.filters import HorillaFilterSet
from horilla_views.cbv_methods import login_required, render_template
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class AttendancesView(TemplateView):
    """
    for attendances page
    """

    template_name = "cbv/attendances/attendance_view_page.html"


class AttendancesListView(HorillaListView):
    """
    list view
    """

    export_file_name = _("Attendance Report")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendances-list-view")
        if self.request.user.has_perm(
            "attendance.change_attendance"
        ) or is_reportingmanager(self.request):
            self.option_method = "attendance_actions"

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
        (_("Pending Hour"), "hours_pending"),
        (_("Overtime"), "attendance_overtime"),
    ]
    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Date", "attendance_date"),
        ("Day", "attendance_day__day"),
        ("Check-In", "attendance_clock_in"),
        ("In Date", "attendance_clock_in_date"),
        ("Check-Out", "attendance_clock_out"),
        ("Out Date", "attendance_clock_out_date"),
        ("Shift", "shift_id__employee_shift"),
        ("Work Type", "work_type_id__work_type"),
        ("Min Hour", "minimum_hour"),
        ("At Work", "attendance_worked_hour"),
        ("Pending Hour", "hours_pending"),
        ("Overtime", "attendance_overtime"),
    ]
    records_per_page = 10

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        """
        Get queryset
        """
        get_data = self.request.GET.copy()
        # Check if user has set any range filter
        has_min = (
            "attendance_date__gte" in get_data and get_data["attendance_date__gte"]
        )
        has_max = (
            "attendance_date__lte" in get_data and get_data["attendance_date__lte"]
        )

        # If no date range is specified, set default to last 2 days
        if not has_min and not has_max:
            today = datetime.now().date()
            two_days_ago = today - timedelta(days=32)
            get_data["attendance_date__gte"] = two_days_ago.strftime("%Y-%m-%d")
            get_data["attendance_date__lte"] = today.strftime("%Y-%m-%d")

        if get_data.get("attendance_date"):
            get_data["attendance_date__gte"] = get_data["attendance_date"]
            get_data["attendance_date__lte"] = get_data["attendance_date"]

        if not self.queryset:
            self.queryset = super().get_queryset(
                filtered=True, queryset=self.filter_class(get_data).qs
            )
        return self.queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class AttendancesTabView(HorillaTabView):
    """
    tabview of candidate page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "attendances-tab"
        self.tabs = [
            {
                "title": _("Attendance To Validate"),
                "url": f"{reverse('validate-attendance-tab')}",
                "actions": [
                    {
                        "action": "Validate",
                        "attrs": """
                    onclick="
                    bulkValidateTabAttendance();
                    "
                    style="cursor: pointer;"
                """,
                    }
                ],
            },
            {
                "title": _(" OT Attendances"),
                "url": f"{reverse('ot-attendance-tab')}",
                "actions": [
                    {
                        "action": "Approve OT",
                        "attrs": """
                    onclick="
                    otBulkValidateTabAttendance();
                    "
                    style="cursor: pointer;"
                """,
                    }
                ],
            },
            {
                "title": _(" Validated Attendances"),
                "url": f"{reverse('validated-attendance-tab')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class AttendancesNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("attendances-tab-view")
        self.search_in = [
            ("attendance_day", _("Day")),
            ("shift_id", _("Shift")),
            ("work_type_id", _("Work Type")),
            ("employee_id__employee_work_info__department_id", _("Department")),
            (
                "employee_id__employee_work_info__job_position_id",
                _("Job Position"),
            ),
            ("employee_id__employee_work_info__company_id", _("Company")),
        ]
        self.create_attrs = f"""
             hx-get="{reverse_lazy("attendance-create")}"
             hx-target="#genericModalBody"
             data-target="#genericModal"
             data-toggle="oh-modal-toggle"
         """
        actions = [
            {
                "action": _("Import"),
                "attrs": """
                    onclick="
                    importAttendanceNav();
                    "
                    data-toggle = "oh-modal-toggle"
                    data-target = "#attendanceImport
                    "
                    style="cursor: pointer;"
                """,
            },
            {
                "action": _("Export"),
                "attrs": f"""
                    data-toggle = "oh-modal-toggle"
                    data-target = "#genericModal"
                    hx-target="#genericModalBody"
                    hx-get ="{reverse('attendences-navbar-export')}"
                    style="cursor: pointer;"
                """,
            },
        ]
        if self.request.user.has_perm("attendance.add_attendance"):
            actions.append(
                {
                    "action": _("Delete"),
                    "attrs": """
                        onclick="
                        bulkDeleteAttendanceNav();
                        "
                        data-action="delete"
                        style="cursor: pointer; color:red !important"
                    """,
                }
            )
        self.actions = actions

    nav_title = _("Attendances")
    filter_body_template = "cbv/attendances/attendances_filter_page.html"
    filter_instance = AttendanceFilters()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("employee_id", _("Employee")),
        ("attendance_date", _("Attendance Date")),
        ("shift_id", _("Shift")),
        ("Work Type", _("work_type_id")),
        ("minimum_hour", _("Min Hour")),
        ("employee_id__country", "Country"),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        (
            "employee_id__employee_work_info__employee_type_id",
            _("Employement Type"),
        ),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class AttendancesExportNav(TemplateView):
    """
    for bulk export
    """

    template_name = "cbv/attendances/attendances_export_page.html"

    def get_context_data(self, **kwargs: Any):
        """
        get data for export
        """

        attendances = Attendance.objects.all()
        export_form = AttendanceExportForm
        export = AttendanceFilters(queryset=attendances)
        context = super().get_context_data(**kwargs)
        context["export_form"] = export_form
        context["export"] = export
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class ValidateAttendancesList(AttendancesListView):
    """
    validate tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("validate-attendance-tab")

    def get_queryset(self):
        if not self.queryset:
            self.queryset = super().get_queryset()
            self.queryset = self.queryset.filter(
                attendance_validated=False, employee_id__is_active=True
            )
            self.queryset = filtersubordinates(
                self.request, self.queryset, "attendance.view_attendance"
            )
        return self.queryset

    selected_instances_key_id = "validateselectedInstances"
    action_method = "validate_button"
    row_attrs = """
                hx-get='{validate_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    header_attrs = {
        "action": """
                    style="width:150px !important;"
                """
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class OTAttendancesList(AttendancesListView):
    """
    OT tab
    """

    selected_instances_key_id = "overtimeselectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("ot-attendance-tab")
        self.action_method = "ot_approve"

    def get_queryset(self):
        if not self.queryset:
            self.queryset = super().get_queryset()
            minot = strtime_seconds("00:30")
            condition = (
                AttendanceValidationCondition.objects.first()
            )  # and condition.minimum_overtime_to_approve is not None
            if condition is not None:
                minot = strtime_seconds(condition.minimum_overtime_to_approve)
            self.queryset = self.queryset.filter(
                overtime_second__gt=0,
                attendance_validated=True,
            )
            self.queryset = filtersubordinates(
                self.request, self.queryset, "attendance.view_attendance"
            )
        return self.queryset

    row_attrs = """
                hx-get='{ot_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    header_attrs = {
        "action": """
                    style="width:150px !important;"
                """
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class ValidatedAttendancesList(AttendancesListView):
    """
    validated tab
    """

    selected_instances_key_id = "validatedselectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("validated-attendance-tab")

    def get_queryset(self):

        if not self.queryset:
            self.queryset = super().get_queryset()
            self.queryset = self.queryset.filter(
                attendance_validated=True, employee_id__is_active=True
            )
            self.queryset = filtersubordinates(
                self.request, self.queryset, "attendance.view_attendance"
            )
        return self.queryset

    row_attrs = """
                hx-get='{validated_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class GenericAttendancesDetailView(HorillaDetailedView):
    """
    Generic Detail view of page
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
        (_("Activities"), "attendance_detail_activity_col", True),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class ValidateDetailView(GenericAttendancesDetailView):
    """
    detail view for validate tab
    """

    action_method = "validate_detail_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class OtDetailView(GenericAttendancesDetailView):
    """
    detail view for OT tab
    """

    action_method = "ot_detail_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.view_attendance"), name="dispatch")
class ValidatedDetailView(GenericAttendancesDetailView):
    """
    detail view for validate tab
    """

    action_method = "validated_detail_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.add_attendance"), name="dispatch")
class AttendancesFormView(HorillaFormView):
    """
    form view
    """

    form_class = AttendanceForm
    model = Attendance
    new_display_title = _("Add Attendances")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form = choosesubordinates(
            self.request, self.form, "attendance.add_attendance"
        )

        context["form"] = self.form
        context["view_id"] = "attendanceCreate"

        return context

    def form_valid(self, form: AttendanceForm) -> HttpResponse:
        if form.is_valid():
            message = _("Attendance Added")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("attendance.change__attendance"), name="dispatch")
class AttendanceUpdateFormView(HorillaFormView):
    """
    form for update
    """

    model = Attendance
    form_class = AttendanceUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Edit Attendance")

        context["view_id"] = "attendanceUpdate"

        return context

    def form_valid(self, form: AttendanceUpdateForm) -> HttpResponse:
        if form.is_valid():
            message = _("Attandance Updated")
            form.save()
            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class AttendanceDetailActivityList(AttendanceActivityListView):
    """
    List view for activity col in detail view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.action_method = None
        resolved = resolve(self.request.path_info)
        kwargs = {
            "pk": resolved.kwargs.get("pk"),
        }
        self.search_url = reverse("get-attendance-activities", kwargs=kwargs)

    bulk_select_option = None
    row_attrs = ""

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = Attendance.find(self.kwargs.get("pk"))
        queryset = queryset.filter(
            attendance_date=pk.attendance_date, employee_id=pk.employee_id
        )

        return queryset


class PenaltyAccountListView(HorillaListView):
    """
    list view for penalty tab
    """

    filter_class = PenaltyFilter
    model = PenaltyAccounts
    records_per_page = 3
    columns = [
        (_("Leave Type"), "leave_type_id"),
        (_("Minus Days"), "minus_leaves"),
        (_("Deducted From CFD"), "get_deduct_from_carry_forward"),
        (_("Penalty amount"), "penalty_amount"),
        (_("Created Date"), "created_at"),
        (_("Penalty Type"), "penalty_type_col"),
    ]

    actions = [
        {
            "action": _("Delete"),
            "icon": "trash-outline",
            "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100 text-danger"
                        hx-confirm="Are you sure you want to delete this penalty?"
                        hx-post="{get_delete_url}"
                        hx-target="#penaltyTr{get_delete_instance}"
                        hx-swap="delete"

                      """,
        }
    ]

    row_attrs = """
                id = "penaltyTr{get_delete_instance}"
                """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("individual-panlty-list-view", kwargs={"pk": pk})

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset


class ValidateAttendancesIndividualTabView(AttendancesListView):
    """
    list view for validate attendance tab view
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(
            employee_id=pk,
            attendance_validated=False,
            employee_id__is_active=True,
        )
        queryset = (
            filtersubordinates(self.request, queryset, "attendance.view_attendance")
            | queryset
        )
        return queryset

    selected_instances_key_id = "validateselectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "validate-attendance-individual-tab", kwargs={"pk": pk}
        )
        if self.request.user.has_perm(
            "attendance.change_attendance"
        ) or is_reportingmanager(self.request):
            self.action_method = "validate_button"
        self.view_id = "validate-container"

    row_attrs = """
                hx-get='{individual_validate_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


class ValidateAttendancesIndividualDetailView(GenericAttendancesDetailView):
    """
    Validate tab detail view in single view of employee
    """

    action_method = "validate_detail_actions"

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        obj = queryset.get(pk=pk)
        employee_id = obj.employee_id
        if is_reportingmanager(self.request):
            queryset = filtersubordinates(
                self.request, queryset, "attendance.view_attendance"
            ) | queryset.filter(employee_id=self.request.user.employee_get)
        elif self.request.user.has_perm("attendance.view_attendance"):
            queryset = queryset.filter(employee_id=employee_id)
        else:
            queryset = queryset.filter(employee_id=self.request.user.employee_get)
        return queryset

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(GenericAttendancesDetailView, self).dispatch(*args, **kwargs)


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Attendance",
            # "view": views.attendance_tab,
            "view": AttendanceTabView.as_view(),
            "accessibility": "attendance.cbv.accessibility.attendance_accessibility",
        },
        {
            "title": "Penalty Account",
            "view": PenaltyAccountListView.as_view(),
            "accessibility": "attendance.cbv.accessibility.penalty_accessibility",
        },
    ]
)


def get_working_today(queryset, _name, value):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    working_employees = Attendance.objects.filter(
        attendance_date__gte=yesterday,
        attendance_date__lte=today,
        attendance_clock_out_date__isnull=True,
    ).values_list("employee_id", flat=True)

    if value:
        queryset = queryset.filter(id__in=working_employees)
    else:
        queryset = queryset.exclude(id__in=working_employees)
    return queryset


og_init = EmployeeFilter.__init__


def online_init(self, *args, **kwargs):
    og_init(self, *args, **kwargs)
    custom_field = django_filters.BooleanFilter(
        label="Working", method=get_working_today
    )
    self.filters["working_today"] = custom_field
    self.form.fields["working_today"] = custom_field.field
    self.form.fields["working_today"].widget.attrs.update(
        {
            "class": "oh-select oh-select-2 w-100",
        }
    )


status_indications = [
    (
        "offline--dot",
        _("Offline"),
        """
            onclick="
                $('#applyFilter').closest('form').find('[name=working_today]').val('false');
                $('#applyFilter').click();
            "
            """,
    ),
    (
        "online--dot",
        _("Online"),
        """
            onclick="$('#applyFilter').closest('form').find('[name=working_today]').val('true');
                $('#applyFilter').click();
            "
            """,
    ),
]


def offline_online(self):
    """
    This method for get custome coloumn for rating.
    """

    return render_template(
        path="cbv/employees_view/offline_online.html",
        context={"instance": self},
    )


EmployeeFilter.__init__ = online_init
EmployeeNav.filter_instance = EmployeeFilter()
EmployeeCard.card_status_indications = status_indications
EmployeesList.row_status_indications = status_indications
Employee.offline_online = offline_online
