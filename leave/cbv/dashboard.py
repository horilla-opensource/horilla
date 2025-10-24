from datetime import date
from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.methods import filtersubordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView
from leave.cbv.leave_allocation_request import LeaveAllocationRequests
from leave.cbv.leave_requests import LeaveRequestsListView
from leave.cbv.my_leave_request import MyLeaveRequestListView
from leave.filters import UserLeaveRequestFilter
from leave.models import LeaveRequest


@method_decorator(login_required, name="dispatch")
class LeaveAllocationRequestToApprove(LeaveAllocationRequests):
    """
    List view of the page leave allocation to approve in dashboard
    """

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Leave Type"), "leave_type_id"),
        (_("Requested Days"), "requested_days"),
    ]

    bulk_select_option = False
    row_status_indications = None
    option_method = None
    show_toggle_form = False
    records_per_page = 5

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-allocation-approve")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(status="requested", employee_id__is_active=True)
        return queryset


@method_decorator(login_required, name="dispatch")
class LeaveRequestsToApprove(LeaveRequestsListView):
    """
    List view of the page leave requests to approve in dashboard
    """

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Period"), "get_period"),
    ]

    header_attrs = {
        "action": 'style ="width:100px !important"',
        "employee_id": 'style ="width:100px !important"',
        "get_period": 'style ="width:100px !important"',
    }

    bulk_select_option = False
    row_status_indications = None
    option_method = None
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("leave-request-and-approve")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            status="requested",
            employee_id__is_active=True,
            start_date__gte=date.today(),
        )
        queryset = filtersubordinates(
            self.request, queryset, "leave.change_leaverequest"
        )
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("leave.view_leaverequest"), name="dispatch")
class DashboardOnLeave(HorillaListView):
    """
    list view for on leave in dashboard
    """

    columns = [
        ("Employee", "employee_id", "employee_id__get_avatar"),
    ]

    model = LeaveRequest
    filter_class = UserLeaveRequestFilter
    show_toggle_form = False
    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-on-leave")
        if self.request.user.has_perm("leave.view_leaverequest"):
            self.row_attrs = """
                hx-get='{leave_requests_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        today = date.today()
        queryset = super().get_queryset()
        queryset = queryset.filter(
            employee_id__is_active=True,
            status="approved",
            start_date__lte=today,
            end_date__gte=today,
        )
        return queryset


@method_decorator(login_required, name="dispatch")
class DashboardTotalLeaveRequest(MyLeaveRequestListView):
    """
    list view for total leave request in dashboard
    """

    columns = [
        ("Employee", "employee_id", "employee_id__get_avatar"),
        ("Leave Type", "leave_type_id"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Requested Days", "requested_days"),
        ("Status", "status"),
    ]

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name", "employee_id__get_avatar"),
        ("Leave Type", "leave_type_id__name", "leave_type_id__get_avatar"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Requested Days", "requested_days"),
        ("Status", "status"),
    ]

    header_attrs = {
        "start_date": 'style ="width:100px !important"',
        "employee_id": 'style ="width:100px !important"',
        "leave_type_id": 'style ="width:100px !important"',
        "end_date": 'style ="width:100px !important"',
        "status": 'style ="width:100px !important"',
        "requested_days": 'style ="width:100px !important"',
    }

    option_method = None
    action_method = None
    bulk_select_option = False
    row_status_class = None
    row_status_indications = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-total-leave-request")

    def get_queryset(self):
        """
        to filter data
        """
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(employee_id=employee, status="approved")
        return queryset
