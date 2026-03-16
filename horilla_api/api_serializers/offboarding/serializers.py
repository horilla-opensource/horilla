"""
horilla_api/api_serializers/offboarding/serializers.py
"""

from rest_framework import serializers

from base.models import Company
from employee.models import Employee
from offboarding.models import (
    EmployeeTask,
    ExitReason,
    Offboarding,
    OffboardingEmployee,
    OffboardingNote,
    OffboardingStage,
    OffboardingTask,
    ResignationLetter,
)


class OffboardingSerializer(serializers.ModelSerializer):
    managers = serializers.SerializerMethodField()
    managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="managers",
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
    offboarding_stages = serializers.SerializerMethodField()

    class Meta:
        model = Offboarding
        fields = "__all__"
        extra_kwargs = {
            "managers": {"read_only": True},
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

    def get_company_id(self, obj):
        if obj.company_id:
            return {
                "id": obj.company_id.id,
                "company": obj.company_id.company,
            }
        return None

    def get_offboarding_stages(self, obj):
        stages = obj.offboardingstage_set.all()
        if stages.exists():
            return [
                {
                    "id": stage.id,
                    "title": stage.title,
                    "type": stage.type,
                }
                for stage in stages
            ]
        return []


class OffboardingStageSerializer(serializers.ModelSerializer):
    offboarding_id = serializers.SerializerMethodField()
    offboarding_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Offboarding.objects.all(),
        source="offboarding_id",
        write_only=True,
        required=False,
    )
    managers = serializers.SerializerMethodField()
    managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="managers",
        write_only=True,
        required=False,
    )

    class Meta:
        model = OffboardingStage
        fields = "__all__"
        extra_kwargs = {
            "managers": {"read_only": True},
        }

    def get_offboarding_id(self, obj):
        if obj.offboarding_id:
            return {
                "id": obj.offboarding_id.id,
                "title": obj.offboarding_id.title,
            }
        return None

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


class OffboardingEmployeeSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    stage_id = serializers.SerializerMethodField()
    stage_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingStage.objects.all(),
        source="stage_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = OffboardingEmployee
        fields = "__all__"

    def get_employee_id(self, obj):
        if obj.employee_id:
            return {
                "id": obj.employee_id.id,
                "employee_first_name": obj.employee_id.employee_first_name,
                "employee_last_name": obj.employee_id.employee_last_name,
                "get_full_name": obj.employee_id.get_full_name(),
            }
        return None

    def get_stage_id(self, obj):
        if obj.stage_id:
            return {
                "id": obj.stage_id.id,
                "title": obj.stage_id.title,
                "type": obj.stage_id.type,
            }
        return None


class ResignationLetterSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    offboarding_employee_id = serializers.SerializerMethodField()
    offboarding_employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingEmployee.objects.all(),
        source="offboarding_employee_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = ResignationLetter
        fields = "__all__"

    def get_employee_id(self, obj):
        if obj.employee_id:
            return {
                "id": obj.employee_id.id,
                "employee_first_name": obj.employee_id.employee_first_name,
                "employee_last_name": obj.employee_id.employee_last_name,
                "get_full_name": obj.employee_id.get_full_name(),
            }
        return None

    def get_offboarding_employee_id(self, obj):
        if obj.offboarding_employee_id:
            return {
                "id": obj.offboarding_employee_id.id,
                "employee_id": (
                    {
                        "id": obj.offboarding_employee_id.employee_id.id,
                        "get_full_name": obj.offboarding_employee_id.employee_id.get_full_name(),
                    }
                    if obj.offboarding_employee_id.employee_id
                    else None
                ),
            }
        return None


class OffboardingTaskSerializer(serializers.ModelSerializer):
    stage_id = serializers.SerializerMethodField()
    stage_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingStage.objects.all(),
        source="stage_id",
        write_only=True,
        required=False,
    )
    managers = serializers.SerializerMethodField()
    managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="managers",
        write_only=True,
        required=False,
    )

    class Meta:
        model = OffboardingTask
        fields = "__all__"
        extra_kwargs = {
            "managers": {"read_only": True},
        }

    def get_stage_id(self, obj):
        if obj.stage_id:
            return {
                "id": obj.stage_id.id,
                "title": obj.stage_id.title,
            }
        return None

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


class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingEmployee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    task_id = serializers.SerializerMethodField()
    task_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingTask.objects.all(),
        source="task_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = EmployeeTask
        fields = "__all__"

    def get_employee_id(self, obj):
        if obj.employee_id:
            return {
                "id": obj.employee_id.id,
                "employee_id": (
                    {
                        "id": obj.employee_id.employee_id.id,
                        "employee_first_name": obj.employee_id.employee_id.employee_first_name,
                        "employee_last_name": obj.employee_id.employee_id.employee_last_name,
                        "get_full_name": obj.employee_id.employee_id.get_full_name(),
                    }
                    if obj.employee_id.employee_id
                    else None
                ),
            }
        return None

    def get_task_id(self, obj):
        if obj.task_id:
            return {
                "id": obj.task_id.id,
                "title": obj.task_id.title,
            }
        return None


class OffboardingNoteSerializer(serializers.ModelSerializer):
    note_by = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingEmployee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    stage_id = serializers.SerializerMethodField()
    stage_id_write = serializers.PrimaryKeyRelatedField(
        queryset=OffboardingStage.objects.all(),
        source="stage_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = OffboardingNote
        fields = "__all__"

    def get_note_by(self, obj):
        if obj.note_by:
            return {
                "id": obj.note_by.id,
                "employee_first_name": obj.note_by.employee_first_name,
                "employee_last_name": obj.note_by.employee_last_name,
                "get_full_name": obj.note_by.get_full_name(),
            }
        return None

    def get_employee_id(self, obj):
        if obj.employee_id:
            return {
                "id": obj.employee_id.id,
                "employee_id": (
                    {
                        "id": obj.employee_id.employee_id.id,
                        "get_full_name": obj.employee_id.employee_id.get_full_name(),
                    }
                    if obj.employee_id.employee_id
                    else None
                ),
            }
        return None

    def get_stage_id(self, obj):
        if obj.stage_id:
            return {
                "id": obj.stage_id.id,
                "title": obj.stage_id.title,
            }
        return None
