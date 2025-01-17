from datetime import date
from typing import Optional

from django.db import transaction
from django.http import QueryDict
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from asset.filters import AssetFilter
from asset.models import Asset, AssetCategory, AssetLot, AssetAssignment, AssetRequest, ReturnImages
from asset.api_filters.asset.filters import AssetCategoryFilter
from asset.api_serializers.asset.serializers import (
    AssetSerializer, AssetGetAllSerializer, AssetCategorySerializer,
    AssetLotSerializer, AssetAssignmentGetSerializer, AssetAssignmentSerializer,
    AssetRequestGetSerializer, AssetRequestSerializer, AssetApproveSerializer,
    AssetReturnSerializer
)

class BaseModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    pagination_class = PageNumberPagination

    def get_object_or_404(self, pk: int):
        try:
            return self.queryset.get(pk=pk)
        except self.queryset.model.DoesNotExist as e:
            raise ValidationError(str(e))

class AssetViewSet(BaseModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssetFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetGetAllSerializer
        return AssetSerializer

class AssetCategoryViewSet(BaseModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssetCategoryFilter

class AssetLotViewSet(BaseModelViewSet):
    queryset = AssetLot.objects.all()
    serializer_class = AssetLotSerializer

class AssetAssignmentViewSet(BaseModelViewSet):
    queryset = AssetAssignment.objects.all()
    serializer_class = AssetAssignmentSerializer

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AssetAssignmentGetSerializer
        return AssetAssignmentSerializer

    @action(detail=True, methods=['put'])
    @transaction.atomic
    def return_asset(self, request, pk=None):
        assignment = self.get_object_or_404(pk)
        
        if not request.user.has_perm('asset.change_assetassignment'):
            assignment.return_request = True
            assignment.save()
            return Response(status=status.HTTP_200_OK)

        serializer = AssetReturnSerializer(instance=assignment, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        images = [
            ReturnImages.objects.create(image=image)
            for image in request.data.getlist('image')
        ]
        
        asset_return = serializer.save()
        asset_return.return_images.set(images)
        
        # Update asset status based on return condition
        new_status = 'Available' if asset_return.return_status == 'Healthy' else 'Not-Available'
        Asset.objects.filter(id=pk).update(asset_status=new_status)
        
        # Update return date
        assignment.return_date = date.today()
        assignment.save()
        
        return Response(status=status.HTTP_200_OK)

class AssetRequestViewSet(BaseModelViewSet):
    queryset = AssetRequest.objects.all().order_by('-id')
    serializer_class = AssetRequestSerializer

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AssetRequestGetSerializer
        return AssetRequestSerializer

    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        asset_request = self.get_object_or_404(pk)
        if asset_request.asset_request_status != 'Requested':
            raise ValidationError({'error': 'Access Denied - Invalid request status'})
            
        asset_request.asset_request_status = 'Rejected'
        asset_request.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['put'])
    @transaction.atomic
    def approve(self, request, pk=None):
        asset_request = self.get_object_or_404(pk)
        if asset_request.asset_request_status != 'Requested':
            raise ValidationError({'error': 'Access Denied - Invalid request status'})

        data = request.data.dict() if isinstance(request.data, QueryDict) else request.data
        data.update({
            'assigned_to_employee_id': asset_request.requested_employee_id.id,
            'assigned_by_employee_id': request.user.employee_get.id
        })

        serializer = AssetApproveSerializer(
            data=data,
            context={'asset_request': asset_request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            serializer.save()
            Asset.objects.filter(id=data['asset_id']).update(asset_status='In use')
            asset_request.asset_request_status = 'Approved'
            asset_request.save()

        return Response(status=status.HTTP_200_OK)
