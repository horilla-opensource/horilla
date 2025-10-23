"""
Asset category forms
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from asset.cbv.asset_batch_no import DynamicCreateBatchNo
from asset.filters import AssetCategoryFilter, AssetFilter, CustomAssetFilter
from asset.forms import AssetCategoryForm, AssetForm, AssetReportForm
from asset.models import Asset, AssetCategory, AssetDocuments, AssetReport
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaNavView,
)
from horilla_views.views import HorillaDeleteConfirmationView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetcategory"), name="dispatch")
class AssetCategoryFormView(HorillaFormView):
    """
    form view for create asset category
    """

    form_class = AssetCategoryForm
    model = AssetCategory
    new_display_title = _("Asset Category Creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Asset Category Update")

        return context

    def form_valid(self, form: AssetCategoryForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Asset category updated successfully")
            else:
                message = _("Asset category created successfully")
            form.save()
            messages.success(self.request, _(message))
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('.filterButton').click();</script>"
            )
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.add_asset"), name="dispatch")
class AssetFormView(HorillaFormView):
    """
    form view for create asset
    """

    form_class = AssetForm
    model = Asset
    new_display_title = _("Asset Creation")
    dynamic_create_fields = [("asset_lot_number_id", DynamicCreateBatchNo)]
    template_name = "cbv/asset/asset_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_category_id = self.kwargs.get("asset_category_id")
        self.form.fields["asset_category_id"].initial = asset_category_id
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Asset Update")
        else:
            self.form.fields["asset_category_id"].widget = forms.HiddenInput()
        return context

    def form_valid(self, form: AssetForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Asset updated successfully")
            else:
                message = _("Asset created successfully")
            form.save()
            messages.success(self.request, _(message))
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('.filterButton').click();</script>"
            )
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_assetcategory"), name="dispatch")
class AssetCategoryDuplicateFormView(HorillaFormView):
    """
    form view for create duplicate asset category
    """

    form_class = AssetCategoryForm
    model = AssetCategory
    new_display_title = _("Asset Category Duplicate")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        original_object = AssetCategory.objects.get(id=self.kwargs["obj_id"])
        form = self.form_class(instance=original_object)
        for field_name, field in form.fields.items():
            if isinstance(field, forms.CharField):
                if field.initial:
                    initial_value = field.initial
                else:
                    initial_value = f"{form.initial.get(field_name, '')} (copy)"
                form.initial[field_name] = initial_value
                form.fields[field_name].initial = initial_value
        context["form"] = form
        self.form_class.verbose_name = _("Duplicate")
        return context

    def form_valid(self, form: AssetCategoryForm) -> HttpResponse:
        if form.is_valid():
            message = _("Asset category created successfully")
            form.save()
            messages.success(self.request, _(message))
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('.filterButton').click();</script>"
            )
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_asset"), name="dispatch")
class AssetDuplicateFormView(HorillaFormView):
    """
    form view for create duplicate for asset
    """

    form_class = AssetForm
    model = Asset
    new_display_title = _("Asset Duplicate")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        original_object = Asset.objects.get(id=self.kwargs["obj_id"])
        form = self.form_class(instance=original_object)
        form.fields["asset_category_id"].widget = forms.HiddenInput()
        for field_name, field in form.fields.items():
            if isinstance(field, forms.CharField):
                if field.initial:
                    initial_value = field.initial
                else:
                    initial_value = f"{form.initial.get(field_name, '')} (copy)"
                form.initial[field_name] = initial_value
                form.fields[field_name].initial = initial_value
        context["form"] = form
        self.form_class.verbose_name = _("Duplicate")
        return context

    def form_valid(self, form: AssetForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Asset updated successfully")
            else:
                message = _("Asset created successfully")
            form.save()
            messages.success(self.request, _(message))
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('.filterButton').click();</script>"
            )
        return super().form_valid(form)


class AssetReportFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = AssetReportForm
    model = AssetReport
    new_display_title = _("Add Asset Report")

    def get_initial(self) -> dict:
        initial = super().get_initial()
        initial["asset_id"] = self.kwargs.get("asset_id")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = self.kwargs.get("asset_id")
        asset = Asset.objects.filter(id=asset_id)
        self.form.fields["asset_id"].queryset = asset
        return context

    def form_valid(self, form: AssetReportForm) -> HttpResponse:
        if form.is_valid():
            message = _("Asset report added successfully.")
            asset = form.save()
            uploaded_files = form.cleaned_data.get("files")
            if uploaded_files:
                for file in uploaded_files:
                    AssetDocuments.objects.create(asset_report=asset, file=file)
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("asset.view_asset"), name="dispatch")
class AssetCategoryNav(HorillaNavView):
    """
    nav bar for asset category
    """

    nav_title = _("Asset Category")
    filter_body_template = "cbv/asset_category/filter.html"
    filter_instance = AssetFilter()
    filter_form_context_name = "form"
    search_swap_target = "#assetCategoryList"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("asset-category-view-search-filter")
        self.actions = []
        if self.request.user.has_perm("add_assetcategory"):
            self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-get="{reverse('asset-category-creation')}"
                            hx-target="#genericModalBody"
                            """
        if self.request.user.has_perm("add_assetcategory"):
            self.actions.append(
                {
                    "action": _("Import"),
                    "attrs": f"""
                            onclick="getAssetImportTemplate();"
                            data-toggle="oh-modal-toggle"
                            data-target="#objectCreateModal"
                            hx-get="{reverse('asset-import')}"
                            hx-target="#objectCreateModalTarget"
                            style="cursor: pointer;"
                        """,
                },
            )

        if self.request.user.has_perm("view_asset"):
            self.actions.append(
                {
                    "action": _("Export"),
                    "attrs": f"""
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get="{reverse('asset-export-excel')}"
                        hx-target="#objectCreateModalTarget"
                        style="cursor: pointer;"
                    """,
                }
            )


class AssetDeleteConfirmationView(HorillaDeleteConfirmationView):

    def post(self, *args, **kwargs):
        super().post(*args, **kwargs)
        return HorillaFormView.HttpResponse(targets_to_reload=["#applyFilter"])
