"""
horilla_api/api_serializers/pms/serializers.py
"""

from rest_framework import serializers

from base.models import Company, Department, JobPosition
from employee.models import Employee
from pms.models import (
    AnonymousFeedback,
    Answer,
    BonusPointSetting,
    Comment,
    EmployeeBonusPoint,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    KeyResultFeedback,
    Meetings,
    MeetingsAnswer,
    Objective,
    Period,
    Question,
    QuestionOptions,
    QuestionTemplate,
)


class PeriodSerializer(serializers.ModelSerializer):
    company_id = serializers.SerializerMethodField()
    company_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        many=True,
        source="company_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Period
        fields = "__all__"
        extra_kwargs = {
            "company_id": {"read_only": True},
        }

    def get_company_id(self, obj):
        if obj.company_id.exists():
            return [
                {
                    "id": company.id,
                    "company": company.company,
                }
                for company in obj.company_id.all()
            ]
        return []


class KeyResultSerializer(serializers.ModelSerializer):
    company_id = serializers.SerializerMethodField()
    company_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source="company_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = KeyResult
        fields = "__all__"

    def get_company_id(self, obj):
        if obj.company_id:
            return {
                "id": obj.company_id.id,
                "company": obj.company_id.company,
            }
        return None


class ObjectiveSerializer(serializers.ModelSerializer):
    managers = serializers.SerializerMethodField()
    managers_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="managers",
        write_only=True,
        required=False,
    )
    assignees = serializers.SerializerMethodField()
    assignees_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="assignees",
        write_only=True,
        required=False,
    )
    key_result_id = serializers.SerializerMethodField()
    key_result_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=KeyResult.objects.all(),
        many=True,
        source="key_result_id",
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

    class Meta:
        model = Objective
        fields = "__all__"
        extra_kwargs = {
            "managers": {"read_only": True},
            "assignees": {"read_only": True},
            "key_result_id": {"read_only": True},
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

    def get_assignees(self, obj):
        if obj.assignees.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.assignees.all()
            ]
        return []

    def get_key_result_id(self, obj):
        if obj.key_result_id.exists():
            return [
                {
                    "id": kr.id,
                    "title": kr.title,
                }
                for kr in obj.key_result_id.all()
            ]
        return []

    def get_company_id(self, obj):
        if obj.company_id:
            return {
                "id": obj.company_id.id,
                "company": obj.company_id.company,
            }
        return None


class EmployeeObjectiveSerializer(serializers.ModelSerializer):
    objective_id = serializers.SerializerMethodField()
    objective_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Objective.objects.all(),
        source="objective_id",
        write_only=True,
        required=False,
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    key_result_id = serializers.SerializerMethodField()
    key_result_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=KeyResult.objects.all(),
        many=True,
        source="key_result_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = EmployeeObjective
        fields = "__all__"
        extra_kwargs = {
            "key_result_id": {"read_only": True},
        }

    def get_objective_id(self, obj):
        if obj.objective_id:
            return {
                "id": obj.objective_id.id,
                "title": obj.objective_id.title,
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

    def get_key_result_id(self, obj):
        if obj.key_result_id.exists():
            return [
                {
                    "id": kr.id,
                    "title": kr.title,
                }
                for kr in obj.key_result_id.all()
            ]
        return []


class EmployeeKeyResultSerializer(serializers.ModelSerializer):
    employee_objective_id = serializers.SerializerMethodField()
    employee_objective_id_write = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeObjective.objects.all(),
        source="employee_objective_id",
        write_only=True,
        required=False,
    )
    key_result_id = serializers.SerializerMethodField()
    key_result_id_write = serializers.PrimaryKeyRelatedField(
        queryset=KeyResult.objects.all(),
        source="key_result_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = EmployeeKeyResult
        fields = "__all__"

    def get_employee_objective_id(self, obj):
        if obj.employee_objective_id:
            return {
                "id": obj.employee_objective_id.id,
                "objective": obj.employee_objective_id.objective,
            }
        return None

    def get_key_result_id(self, obj):
        if obj.key_result_id:
            return {
                "id": obj.key_result_id.id,
                "title": obj.key_result_id.title,
            }
        return None


class CommentSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    employee_objective_id = serializers.SerializerMethodField()
    employee_objective_id_write = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeObjective.objects.all(),
        source="employee_objective_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Comment
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

    def get_employee_objective_id(self, obj):
        if obj.employee_objective_id:
            return {
                "id": obj.employee_objective_id.id,
                "objective": obj.employee_objective_id.objective,
            }
        return None


class QuestionTemplateSerializer(serializers.ModelSerializer):
    company_id = serializers.SerializerMethodField()
    company_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        many=True,
        source="company_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = QuestionTemplate
        fields = "__all__"
        extra_kwargs = {
            "company_id": {"read_only": True},
        }

    def get_company_id(self, obj):
        if obj.company_id.exists():
            return [
                {
                    "id": company.id,
                    "company": company.company,
                }
                for company in obj.company_id.all()
            ]
        return []


class QuestionSerializer(serializers.ModelSerializer):
    template_id = serializers.SerializerMethodField()
    template_id_write = serializers.PrimaryKeyRelatedField(
        queryset=QuestionTemplate.objects.all(),
        source="template_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Question
        fields = "__all__"

    def get_template_id(self, obj):
        if obj.template_id:
            return {
                "id": obj.template_id.id,
                "question_template": obj.template_id.question_template,
            }
        return None


class QuestionOptionsSerializer(serializers.ModelSerializer):
    question_id = serializers.SerializerMethodField()
    question_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source="question_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = QuestionOptions
        fields = "__all__"

    def get_question_id(self, obj):
        if obj.question_id:
            return {
                "id": obj.question_id.id,
                "question": obj.question_id.question,
            }
        return None


class FeedbackSerializer(serializers.ModelSerializer):
    manager_id = serializers.SerializerMethodField()
    manager_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="manager_id",
        write_only=True,
        required=False,
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    colleague_id = serializers.SerializerMethodField()
    colleague_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="colleague_id",
        write_only=True,
        required=False,
    )
    subordinate_id = serializers.SerializerMethodField()
    subordinate_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="subordinate_id",
        write_only=True,
        required=False,
    )
    others_id = serializers.SerializerMethodField()
    others_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="others_id",
        write_only=True,
        required=False,
    )
    question_template_id = serializers.SerializerMethodField()
    question_template_id_write = serializers.PrimaryKeyRelatedField(
        queryset=QuestionTemplate.objects.all(),
        source="question_template_id",
        write_only=True,
        required=False,
    )
    employee_key_results_id = serializers.SerializerMethodField()
    employee_key_results_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeKeyResult.objects.all(),
        many=True,
        source="employee_key_results_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Feedback
        fields = "__all__"
        extra_kwargs = {
            "colleague_id": {"read_only": True},
            "subordinate_id": {"read_only": True},
            "others_id": {"read_only": True},
            "employee_key_results_id": {"read_only": True},
        }

    def get_manager_id(self, obj):
        if obj.manager_id:
            return {
                "id": obj.manager_id.id,
                "employee_first_name": obj.manager_id.employee_first_name,
                "employee_last_name": obj.manager_id.employee_last_name,
                "get_full_name": obj.manager_id.get_full_name(),
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

    def get_colleague_id(self, obj):
        if obj.colleague_id.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.colleague_id.all()
            ]
        return []

    def get_subordinate_id(self, obj):
        if obj.subordinate_id.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.subordinate_id.all()
            ]
        return []

    def get_others_id(self, obj):
        if obj.others_id.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.others_id.all()
            ]
        return []

    def get_question_template_id(self, obj):
        if obj.question_template_id:
            return {
                "id": obj.question_template_id.id,
                "question_template": obj.question_template_id.question_template,
            }
        return None

    def get_employee_key_results_id(self, obj):
        if obj.employee_key_results_id.exists():
            return [
                {
                    "id": kr.id,
                    "key_result": kr.key_result,
                }
                for kr in obj.employee_key_results_id.all()
            ]
        return []


class AnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.SerializerMethodField()
    question_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source="question_id",
        write_only=True,
        required=False,
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    feedback_id = serializers.SerializerMethodField()
    feedback_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Feedback.objects.all(),
        source="feedback_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Answer
        fields = "__all__"

    def get_question_id(self, obj):
        if obj.question_id:
            return {
                "id": obj.question_id.id,
                "question": obj.question_id.question,
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

    def get_feedback_id(self, obj):
        if obj.feedback_id:
            return {
                "id": obj.feedback_id.id,
                "review_cycle": obj.feedback_id.review_cycle,
            }
        return None


class KeyResultFeedbackSerializer(serializers.ModelSerializer):
    feedback_id = serializers.SerializerMethodField()
    feedback_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Feedback.objects.all(),
        source="feedback_id",
        write_only=True,
        required=False,
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    key_result_id = serializers.SerializerMethodField()
    key_result_id_write = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeKeyResult.objects.all(),
        source="key_result_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = KeyResultFeedback
        fields = "__all__"

    def get_feedback_id(self, obj):
        if obj.feedback_id:
            return {
                "id": obj.feedback_id.id,
                "review_cycle": obj.feedback_id.review_cycle,
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

    def get_key_result_id(self, obj):
        if obj.key_result_id:
            return {
                "id": obj.key_result_id.id,
                "key_result": obj.key_result_id.key_result,
            }
        return None


class MeetingsSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="employee_id",
        write_only=True,
        required=False,
    )
    manager = serializers.SerializerMethodField()
    manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="manager",
        write_only=True,
        required=False,
    )
    answer_employees = serializers.SerializerMethodField()
    answer_employees_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True,
        source="answer_employees",
        write_only=True,
        required=False,
    )
    question_template = serializers.SerializerMethodField()
    question_template_write = serializers.PrimaryKeyRelatedField(
        queryset=QuestionTemplate.objects.all(),
        source="question_template",
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

    class Meta:
        model = Meetings
        fields = "__all__"
        extra_kwargs = {
            "employee_id": {"read_only": True},
            "manager": {"read_only": True},
            "answer_employees": {"read_only": True},
        }

    def get_employee_id(self, obj):
        if obj.employee_id.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.employee_id.all()
            ]
        return []

    def get_manager(self, obj):
        if obj.manager.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.manager.all()
            ]
        return []

    def get_answer_employees(self, obj):
        if obj.answer_employees.exists():
            return [
                {
                    "id": emp.id,
                    "employee_first_name": emp.employee_first_name,
                    "employee_last_name": emp.employee_last_name,
                    "get_full_name": emp.get_full_name(),
                }
                for emp in obj.answer_employees.all()
            ]
        return []

    def get_question_template(self, obj):
        if obj.question_template:
            return {
                "id": obj.question_template.id,
                "question_template": obj.question_template.question_template,
            }
        return None

    def get_company_id(self, obj):
        if obj.company_id:
            return {
                "id": obj.company_id.id,
                "company": obj.company_id.company,
            }
        return None


class MeetingsAnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.SerializerMethodField()
    question_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source="question_id",
        write_only=True,
        required=False,
    )
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    meeting_id = serializers.SerializerMethodField()
    meeting_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Meetings.objects.all(),
        source="meeting_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = MeetingsAnswer
        fields = "__all__"

    def get_question_id(self, obj):
        if obj.question_id:
            return {
                "id": obj.question_id.id,
                "question": obj.question_id.question,
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

    def get_meeting_id(self, obj):
        if obj.meeting_id:
            return {
                "id": obj.meeting_id.id,
                "title": obj.meeting_id.title,
            }
        return None


class EmployeeBonusPointSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    bonus_point_id = serializers.SerializerMethodField()
    bonus_point_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="bonus_point_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = EmployeeBonusPoint
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

    def get_bonus_point_id(self, obj):
        if obj.bonus_point_id:
            return {
                "id": obj.bonus_point_id.id,
                "points": obj.bonus_point_id.points,
            }
        return None


class BonusPointSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusPointSetting
        fields = "__all__"


class AnonymousFeedbackSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    employee_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee_id",
        write_only=True,
        required=False,
    )
    department_id = serializers.SerializerMethodField()
    department_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department_id",
        write_only=True,
        required=False,
    )
    job_position_id = serializers.SerializerMethodField()
    job_position_id_write = serializers.PrimaryKeyRelatedField(
        queryset=JobPosition.objects.all(),
        source="job_position_id",
        write_only=True,
        required=False,
    )

    class Meta:
        model = AnonymousFeedback
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

    def get_department_id(self, obj):
        if obj.department_id:
            return {
                "id": obj.department_id.id,
                "department": obj.department_id.department,
            }
        return None

    def get_job_position_id(self, obj):
        if obj.job_position_id:
            return {
                "id": obj.job_position_id.id,
                "job_position": obj.job_position_id.job_position,
            }
        return None
