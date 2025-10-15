"""
this page is handling the cbv methods of asset history page
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from asset.filters import AssetHistoryFilter
from asset.models import AssetAssignment
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetassignment"), name="dispatch")
class AssetHistoryView(TemplateView):
    """
    for page view
    """

    template_name = "cbv/asset_history/asset_history_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetassignment"), name="dispatch")
class AssetHistorylistView(HorillaListView):
    """
    list view
    """

    filter_class = AssetHistoryFilter
    model = AssetAssignment

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("asset-history-list")

    columns = [
        (_("Asset"), "asset_id__asset_name", "get_avatar"),
        (_("Employee"), "assigned_to_employee_id"),
        (_("Assigned Date"), "assigned_date"),
        (_("Returned Date"), "return_date"),
        (_("Return Status"), "return_status"),
    ]

    sortby_mapping = [
        ("Asset", "asset_id__asset_name", "get_avatar"),
        ("Employee", "assigned_to_employee_id__get_full_name"),
        ("Assigned Date", "assigned_date"),
        ("Returned Date", "return_date"),
    ]

    row_attrs = """
        hx-get='{asset_detail_view}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetassignment"), name="dispatch")
class AssetHistoryNavView(HorillaNavView):
    """
    navbar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("asset-history-list")

    nav_title = _("Asset History")
    filter_body_template = "cbv/asset_history/asset_history_filter.html"
    filter_form_context_name = "form"
    filter_instance = AssetHistoryFilter()
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("asset_id__asset_name", _("Asset")),
        ("assigned_to_employee_id", _("Employee")),
        ("assigned_date", _("Assigned Date")),
        ("return_date", _("Returned Date")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetassignment"), name="dispatch")
class AssetHistoryDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    model = AssetAssignment
    title = _("Asset Details")
    header = {
        "title": "asset_id",
        "subtitle": "asset_id__asset_category_id",
        "avatar": "assigned_to_employee_id__get_avatar",
    }
    body = [
        (_("Allocated User"), "assigned_to_employee_id"),
        (_("Returned Status"), "return_status"),
        (_("Allocated Date"), "assigned_date"),
        (_("Returned Date"), "return_date"),
        (_("Return Description"), "return_condition"),
        (_("Assign Condition Images"), "assign_condition_img", True),
        (_("Return Condition Images"), "return_condition_img", True),
    ]
    cols = {
        "return_condition": 12,
    }
