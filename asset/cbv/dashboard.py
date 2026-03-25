from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

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
        (
            _("Request User"),
            "requested_employee_id",
            "requested_employee_id__get_avatar",
        ),
        (_("Asset Category"), "asset_category_id"),
        (_("Requested Date"), "asset_request_date"),
    ]

    bulk_select_option = False
    show_toggle_form = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-asset-request-approve")
        self.option_method = None

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
        (
            _("Allocated User"),
            "assigned_to_employee_id",
            "assigned_to_employee_id__get_avatar",
        ),
        (_("Asset"), "asset_id"),
        (_("Assigned Date"), "assigned_date"),
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
