from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator

from asset.cbv.request_and_allocation import AssetAllocationList, AssetRequestList
from base.methods import filtersubordinates
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaListView


@method_decorator(login_required, name="dispatch")
class AssetRequestToApprove(AssetRequestList):
    """
    Asset request to approve in dashboard
    """

    columns = [
        column for column in AssetRequestList.columns if column[1] != "status_col"
    ]

    bulk_select_option = False
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-asset-request-approve")

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        queryset = queryset.filter(
            asset_request_status="Requested", requested_employee_id__is_active=True
        )
        queryset = filtersubordinates(
            self.request,
            queryset,
            "asset.view_assetrequest",
            field="requested_employee_id",
        )
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetcategory"), name="dispatch")
class AllocatedAssetsList(AssetAllocationList):
    """
    List of allocated assets in dashboard
    """

    columns = [
        column
        for column in AssetAllocationList.columns
        if column[1] != "return_status_col"
    ]

    bulk_select_option = False
    show_toggle_form = False
    action_method = None

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            asset_id__asset_status="In use", assigned_to_employee_id__is_active=True
        )
        return queryset
