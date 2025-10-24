"""
This page handles the cbv methods for dashboard views
"""

from datetime import datetime
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.cbv.shift_request import ShiftRequestList
from base.cbv.work_type_request import WorkRequestListView
from base.decorators import manager_can_enter
from base.filters import AnnouncementFilter, AnnouncementViewFilter
from base.methods import filtersubordinates
from base.models import Announcement, AnnouncementView
from employee.filters import EmployeeWorkInformationFilter
from employee.forms import EmployeeWorkInformationUpdateForm
from employee.models import EmployeeWorkInformation
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaListView


@method_decorator(login_required, name="dispatch")
class DashboardWorkTypeRequest(WorkRequestListView):
    """
    Work type request view in dashboard.
    """

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Requested Work Type"), "work_type_id"),
    ]

    row_attrs = """
        hx-get='{detail_view}?instance_ids={ordered_ids}&dashboard=true'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """

    header_attrs = {
        "action": 'style="width:100px !important"',
        "employee_id": 'style="width:100px !important"',
        "work_type_id": 'style="width:100px !important"',
    }

    records_per_page = 5
    option_method = None
    row_status_indications = None
    show_toggle_form = False
    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-work-type-request")
        self.request.dashboard = "dashboard"

    def get_queryset(self):
        """Filter queryset based on permissions and request context."""

        queryset = HorillaListView.get_queryset(self)
        queryset = queryset.filter(
            employee_id__is_active=True,
            approved=False,
            canceled=False,
        )
        queryset = filtersubordinates(
            self.request, queryset, "base.add_worktyperequest"
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class ShiftRequestToApprove(ShiftRequestList):

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Requested Shift"), "shift_id"),
    ]

    row_attrs = """
        hx-get='{shift_details}?instance_ids={ordered_ids}&dashboard=true'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """

    header_attrs = {
        "action": 'style ="width:100px !important"',
        "employee_id": 'style ="width:100px !important"',
        "shift_id": 'style ="width:100px !important"',
    }

    bulk_select_option = False
    show_toggle_form = False
    records_per_page = 5
    option_method = None
    row_status_indications = None
    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-shift-request")

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        queryset = queryset.filter(
            approved=False, canceled=False, employee_id__is_active=True
        )
        queryset = filtersubordinates(self.request, queryset, "base.add_shiftrequest")
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("employee.view_employeeworkinformation"), name="dispatch"
)
class EmployeeWorkInformationList(HorillaListView):
    """
    Employee work information progress list
    """

    columns = [
        (_("Employee"), "employee_id"),
        (_("Progress"), "progress_col"),
    ]

    header_attrs = {"employee_id": 'style ="width:100px !important"'}

    row_attrs = """
        hx-get='{get_edit_url}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """

    model = EmployeeWorkInformation
    filter_class = EmployeeWorkInformationFilter
    bulk_select_option = False
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "pending"
        self.search_url = reverse("emp-workinfo-complete")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = filtersubordinates(
            self.request, queryset, "employee.view_employeeworkinformation"
        )
        queryset = queryset.filter(
            id__in=[obj.id for obj in queryset if obj.calculate_progress() != 100]
        )
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("employee.change_employeeworkinformation"), name="dispatch"
)
class EmployeeWorkInformationFormView(HorillaFormView):
    """
    form view for edit work information
    """

    form_class = EmployeeWorkInformationUpdateForm
    model = EmployeeWorkInformation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Work Information")
        return context

    def form_valid(self, form: EmployeeWorkInformationUpdateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Work Information Updated")
                messages.success(self.request, message)
            form.save()
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('#pendingReload').click();</script>"
            )
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class DashboardAnnouncementView(HorillaListView):
    """
    list view for dashboard announcement
    """

    columns = [
        (_("Title"), "announcement_custom_col"),
    ]

    model = Announcement
    filter_class = AnnouncementFilter
    show_toggle_form = False
    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-announcement-list")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(expire_date__lt=datetime.today().date()).order_by(
            "-created_at"
        )

        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_announcement"), name="dispatch")
class AnnouncementViewedByList(HorillaListView):
    """
    List view for announcement viewed by on detail view
    """

    columns = [
        (_("Viewed By"), "announcement_viewed_by_col"),
    ]

    model = AnnouncementView
    filter_class = AnnouncementViewFilter
    bulk_select_option = False
    show_toggle_form = False

    def get_queryset(self):
        queryset = super().get_queryset()
        anoun = self.kwargs.get("announcement_id")
        queryset = queryset.filter(announcement_id__id=anoun, viewed=True)
        return queryset
