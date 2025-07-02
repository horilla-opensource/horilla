"""
This page handles the cbv methods for resignation tab
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator

from employee.cbv.employee_profile import EmployeeProfileView
from horilla_views.cbv_methods import check_feature_enabled, login_required
from offboarding.cbv.resignation import ResignationLetterDetailView, ResignationListView
from offboarding.models import OffboardingGeneralSetting


# @method_decorator(check_feature_enabled("resignation_request", OffboardingGeneralSetting), name="dispatch")
class ResignationTabView(ResignationListView):
    """
    List view of resignation Tab in profile
    """

    records_per_page = 1

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.action_method = None
        self.view_id = "resignation-container"
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("individual-resignation-tab-list", kwargs={"pk": pk})

    template_name = "cbv/resignation/resignation_tab.html"

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(ResignationListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["employee"] = pk
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset

    row_attrs = """
                hx-get='{get_detail_tab_url}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


class ResignationTabDetailView(ResignationLetterDetailView):
    """
    Detail view of resignation tab in profile
    """

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(ResignationLetterDetailView, self).dispatch(*args, **kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.action_method = None


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Resignation",
            "view": ResignationTabView.as_view(),
            "accessibility": "offboarding.cbv.accessibility.resignation_accessibility",
        },
    ]
)
