"""
This page is handling the cbv methods of asset tab in profile page.
"""

from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from asset.cbv.request_and_allocation import AllocationList, AssetRequestList
from employee.cbv.employee_profile import EmployeeProfileView
from employee.models import Employee
from horilla_views.generic.cbv.views import HorillaTabView


class AssetTabListView(AllocationList):
    """
    Asset tab in individual view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("assets-tab-list-view", kwargs={"pk": pk})
        self.view_id = "asset-div"

    columns = AllocationList.columns + [
        (_("Status"), "status_display"),
        (_("Assigned Date"), "assigned_date_display"),
    ]

    def get_queryset(self):
        """
        Returns a filtered queryset of records assigned to a specific employee
        """

        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(assigned_to_employee_id=pk).exclude(
            return_status__isnull=False
        )
        return queryset


class AssetRequestTab(AssetRequestList):
    """
    Asset request tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("asset-request-tab-list-view", kwargs={"pk": pk})
        self.view_id = "asset-request-div"

    def get_queryset(self):
        """
        Returns a filtered queryset of records for the requested employee.
        """

        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(requested_employee_id=pk)
        return queryset


class AssetTabView(HorillaTabView):
    """
    generic tab view for asset tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "asset-tab"

    def get_context_data(self, **kwargs):
        """
        Adds the employee details and tab information to the context.
        """

        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["emp_id"] = pk
        employee = Employee.objects.get(id=pk)
        context["instance"] = employee
        context["tabs"] = [
            {
                "title": _("Assets"),
                "url": f"{reverse('assets-tab-list-view',kwargs={'pk': pk})}",
            },
            {
                "title": _("Asset Request"),
                "url": f"{reverse('asset-request-tab-list-view',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Create Request",
                        "accessibility": "asset.cbv.accessibility.create_asset_request_accessibility",
                        "attrs": f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-get="{reverse('asset-request-creation')}?pk={pk}"
                                hx-target="#genericModalBody"
                                style="cursor: pointer;"
                                """,
                    }
                ],
            },
        ]
        return context


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Asset",
            "view": AssetTabView.as_view(),
            "accessibility": "asset.cbv.accessibility.asset_accessibility",
        },
    ]
)
