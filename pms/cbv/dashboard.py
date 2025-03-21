"""
This page handles the cbv methods for dashboard views
"""

from typing import Any

from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import filtersubordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView
from pms.cbv.feedback import RequestedFeedbackTab
from pms.filters import EmployeeObjectiveFilter, KeyResultFilter
from pms.models import EmployeeKeyResult, EmployeeObjective


@method_decorator(login_required, name="dispatch")
class DashboardFeedbackView(RequestedFeedbackTab):
    """
    feedback view on dashboard
    """

    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-feedback-answer")
        self.request.dashboard_feedback = "dashboard_feedback"

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        # employee = Employee.objects.filter(employee_user_id=user).first()
        feedback_requested_ids = queryset.filter(
            Q(manager_id=employee, manager_id__is_active=True)
            | Q(colleague_id=employee, colleague_id__is_active=True)
            | Q(subordinate_id=employee, subordinate_id__is_active=True)
        ).distinct()

        queryset = feedback_requested_ids.exclude(feedback_answer__employee_id=employee)
        return queryset

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Title"), "review_cycle"),
    ]

    header_attrs = {
        "employee_id": """
                        style ="width:100px !important"
                        """,
        "review_cycle": """
                        style ="width:100px !important"
                        """,
        "action": """
                        style ="width:100px !important"
                        """,
    }

    row_status_indications = None

    bulk_select_option = False


class KeyResultStatus(HorillaListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "keyContainer"
        self.search_url = reverse("key-result-view")

    model = EmployeeKeyResult
    filter_class = KeyResultFilter
    show_filter_tags = False
    bulk_select_option = False

    header_attrs = {
        "key_result_column": """
                              style="width:200px !important;"
                              """
    }

    columns = [
        (_("Title"), "key_result_column"),
        (_("Start Value"), "start_value"),
        (_("Current Value"), "current_value_col"),
        (_("Target Value"), "target_value_col"),
        (_("Progress Percentage"), "progress_col"),
        (_("Start Date"), "start_date"),
        (_("End date"), "end_date"),
        (_("Status"), "status"),
    ]

    action_method = "actions_col"

    row_attrs = """
                id="empObjTr{get_instance_id}"
                data-kr-id ="{get_instance_id}"
                """

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(HorillaListView, self).dispatch(*args, **kwargs)


class DasboardObjectivesRisk(HorillaListView):
    """
    list view for objectives at risk
    """

    model = EmployeeObjective
    filter_class = EmployeeObjectiveFilter
    bulk_select_option = False
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-risk-objectives")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(status="At Risk")
        return queryset

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
    ]

    row_attrs = """
                hx-get='{employee_objective_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
