"""
URL configuration for asset-related views.
"""

from django import views
from django.urls import path

from asset.cbv import (
    asset,
    asset_batch_no,
    asset_category,
    asset_history,
    asset_tab,
    dashboard,
    request_and_allocation,
)
from asset.forms import AssetCategoryForm, AssetForm
from asset.models import Asset, AssetCategory
from base.views import object_duplicate

from . import views

urlpatterns = [
    path(
        "asset-history/", asset_history.AssetHistoryView.as_view(), name="asset-history"
    ),
    path(
        "asset-history-list/",
        asset_history.AssetHistorylistView.as_view(),
        name="asset-history-list",
    ),
    path(
        "asset-history-nav/",
        asset_history.AssetHistoryNavView.as_view(),
        name="asset-history-nav",
    ),
    path(
        "asset-history-detail-view/<int:pk>/",
        asset_history.AssetHistoryDetailView.as_view(),
        name="asset-history-detail-view",
    ),
    # path(
    #     "asset-creation/<int:asset_category_id>/",
    #     views.asset_creation,
    #     name="asset-creation",
    # ),
    path(
        "asset-creation/<int:asset_category_id>/",
        asset_category.AssetFormView.as_view(),
        name="asset-creation",
    ),
    path("asset-list/<int:cat_id>", asset.AssetListView.as_view(), name="asset-list"),
    # path("asset-update/<int:asset_id>/", views.asset_update, name="asset-update"),
    path(
        "asset-update/<int:pk>/",
        asset_category.AssetFormView.as_view(),
        name="asset-update",
    ),
    # path(
    #     "duplicate-asset/<int:obj_id>/",
    #     object_duplicate,
    #     name="duplicate-asset",
    #     kwargs={
    #         "model": Asset,
    #         "form": AssetForm,
    #         "form_name": "asset_creation_form",
    #         "template": "asset/asset_creation.html",
    #     },
    # ),
    path(
        "duplicate-asset/<int:obj_id>/",
        asset_category.AssetDuplicateFormView.as_view(),
        name="duplicate-asset",
    ),
    path("asset-delete/<int:asset_id>/", views.asset_delete, name="asset-delete"),
    # path(
    #     "asset-information/<int:asset_id>/",
    #     views.asset_information,
    #     name="asset-information",
    # ),
    path(
        "asset-information/<int:pk>/",
        asset.AssetInformationView.as_view(),
        name="asset-information",
    ),
    path("asset-category-view/", views.asset_category_view, name="asset-category-view"),
    path(
        "asset-category-view-search-filter",
        views.asset_category_view_search_filter,
        name="asset-category-view-search-filter",
    ),
    # path(
    #     "asset-category-duplicate/<int:obj_id>/",
    #     object_duplicate,
    #     name="asset-category-duplicate",
    #     kwargs={
    #         "model": AssetCategory,
    #         "form": AssetCategoryForm,
    #         "form_name": "asset_category_form",
    #         "template": "category/asset_category_creation.html",
    #     },
    # ),
    path(
        "asset-category-duplicate/<int:obj_id>/",
        asset_category.AssetCategoryDuplicateFormView.as_view(),
        name="asset-category-duplicate",
        kwargs={
            "model": AssetCategory,
            "form": AssetCategoryForm,
            "form_name": "form",
            "template": "category/asset_category_form.html",
        },
    ),
    path(
        "asset-category-nav/",
        asset_category.AssetCategoryNav.as_view(),
        name="asset-category-nav",
    ),
    # path(
    #     "asset-category-creation",
    #     views.asset_category_creation,
    #     name="asset-category-creation",
    # ),
    path(
        "asset-category-creation",
        asset_category.AssetCategoryFormView.as_view(),
        name="asset-category-creation",
    ),
    # path(
    #     "asset-category-update/<int:cat_id>",
    #     views.asset_category_update,
    #     name="asset-category-update",
    # ),
    path(
        "asset-category-update/<int:pk>",
        asset_category.AssetCategoryFormView.as_view(),
        name="asset-category-update",
    ),
    path(
        "asset-category-delete/<int:cat_id>",
        views.delete_asset_category,
        name="asset-category-delete",
    ),
    # path(
    #     "asset-request-creation",
    #     views.asset_request_creation,
    #     name="asset-request-creation",
    # ),
    path(
        "asset-request-creation",
        request_and_allocation.AssetRequestCreateForm.as_view(),
        name="asset-request-creation",
    ),
    # path(
    #     "asset-request-allocation-view/",
    #     views.asset_request_allocation_view,
    #     name="asset-request-allocation-view",
    # ),
    path(
        "asset-request-individual-view/<int:asset_request_id>",
        views.asset_request_individual_view,
        name="asset-request-individual-view",
    ),
    path(
        "own-asset-individual-view/<int:asset_id>",
        views.own_asset_individual_view,
        name="own-asset-individual-view",
    ),
    path(
        "asset-allocation-individual-view/<int:asset_allocation_id>",
        views.asset_allocation_individual_view,
        name="asset-allocation-individual-view",
    ),
    path(
        "asset-request-allocation-view-search-filter",
        views.asset_request_alloaction_view_search_filter,
        name="asset-request-allocation-view-search-filter",
    ),
    path(
        "asset-request-approve/<int:req_id>/",
        views.asset_request_approve,
        name="asset-request-approve",
    ),
    path(
        "asset-request-reject/<int:req_id>/",
        views.asset_request_reject,
        name="asset-request-reject",
    ),
    # path(
    #     "asset-allocate-creation",
    #     views.asset_allocate_creation,
    #     name="asset-allocate-creation",
    # ),
    path(
        "asset-allocate-creation",
        request_and_allocation.AssetAllocationFormView.as_view(),
        name="asset-allocate-creation",
    ),
    path(
        "asset-allocate-return/<int:asset_id>/",
        views.asset_allocate_return,
        name="asset-allocate-return",
    ),
    path(
        "asset-allocate-return-request/<int:asset_id>/",
        views.asset_allocate_return_request,
        name="asset-allocate-return-request",
    ),
    path("asset-excel", views.asset_excel, name="asset-excel"),
    path("asset-import", views.asset_import, name="asset-import"),
    path("asset-export-excel", views.asset_export_excel, name="asset-export-excel"),
    # path(
    #     "asset-batch-number-creation",
    #     views.asset_batch_number_creation,
    #     name="asset-batch-number-creation",
    # ),
    # path("asset-batch-view", views.asset_batch_view, name="asset-batch-view"),
    path(
        "asset-batch-number-creation",
        asset_batch_no.AssetBatchCreateFormView.as_view(),
        name="asset-batch-number-creation",
    ),
    path(
        "asset-batch-view",
        asset_batch_no.AssetBatchNoView.as_view(),
        name="asset-batch-view",
    ),
    path(
        "asset-batch-list",
        asset_batch_no.AssetBatchNoListView.as_view(),
        name="asset-batch-list",
    ),
    path(
        "asset-batch-nav",
        asset_batch_no.AssetBatchNoNav.as_view(),
        name="asset-batch-nav",
    ),
    path(
        "asset-batch-detail-view/<int:pk>/",
        asset_batch_no.AssetBatchDetailView.as_view(),
        name="asset-batch-detail-view",
    ),
    path(
        "asset-batch-number-search",
        views.asset_batch_number_search,
        name="asset-batch-number-search",
    ),
    # path(
    #     "asset-batch-update/<int:batch_id>",
    #     views.asset_batch_update,
    #     name="asset-batch-update",
    # ),
    path(
        "asset-batch-update/<int:pk>",
        asset_batch_no.AssetBatchCreateFormView.as_view(),
        name="asset-batch-update",
    ),
    path(
        "asset-batch-number-delete/<int:batch_id>",
        views.asset_batch_number_delete,
        name="asset-batch-number-delete",
    ),
    path("asset-count-update", views.asset_count_update, name="asset-count-update"),
    path("add-asset-report/", views.add_asset_report, name="add-asset-report"),
    # path(
    #     "add-asset-report/<int:asset_id>",
    #     views.add_asset_report,
    #     name="add-asset-report",
    # ),
    path(
        "add-asset-report/<int:asset_id>/",
        asset_category.AssetReportFormView.as_view(),
        name="add-asset-report",
    ),
    path("dashboard/", views.asset_dashboard, name="asset-dashboard"),
    path(
        "asset-dashboard-requests/",
        views.asset_dashboard_requests,
        name="asset-dashboard-requests",
    ),
    path(
        "asset-dashboard-allocates/",
        views.asset_dashboard_allocates,
        name="asset-dashboard-allocates",
    ),
    path(
        "asset-available-chart/",
        views.asset_available_chart,
        name="asset-available-chart",
    ),
    path(
        "asset-category-chart/", views.asset_category_chart, name="asset-category-chart"
    ),
    # path(
    #     "asset-history",
    #     views.asset_history,
    #     name="asset-history",
    # ),
    path(
        "asset-history-single-view/<int:asset_id>",
        views.asset_history_single_view,
        name="asset-history-single-view",
    ),
    path(
        "asset-history-search",
        views.asset_history_search,
        name="asset-history-search",
    ),
    path(
        "asset-request-allocation-view/",
        request_and_allocation.RequestAndAllocationView.as_view(),
        name="asset-request-allocation-view",
    ),
    path(
        "list-asset-request-allocation",
        request_and_allocation.AllocationList.as_view(),
        name="list-asset-request-allocation",
    ),
    path(
        "list-asset",
        request_and_allocation.AssetList.as_view(),
        name="list-asset",
    ),
    path(
        "tab-asset-request-allocation",
        request_and_allocation.RequestAndAllocationTab.as_view(),
        name="tab-asset-request-allocation",
    ),
    path(
        "list-asset-request",
        request_and_allocation.AssetRequestList.as_view(),
        name="list-asset-request",
    ),
    path(
        "list-asset-allocation",
        request_and_allocation.AssetAllocationList.as_view(),
        name="list-asset-allocation",
    ),
    path(
        "nav-asset-request-allocation",
        request_and_allocation.RequestAndAllocationNav.as_view(),
        name="nav-asset-request-allocation",
    ),
    path(
        "asset-detail-view/<int:pk>/",
        request_and_allocation.AssetDetailView.as_view(),
        name="asset-detail-view",
    ),
    path(
        "asset-request-detail-view/<int:pk>/",
        request_and_allocation.AssetRequestDetailView.as_view(),
        name="asset-request-detail-view",
    ),
    path(
        "asset-request-tab-list-view/<int:pk>/",
        asset_tab.AssetRequestTab.as_view(),
        name="asset-request-tab-list-view",
    ),
    path(
        "assets-tab-list-view/<int:pk>/",
        asset_tab.AssetTabListView.as_view(),
        name="assets-tab-list-view",
    ),
    path(
        "assets-tab-list-view/<int:pk>/",
        asset_tab.AssetTabListView.as_view(),
        name="assets-tab-list-view",
    ),
    path(
        "asset-allocation-detail-view/<int:pk>/",
        request_and_allocation.AssetAllocationDetailView.as_view(),
        name="asset-allocation-detail-view",
    ),
    path(
        "asset-request-approve-form/<int:req_id>/",
        request_and_allocation.AssetApproveFormView.as_view(),
        name="asset-request-approve-form",
    ),
    path("asset-tab/<int:pk>", views.asset_tab, name="asset-tab"),
    path(
        "profile-asset-tab/<int:emp_id>",
        views.profile_asset_tab,
        name="profile-asset-tab",
    ),
    path(
        "asset-request-tab/<int:emp_id>",
        views.asset_request_tab,
        name="asset-request-tab",
    ),
    # path(
    #     "dashboard-asset-request-approve",
    #     views.dashboard_asset_request_approve,
    #     name="dashboard-asset-request-approve",
    # ),
    path(
        "dashboard-asset-request-approve",
        dashboard.AssetRequestToApprove.as_view(),
        name="dashboard-asset-request-approve",
    ),
    path(
        "dashboard-allocated-asset",
        dashboard.AllocatedAssetsList.as_view(),
        name="dashboard-allocated-asset",
    ),
]
