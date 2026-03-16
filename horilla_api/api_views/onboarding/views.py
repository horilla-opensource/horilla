"""
horilla_api/api_views/onboarding/views.py
"""

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.methods import filtersubordinates
from horilla_api.api_serializers.onboarding.serializers import (
    CandidateStageSerializer,
    CandidateTaskSerializer,
    OnboardingPortalSerializer,
    OnboardingStageSerializer,
    OnboardingTaskSerializer,
)
from onboarding.filters import (
    CandidateTaskFilter,
    OnboardingCandidateFilter,
    OnboardingStageFilter,
    OnboardingTaskFilter,
)
from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
    OnboardingStage,
    OnboardingTask,
)

from ...api_decorators.base.decorators import (
    manager_permission_required,
    permission_required,
)
from ...api_methods.base.methods import groupby_queryset, permission_based_queryset


def object_check(cls, pk):
    try:
        obj = cls.objects.get(id=pk)
        return obj
    except cls.DoesNotExist:
        return None


# Onboarding Stage Views
class OnboardingStageGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OnboardingStageFilter
    queryset = OnboardingStage.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, recruitment_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OnboardingStage.objects.none()
        queryset = OnboardingStage.objects.all()
        if recruitment_id:
            queryset = queryset.filter(recruitment_id=recruitment_id)
        user = request.user
        # checking user level permissions
        perm = "onboarding.view_onboardingstage"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, recruitment_id=None):
        if pk:
            stage = object_check(OnboardingStage, pk)
            if stage is None:
                return Response({"error": "OnboardingStage not found"}, status=404)
            serializer = OnboardingStageSerializer(stage)
            return Response(serializer.data, status=200)

        stages = self.get_queryset(request, recruitment_id)
        filterset = self.filterset_class(request.GET, queryset=stages)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = OnboardingStageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("onboarding.add_onboardingstage")
    def post(self, request, recruitment_id=None, **kwargs):
        data = request.data.copy()
        if recruitment_id and not data.get("recruitment_id_write"):
            data["recruitment_id_write"] = recruitment_id
        serializer = OnboardingStageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OnboardingStageGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        stage = object_check(OnboardingStage, pk)
        if stage is None:
            return Response({"error": "OnboardingStage not found"}, status=404)
        serializer = OnboardingStageSerializer(stage)
        return Response(serializer.data, status=200)

    @permission_required("onboarding.change_onboardingstage")
    def put(self, request, pk):
        stage = object_check(OnboardingStage, pk)
        if stage is None:
            return Response({"error": "OnboardingStage not found"}, status=404)
        serializer = OnboardingStageSerializer(stage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("onboarding.delete_onboardingstage")
    def delete(self, request, pk):
        stage = object_check(OnboardingStage, pk)
        if stage is None:
            return Response({"error": "OnboardingStage not found"}, status=404)
        try:
            stage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Onboarding Task Views
class OnboardingTaskGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OnboardingTaskFilter
    queryset = OnboardingTask.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, stage_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OnboardingTask.objects.none()
        queryset = OnboardingTask.objects.all()
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "onboarding.view_onboardingtask"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, stage_id=None):
        if pk:
            task = object_check(OnboardingTask, pk)
            if task is None:
                return Response({"error": "OnboardingTask not found"}, status=404)
            serializer = OnboardingTaskSerializer(task)
            return Response(serializer.data, status=200)

        tasks = self.get_queryset(request, stage_id)
        filterset = self.filterset_class(request.GET, queryset=tasks)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = OnboardingTaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("onboarding.add_onboardingtask")
    def post(self, request, stage_id=None, **kwargs):
        data = request.data.copy()
        if stage_id and not data.get("stage_id_write"):
            data["stage_id_write"] = stage_id
        serializer = OnboardingTaskSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OnboardingTaskGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = object_check(OnboardingTask, pk)
        if task is None:
            return Response({"error": "OnboardingTask not found"}, status=404)
        serializer = OnboardingTaskSerializer(task)
        return Response(serializer.data, status=200)

    @permission_required("onboarding.change_onboardingtask")
    def put(self, request, pk):
        task = object_check(OnboardingTask, pk)
        if task is None:
            return Response({"error": "OnboardingTask not found"}, status=404)
        serializer = OnboardingTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("onboarding.delete_onboardingtask")
    def delete(self, request, pk):
        task = object_check(OnboardingTask, pk)
        if task is None:
            return Response({"error": "OnboardingTask not found"}, status=404)
        try:
            task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Stage Views
class CandidateStageGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OnboardingCandidateFilter
    queryset = CandidateStage.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None, stage_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return CandidateStage.objects.none()
        queryset = CandidateStage.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if stage_id:
            queryset = queryset.filter(onboarding_stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "onboarding.view_candidatestage"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None, stage_id=None):
        if pk:
            candidate_stage = object_check(CandidateStage, pk)
            if candidate_stage is None:
                return Response({"error": "CandidateStage not found"}, status=404)
            serializer = CandidateStageSerializer(candidate_stage)
            return Response(serializer.data, status=200)

        candidate_stages = self.get_queryset(request, candidate_id, stage_id)
        filterset = self.filterset_class(request.GET, queryset=candidate_stages)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = CandidateStageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("onboarding.add_candidatestage")
    def post(self, request, candidate_id=None, stage_id=None, **kwargs):
        data = request.data.copy()
        if candidate_id and not data.get("candidate_id_write"):
            data["candidate_id_write"] = candidate_id
        if stage_id and not data.get("onboarding_stage_id_write"):
            data["onboarding_stage_id_write"] = stage_id
        serializer = CandidateStageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateStageGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        candidate_stage = object_check(CandidateStage, pk)
        if candidate_stage is None:
            return Response({"error": "CandidateStage not found"}, status=404)
        serializer = CandidateStageSerializer(candidate_stage)
        return Response(serializer.data, status=200)

    @permission_required("onboarding.change_candidatestage")
    def put(self, request, pk):
        candidate_stage = object_check(CandidateStage, pk)
        if candidate_stage is None:
            return Response({"error": "CandidateStage not found"}, status=404)
        serializer = CandidateStageSerializer(
            candidate_stage, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("onboarding.delete_candidatestage")
    def delete(self, request, pk):
        candidate_stage = object_check(CandidateStage, pk)
        if candidate_stage is None:
            return Response({"error": "CandidateStage not found"}, status=404)
        try:
            candidate_stage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Task Views
class CandidateTaskGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CandidateTaskFilter
    queryset = CandidateTask.objects.none()  # For drf-yasg schema generation

    def get_queryset(
        self, request=None, candidate_id=None, task_id=None, stage_id=None
    ):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return CandidateTask.objects.none()
        queryset = CandidateTask.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if task_id:
            queryset = queryset.filter(onboarding_task_id=task_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "onboarding.view_candidatetask"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None, task_id=None, stage_id=None):
        if pk:
            candidate_task = object_check(CandidateTask, pk)
            if candidate_task is None:
                return Response({"error": "CandidateTask not found"}, status=404)
            serializer = CandidateTaskSerializer(candidate_task)
            return Response(serializer.data, status=200)

        candidate_tasks = self.get_queryset(request, candidate_id, task_id, stage_id)
        filterset = self.filterset_class(request.GET, queryset=candidate_tasks)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = CandidateTaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("onboarding.add_candidatetask")
    def post(self, request, candidate_id=None, task_id=None, stage_id=None, **kwargs):
        data = request.data.copy()
        if candidate_id and not data.get("candidate_id_write"):
            data["candidate_id_write"] = candidate_id
        if task_id and not data.get("onboarding_task_id_write"):
            data["onboarding_task_id_write"] = task_id
        if stage_id and not data.get("stage_id_write"):
            data["stage_id_write"] = stage_id
        serializer = CandidateTaskSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateTaskGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        candidate_task = object_check(CandidateTask, pk)
        if candidate_task is None:
            return Response({"error": "CandidateTask not found"}, status=404)
        serializer = CandidateTaskSerializer(candidate_task)
        return Response(serializer.data, status=200)

    @permission_required("onboarding.change_candidatetask")
    def put(self, request, pk):
        candidate_task = object_check(CandidateTask, pk)
        if candidate_task is None:
            return Response({"error": "CandidateTask not found"}, status=404)
        serializer = CandidateTaskSerializer(
            candidate_task, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("onboarding.delete_candidatetask")
    def delete(self, request, pk):
        candidate_task = object_check(CandidateTask, pk)
        if candidate_task is None:
            return Response({"error": "CandidateTask not found"}, status=404)
        try:
            candidate_task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Onboarding Portal Views
class OnboardingPortalGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = OnboardingPortal.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OnboardingPortal.objects.none()
        queryset = OnboardingPortal.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        user = request.user
        # checking user level permissions
        perm = "onboarding.view_onboardingportal"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None):
        if pk:
            portal = object_check(OnboardingPortal, pk)
            if portal is None:
                return Response({"error": "OnboardingPortal not found"}, status=404)
            serializer = OnboardingPortalSerializer(portal)
            return Response(serializer.data, status=200)

        portals = self.get_queryset(request, candidate_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(portals, request)
        serializer = OnboardingPortalSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("onboarding.add_onboardingportal")
    def post(self, request, candidate_id=None, **kwargs):
        data = request.data.copy()
        if candidate_id and not data.get("candidate_id_write"):
            data["candidate_id_write"] = candidate_id
        serializer = OnboardingPortalSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OnboardingPortalGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        portal = object_check(OnboardingPortal, pk)
        if portal is None:
            return Response({"error": "OnboardingPortal not found"}, status=404)
        serializer = OnboardingPortalSerializer(portal)
        return Response(serializer.data, status=200)

    @permission_required("onboarding.change_onboardingportal")
    def put(self, request, pk):
        portal = object_check(OnboardingPortal, pk)
        if portal is None:
            return Response({"error": "OnboardingPortal not found"}, status=404)
        serializer = OnboardingPortalSerializer(portal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("onboarding.delete_onboardingportal")
    def delete(self, request, pk):
        portal = object_check(OnboardingPortal, pk)
        if portal is None:
            return Response({"error": "OnboardingPortal not found"}, status=404)
        try:
            portal.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
