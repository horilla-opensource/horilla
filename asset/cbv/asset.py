from typing import Any

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from asset.filters import AssetFilter
from asset.models import Asset
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaListView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetlot"), name="dispatch")
class AssetListView(HorillaListView):
    """
    list view for batch number
    """

    model = Asset
    filter_class = AssetFilter
    columns = ["asset_name", "asset_status", "asset_tracking_id", "asset_lot_number_id"]
    show_filter_tags = False
    bulk_select_option = False
    action_method = "action_column"
    header_attrs = {"asset_name": "style='width:200px !important;'"}

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        return (
            super()
            .get_queryset(queryset, filtered, *args, **kwargs)
            .filter(asset_category_id=self.kwargs["cat_id"])
        )

    row_attrs = """
        hx-get='{asset_detail}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


class AssetInformationView(HorillaDetailedView):
    """
    Detail view of the page
    """

    def get_context_data(self, **kwargs: Any):
        """
        Return context data with the title set to the contract's name.
        """

        context = super().get_context_data(**kwargs)
        asset_name = context["asset"].asset_name
        context["title"] = asset_name
        return context

    model = Asset
    header = False
    action_method = "detail_view_action"
    body = [
        "asset_tracking_id",
        "asset_purchase_date",
        "asset_purchase_cost",
        "asset_status",
        "asset_lot_number_id",
        "asset_category_id",
    ]
