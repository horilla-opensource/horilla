"""
horilla_api/api_serializers/project/serializers.py
"""

from rest_framework import serializers

from base.models import Company
from employee.models import Employee
from project.models import Project, ProjectStage, Task, TimeSheet


class ProjectStageSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source="project",
        write_only=True,
        required=False,
    )

    class Meta:
        model = ProjectStage
        fields = "__all__"

    def get_project(self, obj):
        if obj.project:
            return {
                "id": obj.project.id,
                "title": obj.project.title,
            }
        return None


class ProjectSerializer(serializers.ModelSerializer):
    managers = serializers.SerializerMethodField()
    managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="managers",
        write_only=True,
        required=False,
    )
    members = serializers.SerializerMethodField()
    members_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="members",
        write_only=True,
        required=False,
    )
    company_id = serializers.SerializerMethodField()
    company_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source="company_id",
        write_only=True,
        required=False,
    )
    project_stages = ProjectStageSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
        extra_kwargs = {
            "managers": {"read_only": True},
            "members": {"read_only": True},
        }

    def get_managers(self, obj):
        if obj.managers.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.managers.all()
            ]
        return []

    def get_members(self, obj):
        if obj.members.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.members.all()
            ]
        return []

    def get_company_id(self, obj):
        if obj.company_id:
            return {
                "id": obj.company_id.id,
                "company": obj.company_id.company,
            }
        return None


class TaskSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source="project",
        write_only=True,
        required=False,
    )
    stage = serializers.SerializerMethodField()
    stage_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectStage.objects.all(),
        source="stage",
        write_only=True,
        required=False,
    )
    task_managers = serializers.SerializerMethodField()
    task_managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="task_managers",
        write_only=True,
        required=False,
    )
    task_members = serializers.SerializerMethodField()
    task_members_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="task_members",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = "__all__"
        extra_kwargs = {
            "task_managers": {"read_only": True},
            "task_members": {"read_only": True},
        }

    def get_project(self, obj):
        if obj.project:
            return {
                "id": obj.project.id,
                "title": obj.project.title,
            }
        return None

    def get_stage(self, obj):
        if obj.stage:
            return {
                "id": obj.stage.id,
                "title": obj.stage.title,
            }
        return None

    def get_task_managers(self, obj):
        if obj.task_managers.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.task_managers.all()
            ]
        return []

    def get_task_members(self, obj):
        if obj.task_members.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.task_members.all()
            ]
        return []


class TimeSheetSerializer(serializers.ModelSerializer):
    project_id = serializers.SerializerMethodField()
    project_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source="project_id",
        write_only=True,
        required=False,
    )
    task_id = serializers.SerializerMethodField()
    task_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), source="task_id", write_only=True, required=False
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = TimeSheet
        fields = "__all__"

    def get_project_id(self, obj):
        if obj.project_id:
            return {
                "id": obj.project_id.id,
                "title": obj.project_id.title,
            }
        return None

    def get_task_id(self, obj):
        if obj.task_id:
            return {
                "id": obj.task_id.id,
                "title": obj.task_id.title,
            }
        return None

    def get_employee_id(self, obj):
        if obj.employee_id:
            return {
                "id": obj.employee_id.id,
                "employee_first_name": obj.employee_id.employee_first_name,
                "employee_last_name": obj.employee_id.employee_last_name,
                "get_full_name": obj.employee_id.get_full_name(),
            }
        return None
