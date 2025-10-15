"""
Request and allocation page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import DeleteView

from asset.filters import AssetAllocationFilter, AssetRequestFilter, CustomAssetFilter
from asset.forms import AssetAllocationForm, AssetRequestForm
from asset.models import Asset, AssetAssignment, AssetRequest, ReturnImages
from base.methods import filtersubordinates
from employee.models import Employee
from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
class RequestAndAllocationView(TemplateView):
    """
    for request and allocation page
    """

    template_name = "cbv/request_and_allocation/request_and_allocation.html"


@method_decorator(login_required, name="dispatch")
class AllocationList(HorillaListView):
    """
    For both  asset allocation and asset tab
    """

    # view_id = "view-container"

    bulk_update_fields = ["asset_id__expiry_date"]

    model = AssetAssignment
    filter_class = AssetAllocationFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-asset")

    columns = [
        (_("Asset"), "asset_id", "get_avatar"),
        (_("Category"), "asset_id__asset_category_id"),
        (_("Expiry Date"), "asset_id__expiry_date"),
    ]

    header_attrs = {
        "action": """ style = "width:180px !important" """,
        "asset_id__asset_name": """ style = "width:250px !important" """,
        "asset_id__asset_category_id": """ style = "width:250px !important" """,
        "asset_id__expiry_date": """ style = "width:250px !important" """,
    }

    sortby_mapping = [
        ("Category", "asset_id__asset_category_id__asset_category_name"),
        ("Expiry Date", "asset_id__expiry_date"),
    ]

    action_method = "asset_action"

    row_attrs = """
        hx-get='{detail_view_asset}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


@method_decorator(login_required, name="dispatch")
class AssetList(AllocationList):
    """
    Asset tab
    """

    # view_id = "assetlist"
    def get_queryset(self):
        """
        Returns a queryset of AssetRequest objects filtered by
        the current user's employee ID.
        """
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(assigned_to_employee_id=employee).exclude(
            return_status__isnull=False
        )
        return queryset

    selected_instances_key_id = "assetlistInstances"


@method_decorator(login_required, name="dispatch")
class AssetAllocationList(AllocationList):
    """
    Asset allocation tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-asset-allocation")

        if any(
            self.request.user.has_perm(p)
            for p in [
                "asset.delete_assetassignment",
                "asset.change_assetassignment",
                "asset.add_assetassignment",
            ]
        ):
            self.action_method = "allocation_action"
            self.option_method = "allocation_option"

    columns = [
        (
            _("Allocated User"),
            "assigned_to_employee_id",
            "assigned_to_employee_id__get_avatar",
        ),
        (_("Asset"), "asset_id"),
        (_("Assigned Date"), "assigned_date"),
        (_("Return Date"), "return_status_col"),
    ]

    sortby_mapping = [
        ("Allocated User", "assigned_to_employee_id__get_full_name"),
        ("Asset", "asset_id__asset_name"),
        ("Assigned Date", "assigned_date"),
        ("Return Date", "return_status_col"),
    ]

    row_attrs = """
        hx-get='{detail_view_asset_allocation}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


@method_decorator(login_required, name="dispatch")
class AssetRequestList(HorillaListView):
    """
    Asset Request Tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.search_url = reverse("list-asset-request")
        # self.view_id = "view-container"
        if self.request.user.has_perm("asset.add_assetassignment"):
            self.action_method = "action_col"

        self.option_method = "option_col"

    model = AssetRequest
    filter_class = AssetRequestFilter

    def get_queryset(self):
        """
        Returns a filtered queryset of AssetRequest objects
        based on user permissions and employee ID.
        """

        queryset = super().get_queryset()
        queryset = filtersubordinates(
            request=self.request,
            perm="asset.view_assetrequest",
            queryset=queryset,
            field="requested_employee_id",
        ) | queryset.filter(requested_employee_id=self.request.user.employee_get)
        return queryset

    columns = [
        (
            _("Request User"),
            "requested_employee_id",
            "requested_employee_id__get_avatar",
        ),
        (_("Asset Category"), "asset_category_id"),
        (_("Requested Date"), "asset_request_date"),
        (_("Status"), "status_col"),
    ]

    header_attrs = {"action": """ style = "width:180px !important" """}

    sortby_mapping = [
        ("Request User", "requested_employee_id__get_full_name"),
        ("Asset Category", "asset_category_id__asset_category_name"),
        ("Requested Date", "asset_request_date"),
        ("Status", "status_col"),
    ]

    row_attrs = """
        hx-get='{detail_view_asset_request}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="asset.delete_assetassignment"), name="dispatch"
)
class AssetAllocationDelete(DeleteView):
    """
    This the Asset Allocation Delete View
    """

    model = AssetAssignment

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, _("Allocation deleted successfully"))

        return HorillaFormView.HttpResponse()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="asset.delete_assetrequest"), name="dispatch"
)
class AssetRequestDelete(DeleteView):
    """
    This the Asset Request Delete View
    """

    model = AssetRequest

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, _("Asset request deleted successfully"))

        return HorillaFormView.HttpResponse()


@method_decorator(login_required, name="dispatch")
class RequestAndAllocationTab(HorillaTabView):
    """
    Tab View
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Asset"),
                "url": f"{reverse('list-asset')}",
            },
            {
                "title": _("Asset Request"),
                "url": f"{reverse('list-asset-request')}",
                "actions": [
                    {
                        "action": "Create Request",
                        "attrs": f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-get="{reverse('asset-request-creation')}"
                            hx-target="#genericModalBody"
                            style="cursor: pointer;"
                        """,
                    }
                ],
            },
        ]
        if self.request.user.has_perm("asset.view_assetassignment"):
            self.tabs.append(
                {
                    "title": _("Asset Allocation"),
                    "url": f"{reverse('list-asset-allocation')}",
                    "actions": [
                        {
                            "action": "Create Allocation",
                            "attrs": f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-get="{reverse('asset-allocate-creation')}"
                                hx-target="#genericModalBody"
                                style="cursor: pointer;"
                            """,
                        }
                    ],
                },
            )


@method_decorator(login_required, name="dispatch")
class RequestAndAllocationNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("tab-asset-request-allocation")

    nav_title = _("Asset")
    filter_instance = AssetAllocationFilter()
    filter_form_context_name = "asset_allocation_filter_form"
    filter_body_template = "cbv/request_and_allocation/filter.html"
    search_swap_target = "#listContainer"

    def get_context_data(self, **kwargs):
        """
        context data
        """
        context = super().get_context_data(**kwargs)
        assets_filter_form = CustomAssetFilter()
        asset_request_filter_form = AssetRequestFilter()
        context["assets_filter_form"] = assets_filter_form.form
        context["asset_request_filter_form"] = asset_request_filter_form.form
        return context

    group_by_fields = [
        ("requested_employee_id", _("Asset Request / Employee")),
        ("asset_category_id", _("Asset Request / Asset Category")),
        ("asset_request_date", _("Asset Request / Request Date")),
        ("asset_request_status", _("Asset Request / Status")),
        ("assigned_to_employee_id", _("Asset Allocation / Employee")),
        ("assigned_date", _("Asset Allocation / Assigned Date")),
        ("return_date", _("Asset Allocation / Return Date")),
    ]


@method_decorator(login_required, name="dispatch")
class AssetDetailView(HorillaDetailedView):
    """
    detail view of asset tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Tracking Id"), "asset_id__asset_tracking_id"),
            (_("Batch No"), "asset_id__asset_lot_number_id"),
            (_("Assigned Date"), "assigned_date"),
            (_("Status"), "asset_detail_status"),
            (_("Assigned by"), "assigned_by_employee_id"),
            (_("Description"), "asset_id__asset_description"),
            # ("Category","asset_id__asset_category_id")
        ]
        self.cols = {
            "asset_id__asset_description": 12,
        }

    action_method = "asset_detail_action"

    model = AssetAssignment
    title = _("Asset Information")
    header = {
        "title": "asset_id__asset_name",
        "subtitle": "asset_id__asset_category_id",
        "avatar": "get_avatar",
    }


@method_decorator(login_required, name="dispatch")
class AssetRequestDetailView(HorillaDetailedView):
    """
    detail view of asset request tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Asset Category"), "asset_category_id"),
            (_("Requested Date"), "asset_request_date"),
            (_("Status"), "status_col"),
            (_("Request Description"), "description"),
        ]

        self.cols = {
            "description": 12,
        }

    model = AssetRequest
    title = _("Details")
    header = {
        "title": "requested_employee_id",
        "subtitle": "asset_request_detail_subtitle",
        "avatar": "requested_employee_id__get_avatar",
    }
    action_method = "detail_action_col"


@method_decorator(login_required, name="dispatch")
class AssetAllocationDetailView(HorillaDetailedView):
    """
    detail view of asset allocation tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Returned Status"), "return_status"),
            (_("Allocated User"), "assigned_by_employee_id"),
            (_("Allocated Date"), "assigned_date"),
            (_("Return Date"), "return_date"),
            (_("Asset"), "asset_id"),
            (_("Status"), "detail_status"),
            (_("Return Description"), "return_condition"),
        ]

        self.cols = {
            "return_condition": 12,
        }

    model = AssetAssignment
    title = _("Details")
    header = {
        "title": "assigned_to_employee_id",
        "subtitle": "asset_allocation_detail_subtitle",
        "avatar": "assigned_to_employee_id__get_avatar",
    }
    action_method = "asset_allocation_detail_action"


@method_decorator(login_required, name="dispatch")
class AssetRequestCreateForm(HorillaFormView):
    """
    Create Asset request
    """

    model = AssetRequest
    form_class = AssetRequestForm
    template_name = "cbv/request_and_allocation/forms/req_form.html"
    new_display_title = _("Asset Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get("pk"):
            pk = self.request.GET.get("pk")
            self.form.fields["requested_employee_id"].queryset = (
                Employee.objects.filter(id=pk)
            )
            self.form.fields["requested_employee_id"].initial = pk

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Asset Request")
        return context

    def form_valid(self, form: AssetRequestForm) -> HttpResponse:
        """
        Handles validation and saving of an AssetRequestForm.
        """
        if form.is_valid():
            message = _("Asset Request Created Successfully")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="asset.add_asset"), name="dispatch")
class AssetAllocationFormView(HorillaFormView):
    """
    Create Asset Allocation
    """

    model = AssetAssignment
    form_class = AssetAllocationForm
    template_name = "cbv/request_and_allocation/forms/allo_form.html"
    new_display_title = _("Asset Allocation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Asset Allocation")
        return context

    def form_valid(self, form: AssetAllocationForm) -> HttpResponse:
        """
        form valid function
        """
        if form.is_valid():
            asset = form.instance.asset_id
            asset.asset_status = "In use"
            asset.save()
            message = _("Asset allocated Successfully")
            form.save()
            request = getattr(_thread_locals, "request", None)
            files = request.FILES.getlist("assign_images")
            attachments = []
            if request.FILES:
                for file in files:
                    attachment = ReturnImages()
                    attachment.image = file
                    attachment.save()
                    attachments.append(attachment)
                form.instance.assign_images.add(*attachments)
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


class AssetApproveFormView(HorillaFormView):
    """
    Create Asset Allocation
    """

    model = AssetAssignment
    form_class = AssetAllocationForm
    template_name = "cbv/request_and_allocation/forms/asset_approve_form.html"
    new_display_title = _("Asset Allocation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req_id = self.kwargs.get("req_id")
        asset_request = AssetRequest.objects.filter(id=req_id).first()
        asset_category = asset_request.asset_category_id
        assets = asset_category.asset_set.filter(asset_status="Available")
        self.form.fields["asset_id"].queryset = assets
        self.form.fields["assigned_to_employee_id"].initial = (
            asset_request.requested_employee_id
        )
        self.form.fields["assigned_by_employee_id"].initial = (
            self.request.user.employee_get
        )
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: AssetAllocationForm) -> HttpResponse:
        """
        form valid function
        """
        req_id = self.kwargs.get("req_id")
        asset_request = AssetRequest.objects.filter(id=req_id).first()
        if form.is_valid():
            asset = form.instance.asset_id.id
            asset = Asset.objects.filter(id=asset).first()
            asset.asset_status = "In use"
            asset.save()
            # form = form.save(commit=False)
            # form.assigned_by_employee_id = self.request.user.employee_get
            form.save()
            asset_request.asset_request_status = "Approved"
            asset_request.save()
            request = getattr(_thread_locals, "request", None)
            files = request.FILES.getlist("assign_images")
            attachments = []
            if request.FILES:
                for file in files:
                    attachment = ReturnImages()
                    attachment.image = file
                    attachment.save()
                    attachments.append(attachment)
                form.instance.assign_images.add(*attachments)
            messages.success(self.request, _("Asset request approved successfully!."))
            notify.send(
                self.request.user.employee_get,
                recipient=asset_request.requested_employee_id.employee_user_id,
                verb="Your asset request approved!.",
                verb_ar="تم الموافقة على طلب الأصول الخاص بك!",
                verb_de="Ihr Antragsantrag wurde genehmigt!",
                verb_es="¡Su solicitud de activo ha sido aprobada!",
                verb_fr="Votre demande d'actif a été approuvée !",
                redirect=reverse("asset-request-allocation-view")
                + f"?asset_request_date={asset_request.asset_request_date}\
                &asset_request_status={asset_request.asset_request_status}",
                icon="bag-check",
            )
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)
