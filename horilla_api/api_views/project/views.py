"""
horilla_api/api_views/project/views.py
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
from horilla_api.api_serializers.project.serializers import (
    ProjectSerializer,
    ProjectStageSerializer,
    TaskSerializer,
    TimeSheetSerializer,
)
from project.filters import ProjectFilter, TaskAllFilter, TaskFilter, TimeSheetFilter
from project.models import Project, ProjectStage, Task, TimeSheet

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


# Project Views
class ProjectGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    queryset = Project.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Project.objects.none()
        queryset = Project.objects.all()
        user = request.user
        # checking user level permissions
        perm = "project.view_project"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            project = object_check(Project, pk)
            if project is None:
                return Response({"error": "Project not found"}, status=404)
            serializer = ProjectSerializer(project)
            return Response(serializer.data, status=200)

        projects = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=projects)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = ProjectSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("project.add_project")
    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = object_check(Project, pk)
        if project is None:
            return Response({"error": "Project not found"}, status=404)
        serializer = ProjectSerializer(project)
        return Response(serializer.data, status=200)

    @permission_required("project.change_project")
    def put(self, request, pk):
        project = object_check(Project, pk)
        if project is None:
            return Response({"error": "Project not found"}, status=404)
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("project.delete_project")
    def delete(self, request, pk):
        project = object_check(Project, pk)
        if project is None:
            return Response({"error": "Project not found"}, status=404)
        try:
            project.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Project Stage Views
class ProjectStageGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, project_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False):
            return ProjectStage.objects.none()
        if project_id:
            return ProjectStage.objects.filter(project_id=project_id)
        return ProjectStage.objects.all()

    def get(self, request, project_id=None):
        if project_id:
            stages = self.get_queryset(project_id)
        else:
            stages = self.get_queryset()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(stages, request)
        serializer = ProjectStageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("project.add_projectstage")
    def post(self, request, project_id=None, **kwargs):
        data = request.data.copy()
        if (
            project_id
            and not data.get("project_id_write")
            and not data.get("project_id")
        ):
            data["project_id_write"] = project_id
        serializer = ProjectStageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectStageGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        stage = object_check(ProjectStage, pk)
        if stage is None:
            return Response({"error": "ProjectStage not found"}, status=404)
        serializer = ProjectStageSerializer(stage)
        return Response(serializer.data, status=200)

    @permission_required("project.change_projectstage")
    def put(self, request, pk):
        stage = object_check(ProjectStage, pk)
        if stage is None:
            return Response({"error": "ProjectStage not found"}, status=404)
        serializer = ProjectStageSerializer(stage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("project.delete_projectstage")
    def delete(self, request, pk):
        stage = object_check(ProjectStage, pk)
        if stage is None:
            return Response({"error": "ProjectStage not found"}, status=404)
        try:
            stage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Task Views
class TaskGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskAllFilter
    queryset = Task.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, project_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Task.objects.none()
        queryset = Task.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        user = request.user
        # checking user level permissions
        perm = "project.view_task"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, project_id=None):
        if pk:
            task = object_check(Task, pk)
            if task is None:
                return Response({"error": "Task not found"}, status=404)
            serializer = TaskSerializer(task)
            return Response(serializer.data, status=200)

        tasks = self.get_queryset(request, project_id)
        filterset = self.filterset_class(request.GET, queryset=tasks)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("project.add_task")
    def post(self, request, project_id=None, **kwargs):
        data = request.data.copy()
        if (
            project_id
            and not data.get("project_id_write")
            and not data.get("project_id")
        ):
            data["project_id_write"] = project_id
        serializer = TaskSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = object_check(Task, pk)
        if task is None:
            return Response({"error": "Task not found"}, status=404)
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=200)

    @permission_required("project.change_task")
    def put(self, request, pk):
        task = object_check(Task, pk)
        if task is None:
            return Response({"error": "Task not found"}, status=404)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("project.delete_task")
    def delete(self, request, pk):
        task = object_check(Task, pk)
        if task is None:
            return Response({"error": "Task not found"}, status=404)
        try:
            task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# TimeSheet Views
class TimeSheetGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TimeSheetFilter
    queryset = TimeSheet.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, project_id=None, task_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return TimeSheet.objects.none()
        queryset = TimeSheet.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        user = request.user
        # checking user level permissions
        perm = "project.view_timesheet"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, project_id=None, task_id=None):
        if pk:
            timesheet = object_check(TimeSheet, pk)
            if timesheet is None:
                return Response({"error": "TimeSheet not found"}, status=404)
            serializer = TimeSheetSerializer(timesheet)
            return Response(serializer.data, status=200)

        timesheets = self.get_queryset(request, project_id, task_id)
        filterset = self.filterset_class(request.GET, queryset=timesheets)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = TimeSheetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("project.add_timesheet")
    def post(self, request, project_id=None, task_id=None, **kwargs):
        data = request.data.copy()
        if (
            project_id
            and not data.get("project_id_write")
            and not data.get("project_id")
        ):
            data["project_id_write"] = project_id
        if task_id and not data.get("task_id_write") and not data.get("task_id"):
            data["task_id_write"] = task_id
        serializer = TimeSheetSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TimeSheetGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        timesheet = object_check(TimeSheet, pk)
        if timesheet is None:
            return Response({"error": "TimeSheet not found"}, status=404)
        serializer = TimeSheetSerializer(timesheet)
        return Response(serializer.data, status=200)

    @permission_required("project.change_timesheet")
    def put(self, request, pk):
        timesheet = object_check(TimeSheet, pk)
        if timesheet is None:
            return Response({"error": "TimeSheet not found"}, status=404)
        serializer = TimeSheetSerializer(timesheet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("project.delete_timesheet")
    def delete(self, request, pk):
        timesheet = object_check(TimeSheet, pk)
        if timesheet is None:
            return Response({"error": "TimeSheet not found"}, status=404)
        try:
            timesheet.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
