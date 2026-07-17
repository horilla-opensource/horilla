from django.urls import path, re_path

from ...api_views.asset.views import *

urlpatterns = [
    re_path(
        r"^asset-categories/(?P<pk>\d+)?$",
        AssetCategoryAPIView.as_view(),
        name="api-asset-category-detail",
    ),
    re_path(
        r"^asset-lots/(?P<pk>\d+)?$",
        AssetLotAPIView.as_view(),
        name="api-asset-lot-detail",
    ),
    re_path(r"^assets/(?P<pk>\d+)?$", AssetAPIView.as_view(), name="api-asset-detail"),
    re_path(
        r"^asset-allocations/(?P<pk>\d+)?$",
        AssetAllocationAPIView.as_view(),
        name="api-asset-allocation-detail",
    ),
    re_path(
        r"^asset-requests/(?P<pk>\d+)?$",
        AssetRequestAPIView.as_view(),
        name="api-asset-request-detail",
    ),
    path(
        "asset-return/<int:pk>", AssetReturnAPIView.as_view(), name="api-asset-return"
    ),
    path(
        "asset-reject/<int:pk>", AssetRejectAPIView.as_view(), name="api-asset-reject"
    ),
    path(
        "asset-approve/<int:pk>",
        AssetApproveAPIView.as_view(),
        name="api-asset-approve",
    ),
]
