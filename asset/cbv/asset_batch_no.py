"""
this page is handling the cbv methods for asset batch no
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from asset.filters import AssetBatchNoFilter
from asset.forms import AssetBatchForm
from asset.models import AssetLot
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetlot"), name="dispatch")
class AssetBatchNoView(TemplateView):
    """
    for Asset batch no page
    """

    template_name = "cbv/asset_batch_no/asset_batch_no.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetlot"), name="dispatch")
class AssetBatchNoListView(HorillaListView):
    """
    list view for batch number
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("asset-batch-list")
        self.view_id = "AssetBatchList"

    model = AssetLot
    filter_class = AssetBatchNoFilter

    columns = [
        (_("Batch Number"), "lot_number"),
        (_("Description"), "lot_description"),
        (_("Assets"), "assets_column"),
    ]

    header_attrs = {
        "action": """
                   style = "width:180px !important"
                   """
    }

    action_method = "actions"

    row_attrs = """
                hx-get='{asset_batch_detail}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetlot"), name="dispatch")
class AssetBatchNoNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("asset-batch-list")

        if self.request.user.has_perm("asset.view_assetlot"):
            self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('asset-batch-number-creation')}"
                            """

    nav_title = _("Asset Batch Number")
    filter_instance = AssetBatchNoFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.add_assetlot"), name="dispatch")
class AssetBatchCreateFormView(HorillaFormView):
    """
    form view for create batch number
    """

    form_class = AssetBatchForm
    model = AssetLot
    new_display_title = _("Create Batch Number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Batch Number Update")

        return context

    def form_valid(self, form: AssetBatchForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Batch number updated successfully.")
            else:
                message = _("Batch number created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.add_assetlot"), name="dispatch")
class DynamicCreateBatchNo(AssetBatchCreateFormView):
    """
    view for dynamic batch create
    """

    is_dynamic_create_view = True


class AssetBatchDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    def get_context_data(self, **kwargs: Any):
        """
        Return context data with the title set to the contract's name.
        """

        context = super().get_context_data(**kwargs)
        lot_number = context["assetlot"].lot_number
        context["title"] = "Asset Batch:" + lot_number
        return context

    model = AssetLot
    header = False

    cols = {"assets_column": 12, "lot_description": 12, "lot_number": 12}
    body = {
        (_("Assets"), "assets_column"),
        (_("Description"), "lot_description"),
        (_("Batch Number"), "lot_number"),
    }

    actions = [
        {
            "action": _("Edit"),
            "icon": "create-outline",
            "attrs": """
                        class="oh-btn oh-btn--info w-100"
                        hx-get='{get_update_url}?instance_ids={ordered_ids}'
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
        },
        {
            "action": _("Delete"),
            "icon": "trash-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger w-100"
                    hx-confirm="Do you want to delete this batch number?"
                    hx-post="{get_delete_url}?instance_ids={ordered_ids}"
                    hx-target="#AssetBatchList"
                    """,
        },
    ]
