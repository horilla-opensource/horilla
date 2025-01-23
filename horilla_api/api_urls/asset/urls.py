from django.urls import path, include
from rest_framework.routers import DefaultRouter

from ...api_views.asset.views import (
    AssetViewSet,
    AssetCategoryViewSet,
    AssetLotViewSet,
    AssetAssignmentViewSet,
    AssetRequestViewSet,
)


router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='api-asset')
router.register(r'asset-categories', AssetCategoryViewSet, basename='api-asset-category')
router.register(r'asset-lots', AssetLotViewSet, basename='api-asset-lot')
router.register(r'asset-allocations', AssetAssignmentViewSet, basename='api-asset-allocation')
router.register(r'asset-requests', AssetRequestViewSet, basename='api-asset-request')

urlpatterns = [
    
    path('', include(router.urls)),
    
    
    path(
        'asset-return/<int:pk>/',
        AssetAssignmentViewSet.as_view({'put': 'return_asset'}),
        name='api-asset-return'
    ),
    path(
        'asset-reject/<int:pk>/',
        AssetRequestViewSet.as_view({'put': 'reject'}),
        name='api-asset-reject'
    ),
    path(
        'asset-approve/<int:pk>/',
        AssetRequestViewSet.as_view({'put': 'approve'}),
        name='api-asset-approve'
    ),
]
