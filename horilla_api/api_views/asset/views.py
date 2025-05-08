from datetime import date

from django.http import QueryDict
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from asset.filters import AssetFilter
from asset.models import *

from ...api_filters.asset.filters import AssetCategoryFilter
from ...api_serializers.asset.serializers import *


class AssetAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssetFilter

    def get_asset(self, pk):
        try:
            return Asset.objects.get(pk=pk)
        except Asset.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk=None):
        if pk:
            asset = self.get_asset(pk)
            serializer = AssetSerializer(asset)
            return Response(serializer.data)
        paginator = PageNumberPagination()
        queryset = Asset.objects.all()
        filterset = self.filterset_class(request.GET, queryset=queryset)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = AssetGetAllSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AssetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        asset = self.get_asset(pk)
        serializer = AssetSerializer(asset, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        asset = self.get_asset(pk)
        asset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetCategoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssetCategoryFilter

    def get_asset_category(self, pk):
        try:
            return AssetCategory.objects.get(pk=pk)
        except AssetCategory.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk=None):
        if pk:
            asset_category = self.get_asset_category(pk)
            serializer = AssetCategorySerializer(asset_category)
            return Response(serializer.data)
        paginator = PageNumberPagination()
        queryset = AssetCategory.objects.all()
        filterset = self.filterset_class(request.GET, queryset=queryset)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = AssetCategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AssetCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        asset_category = self.get_asset_category(pk)
        serializer = AssetCategorySerializer(asset_category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        asset_category = self.get_asset_category(pk)
        asset_category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetLotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_lot(self, pk):
        try:
            return AssetLot.objects.get(pk=pk)
        except AssetLot.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk=None):
        if pk:
            asset_lot = self.get_asset_lot(pk)
            serializer = AssetLotSerializer(asset_lot)
            return Response(serializer.data)
        paginator = PageNumberPagination()
        assets = AssetLot.objects.all()
        page = paginator.paginate_queryset(assets, request)
        serializer = AssetLotSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AssetLotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        asset_lot = self.get_asset_lot(pk)
        serializer = AssetLotSerializer(asset_lot, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        asset_lot = self.get_asset_lot(pk)
        asset_lot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetAllocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_assignment(self, pk):
        try:
            return AssetAssignment.objects.get(pk=pk)
        except AssetAssignment.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk=None):
        if pk:
            asset_assignment = self.get_asset_assignment(pk)
            serializer = AssetAssignmentGetSerializer(asset_assignment)
            return Response(serializer.data)
        paginator = PageNumberPagination()
        assets = AssetAssignment.objects.all()
        page = paginator.paginate_queryset(assets, request)
        serializer = AssetAssignmentGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AssetAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        asset_assignment = self.get_asset_assignment(pk)
        serializer = AssetAssignmentSerializer(asset_assignment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        asset_assignment = self.get_asset_assignment(pk)
        asset_assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_request(self, pk):
        try:
            return AssetRequest.objects.get(pk=pk)
        except AssetRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk=None):
        if pk:
            asset_request = self.get_asset_request(pk)
            serializer = AssetRequestGetSerializer(asset_request)
            return Response(serializer.data)
        paginator = PageNumberPagination()
        assets = AssetRequest.objects.all().order_by("-id")
        page = paginator.paginate_queryset(assets, request)
        serializer = AssetRequestGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AssetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        asset_request = self.get_asset_request(pk)
        serializer = AssetRequestSerializer(asset_request, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        asset_request = self.get_asset_request(pk)
        asset_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_request(self, pk):
        try:
            return AssetRequest.objects.get(pk=pk)
        except AssetRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def put(self, request, pk):
        asset_request = self.get_asset_request(pk)
        if asset_request.asset_request_status == "Requested":
            asset_request.asset_request_status = "Rejected"
            asset_request.save()
            return Response(status=204)
        raise serializers.ValidationError({"error": "Access Denied.."})


class AssetApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_request(self, pk):
        try:
            return AssetRequest.objects.get(pk=pk)
        except AssetRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def put(self, request, pk):
        asset_request = self.get_asset_request(pk)
        if asset_request.asset_request_status == "Requested":
            data = request.data
            if isinstance(data, QueryDict):
                data = data.dict()
            data["assigned_to_employee_id"] = asset_request.requested_employee_id.id
            data["assigned_by_employee_id"] = request.user.employee_get.id
            serializer = AssetApproveSerializer(
                data=data, context={"asset_request": asset_request}
            )
            if serializer.is_valid():
                serializer.save()
                asset_id = Asset.objects.get(id=data["asset_id"])
                asset_id.asset_status = "In use"
                asset_id.save()
                asset_request.asset_request_status = "Approved"
                asset_request.save()
                return Response(status=200)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        raise serializers.ValidationError({"error": "Access Denied.."})


class AssetReturnAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_asset_assignment(self, pk):
        try:
            return AssetAssignment.objects.get(pk=pk)
        except AssetAssignment.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def put(self, request, pk):
        asset_assignment = self.get_asset_assignment(pk)
        if request.user.has_perm("app_name.change_mymodel"):
            serializer = AssetReturnSerializer(
                instance=asset_assignment, data=request.data
            )
            if serializer.is_valid():
                images = [
                    ReturnImages.objects.create(image=image)
                    for image in request.data.getlist("image")
                ]
                asset_return = serializer.save()
                asset_return.return_images.set(images)
                if asset_return.return_status == "Healthy":
                    Asset.objects.filter(id=pk).update(asset_status="Available")
                else:
                    Asset.objects.filter(id=pk).update(asset_status="Not-Available")
                AssetAssignment.objects.filter(id=asset_return.id).update(
                    return_date=date.today()
                )
                return Response(status=200)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            AssetAssignment.objects.filter(id=pk).update(return_request=True)
            return Response(status=200)
