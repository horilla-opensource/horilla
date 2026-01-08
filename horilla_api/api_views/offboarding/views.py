"""
horilla_api/api_views/offboarding/views.py
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
from horilla_api.api_serializers.offboarding.serializers import (
    EmployeeTaskSerializer,
    OffboardingEmployeeSerializer,
    OffboardingNoteSerializer,
    OffboardingSerializer,
    OffboardingStageSerializer,
    OffboardingTaskSerializer,
    ResignationLetterSerializer,
)
from offboarding.filters import (
    LetterFilter,
    PipelineEmployeeFilter,
    PipelineFilter,
    PipelineStageFilter,
)
from offboarding.models import (
    EmployeeTask,
    Offboarding,
    OffboardingEmployee,
    OffboardingNote,
    OffboardingStage,
    OffboardingTask,
    ResignationLetter,
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


# Offboarding Views
class OffboardingGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PipelineFilter
    queryset = Offboarding.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Offboarding.objects.none()
        queryset = Offboarding.objects.all()
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_offboarding"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            offboarding = object_check(Offboarding, pk)
            if offboarding is None:
                return Response({"error": "Offboarding not found"}, status=404)
            serializer = OffboardingSerializer(offboarding)
            return Response(serializer.data, status=200)

        offboardings = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=offboardings)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = OffboardingSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_offboarding")
    def post(self, request, **kwargs):
        serializer = OffboardingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OffboardingGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        offboarding = object_check(Offboarding, pk)
        if offboarding is None:
            return Response({"error": "Offboarding not found"}, status=404)
        serializer = OffboardingSerializer(offboarding)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_offboarding")
    def put(self, request, pk):
        offboarding = object_check(Offboarding, pk)
        if offboarding is None:
            return Response({"error": "Offboarding not found"}, status=404)
        serializer = OffboardingSerializer(offboarding, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_offboarding")
    def delete(self, request, pk):
        offboarding = object_check(Offboarding, pk)
        if offboarding is None:
            return Response({"error": "Offboarding not found"}, status=404)
        try:
            offboarding.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Offboarding Stage Views
class OffboardingStageGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PipelineStageFilter
    queryset = OffboardingStage.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, offboarding_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OffboardingStage.objects.none()
        queryset = OffboardingStage.objects.all()
        if offboarding_id:
            queryset = queryset.filter(offboarding_id=offboarding_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_offboardingstage"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, offboarding_id=None):
        if pk:
            stage = object_check(OffboardingStage, pk)
            if stage is None:
                return Response({"error": "OffboardingStage not found"}, status=404)
            serializer = OffboardingStageSerializer(stage)
            return Response(serializer.data, status=200)

        stages = self.get_queryset(request, offboarding_id)
        filterset = self.filterset_class(request.GET, queryset=stages)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = OffboardingStageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_offboardingstage")
    def post(self, request, offboarding_id=None, **kwargs):
        data = request.data.copy()
        if (
            offboarding_id
            and not data.get("offboarding_id_write")
            and not data.get("offboarding_id")
        ):
            data["offboarding_id_write"] = offboarding_id
        serializer = OffboardingStageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OffboardingStageGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        stage = object_check(OffboardingStage, pk)
        if stage is None:
            return Response({"error": "OffboardingStage not found"}, status=404)
        serializer = OffboardingStageSerializer(stage)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_offboardingstage")
    def put(self, request, pk):
        stage = object_check(OffboardingStage, pk)
        if stage is None:
            return Response({"error": "OffboardingStage not found"}, status=404)
        serializer = OffboardingStageSerializer(stage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_offboardingstage")
    def delete(self, request, pk):
        stage = object_check(OffboardingStage, pk)
        if stage is None:
            return Response({"error": "OffboardingStage not found"}, status=404)
        try:
            stage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Offboarding Employee Views
class OffboardingEmployeeGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PipelineEmployeeFilter
    queryset = OffboardingEmployee.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, stage_id=None, offboarding_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OffboardingEmployee.objects.none()
        queryset = OffboardingEmployee.objects.all()
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        if offboarding_id:
            queryset = queryset.filter(stage_id__offboarding_id=offboarding_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_offboardingemployee"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, stage_id=None, offboarding_id=None):
        if pk:
            employee = object_check(OffboardingEmployee, pk)
            if employee is None:
                return Response({"error": "OffboardingEmployee not found"}, status=404)
            serializer = OffboardingEmployeeSerializer(employee)
            return Response(serializer.data, status=200)

        employees = self.get_queryset(request, stage_id, offboarding_id)
        filterset = self.filterset_class(request.GET, queryset=employees)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = OffboardingEmployeeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_offboardingemployee")
    def post(self, request, stage_id=None, **kwargs):
        data = request.data.copy()
        if stage_id and not data.get("stage_id_write") and not data.get("stage_id"):
            data["stage_id_write"] = stage_id
        serializer = OffboardingEmployeeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OffboardingEmployeeGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        employee = object_check(OffboardingEmployee, pk)
        if employee is None:
            return Response({"error": "OffboardingEmployee not found"}, status=404)
        serializer = OffboardingEmployeeSerializer(employee)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_offboardingemployee")
    def put(self, request, pk):
        employee = object_check(OffboardingEmployee, pk)
        if employee is None:
            return Response({"error": "OffboardingEmployee not found"}, status=404)
        serializer = OffboardingEmployeeSerializer(
            employee, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_offboardingemployee")
    def delete(self, request, pk):
        employee = object_check(OffboardingEmployee, pk)
        if employee is None:
            return Response({"error": "OffboardingEmployee not found"}, status=404)
        try:
            employee.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Resignation Letter Views
class ResignationLetterGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LetterFilter
    queryset = ResignationLetter.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return ResignationLetter.objects.none()
        queryset = ResignationLetter.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_resignationletter"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None):
        if pk:
            letter = object_check(ResignationLetter, pk)
            if letter is None:
                return Response({"error": "ResignationLetter not found"}, status=404)
            serializer = ResignationLetterSerializer(letter)
            return Response(serializer.data, status=200)

        letters = self.get_queryset(request, employee_id)
        filterset = self.filterset_class(request.GET, queryset=letters)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = ResignationLetterSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_resignationletter")
    def post(self, request, employee_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        serializer = ResignationLetterSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResignationLetterGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        letter = object_check(ResignationLetter, pk)
        if letter is None:
            return Response({"error": "ResignationLetter not found"}, status=404)
        serializer = ResignationLetterSerializer(letter)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_resignationletter")
    def put(self, request, pk):
        letter = object_check(ResignationLetter, pk)
        if letter is None:
            return Response({"error": "ResignationLetter not found"}, status=404)
        serializer = ResignationLetterSerializer(
            letter, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_resignationletter")
    def delete(self, request, pk):
        letter = object_check(ResignationLetter, pk)
        if letter is None:
            return Response({"error": "ResignationLetter not found"}, status=404)
        try:
            letter.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Offboarding Task Views
class OffboardingTaskGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = OffboardingTask.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, stage_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OffboardingTask.objects.none()
        queryset = OffboardingTask.objects.all()
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_offboardingtask"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, stage_id=None):
        if pk:
            task = object_check(OffboardingTask, pk)
            if task is None:
                return Response({"error": "OffboardingTask not found"}, status=404)
            serializer = OffboardingTaskSerializer(task)
            return Response(serializer.data, status=200)

        tasks = self.get_queryset(request, stage_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = OffboardingTaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_offboardingtask")
    def post(self, request, stage_id=None, **kwargs):
        data = request.data.copy()
        if stage_id and not data.get("stage_id_write") and not data.get("stage_id"):
            data["stage_id_write"] = stage_id
        serializer = OffboardingTaskSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OffboardingTaskGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = object_check(OffboardingTask, pk)
        if task is None:
            return Response({"error": "OffboardingTask not found"}, status=404)
        serializer = OffboardingTaskSerializer(task)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_offboardingtask")
    def put(self, request, pk):
        task = object_check(OffboardingTask, pk)
        if task is None:
            return Response({"error": "OffboardingTask not found"}, status=404)
        serializer = OffboardingTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_offboardingtask")
    def delete(self, request, pk):
        task = object_check(OffboardingTask, pk)
        if task is None:
            return Response({"error": "OffboardingTask not found"}, status=404)
        try:
            task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Employee Task Views
class EmployeeTaskGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = EmployeeTask.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None, task_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return EmployeeTask.objects.none()
        queryset = EmployeeTask.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_employeetask"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None, task_id=None):
        if pk:
            employee_task = object_check(EmployeeTask, pk)
            if employee_task is None:
                return Response({"error": "EmployeeTask not found"}, status=404)
            serializer = EmployeeTaskSerializer(employee_task)
            return Response(serializer.data, status=200)

        employee_tasks = self.get_queryset(request, employee_id, task_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(employee_tasks, request)
        serializer = EmployeeTaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_employeetask")
    def post(self, request, employee_id=None, task_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        if task_id and not data.get("task_id_write") and not data.get("task_id"):
            data["task_id_write"] = task_id
        serializer = EmployeeTaskSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeTaskGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        employee_task = object_check(EmployeeTask, pk)
        if employee_task is None:
            return Response({"error": "EmployeeTask not found"}, status=404)
        serializer = EmployeeTaskSerializer(employee_task)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_employeetask")
    def put(self, request, pk):
        employee_task = object_check(EmployeeTask, pk)
        if employee_task is None:
            return Response({"error": "EmployeeTask not found"}, status=404)
        serializer = EmployeeTaskSerializer(
            employee_task, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_employeetask")
    def delete(self, request, pk):
        employee_task = object_check(EmployeeTask, pk)
        if employee_task is None:
            return Response({"error": "EmployeeTask not found"}, status=404)
        try:
            employee_task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Offboarding Note Views
class OffboardingNoteGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = OffboardingNote.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None, stage_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return OffboardingNote.objects.none()
        queryset = OffboardingNote.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "offboarding.view_offboardingnote"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None, stage_id=None):
        if pk:
            note = object_check(OffboardingNote, pk)
            if note is None:
                return Response({"error": "OffboardingNote not found"}, status=404)
            serializer = OffboardingNoteSerializer(note)
            return Response(serializer.data, status=200)

        notes = self.get_queryset(request, employee_id, stage_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(notes, request)
        serializer = OffboardingNoteSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("offboarding.add_offboardingnote")
    def post(self, request, employee_id=None, stage_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        if stage_id and not data.get("stage_id_write") and not data.get("stage_id"):
            data["stage_id_write"] = stage_id
        serializer = OffboardingNoteSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OffboardingNoteGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        note = object_check(OffboardingNote, pk)
        if note is None:
            return Response({"error": "OffboardingNote not found"}, status=404)
        serializer = OffboardingNoteSerializer(note)
        return Response(serializer.data, status=200)

    @permission_required("offboarding.change_offboardingnote")
    def put(self, request, pk):
        note = object_check(OffboardingNote, pk)
        if note is None:
            return Response({"error": "OffboardingNote not found"}, status=404)
        serializer = OffboardingNoteSerializer(note, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("offboarding.delete_offboardingnote")
    def delete(self, request, pk):
        note = object_check(OffboardingNote, pk)
        if note is None:
            return Response({"error": "OffboardingNote not found"}, status=404)
        try:
            note.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
