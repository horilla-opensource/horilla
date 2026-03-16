"""
horilla_api/api_views/pms/views.py
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla_api.api_serializers.pms.serializers import (
    AnonymousFeedbackSerializer,
    AnswerSerializer,
    BonusPointSettingSerializer,
    CommentSerializer,
    EmployeeBonusPointSerializer,
    EmployeeKeyResultSerializer,
    EmployeeObjectiveSerializer,
    FeedbackSerializer,
    KeyResultFeedbackSerializer,
    KeyResultSerializer,
    MeetingsAnswerSerializer,
    MeetingsSerializer,
    ObjectiveSerializer,
    PeriodSerializer,
    QuestionOptionsSerializer,
    QuestionSerializer,
    QuestionTemplateSerializer,
)
from pms.filters import (
    ActualKeyResultFilter,
    ActualObjectiveFilter,
    AnonymousFilter,
    BonusPointSettingFilter,
    EmployeeBonusPointFilter,
    EmployeeObjectiveFilter,
    FeedbackFilter,
    KeyResultFilter,
    MeetingsFilter,
    ObjectiveFilter,
    PeriodFilter,
    QuestionTemplateFilter,
)
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


# Period Views
class PeriodGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PeriodFilter
    queryset = Period.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Period.objects.none()
        queryset = Period.objects.all()
        user = request.user
        perm = "pms.view_period"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            period = object_check(Period, pk)
            if period is None:
                return Response({"error": "Period not found"}, status=404)
            serializer = PeriodSerializer(period)
            return Response(serializer.data, status=200)

        periods = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=periods)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = PeriodSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_period")
    def post(self, request, **kwargs):
        serializer = PeriodSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PeriodGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        period = object_check(Period, pk)
        if period is None:
            return Response({"error": "Period not found"}, status=404)
        serializer = PeriodSerializer(period)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_period")
    def put(self, request, pk):
        period = object_check(Period, pk)
        if period is None:
            return Response({"error": "Period not found"}, status=404)
        serializer = PeriodSerializer(period, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_period")
    def delete(self, request, pk):
        period = object_check(Period, pk)
        if period is None:
            return Response({"error": "Period not found"}, status=404)
        try:
            period.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# KeyResult Views
class KeyResultGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ActualKeyResultFilter
    queryset = KeyResult.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return KeyResult.objects.none()
        queryset = KeyResult.objects.all()
        user = request.user
        perm = "pms.view_keyresult"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            key_result = object_check(KeyResult, pk)
            if key_result is None:
                return Response({"error": "KeyResult not found"}, status=404)
            serializer = KeyResultSerializer(key_result)
            return Response(serializer.data, status=200)

        key_results = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=key_results)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = KeyResultSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_keyresult")
    def post(self, request, **kwargs):
        serializer = KeyResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KeyResultGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        key_result = object_check(KeyResult, pk)
        if key_result is None:
            return Response({"error": "KeyResult not found"}, status=404)
        serializer = KeyResultSerializer(key_result)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_keyresult")
    def put(self, request, pk):
        key_result = object_check(KeyResult, pk)
        if key_result is None:
            return Response({"error": "KeyResult not found"}, status=404)
        serializer = KeyResultSerializer(key_result, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_keyresult")
    def delete(self, request, pk):
        key_result = object_check(KeyResult, pk)
        if key_result is None:
            return Response({"error": "KeyResult not found"}, status=404)
        try:
            key_result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Objective Views
class ObjectiveGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ActualObjectiveFilter
    queryset = Objective.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Objective.objects.none()
        queryset = Objective.objects.all()
        user = request.user
        perm = "pms.view_objective"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            objective = object_check(Objective, pk)
            if objective is None:
                return Response({"error": "Objective not found"}, status=404)
            serializer = ObjectiveSerializer(objective)
            return Response(serializer.data, status=200)

        objectives = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=objectives)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = ObjectiveSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_objective")
    def post(self, request, **kwargs):
        serializer = ObjectiveSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ObjectiveGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        objective = object_check(Objective, pk)
        if objective is None:
            return Response({"error": "Objective not found"}, status=404)
        serializer = ObjectiveSerializer(objective)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_objective")
    def put(self, request, pk):
        objective = object_check(Objective, pk)
        if objective is None:
            return Response({"error": "Objective not found"}, status=404)
        serializer = ObjectiveSerializer(objective, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_objective")
    def delete(self, request, pk):
        objective = object_check(Objective, pk)
        if objective is None:
            return Response({"error": "Objective not found"}, status=404)
        try:
            objective.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# EmployeeObjective Views
class EmployeeObjectiveGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmployeeObjectiveFilter
    queryset = EmployeeObjective.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None, objective_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return EmployeeObjective.objects.none()
        queryset = EmployeeObjective.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if objective_id:
            queryset = queryset.filter(objective_id=objective_id)
        user = request.user
        perm = "pms.view_employeeobjective"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None, objective_id=None):
        if pk:
            employee_objective = object_check(EmployeeObjective, pk)
            if employee_objective is None:
                return Response({"error": "EmployeeObjective not found"}, status=404)
            serializer = EmployeeObjectiveSerializer(employee_objective)
            return Response(serializer.data, status=200)

        employee_objectives = self.get_queryset(request, employee_id, objective_id)
        filterset = self.filterset_class(request.GET, queryset=employee_objectives)

        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = EmployeeObjectiveSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_employeeobjective")
    def post(self, request, employee_id=None, objective_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        if (
            objective_id
            and not data.get("objective_id_write")
            and not data.get("objective_id")
        ):
            data["objective_id_write"] = objective_id
        serializer = EmployeeObjectiveSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeObjectiveGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        employee_objective = object_check(EmployeeObjective, pk)
        if employee_objective is None:
            return Response({"error": "EmployeeObjective not found"}, status=404)
        serializer = EmployeeObjectiveSerializer(employee_objective)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_employeeobjective")
    def put(self, request, pk):
        employee_objective = object_check(EmployeeObjective, pk)
        if employee_objective is None:
            return Response({"error": "EmployeeObjective not found"}, status=404)
        serializer = EmployeeObjectiveSerializer(
            employee_objective, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_employeeobjective")
    def delete(self, request, pk):
        employee_objective = object_check(EmployeeObjective, pk)
        if employee_objective is None:
            return Response({"error": "EmployeeObjective not found"}, status=404)
        try:
            employee_objective.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# EmployeeKeyResult Views
class EmployeeKeyResultGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = KeyResultFilter
    queryset = EmployeeKeyResult.objects.none()  # For drf-yasg schema generation

    def get_queryset(
        self, request=None, employee_objective_id=None, key_result_id=None
    ):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return EmployeeKeyResult.objects.none()
        queryset = EmployeeKeyResult.objects.all()
        if employee_objective_id:
            queryset = queryset.filter(employee_objective_id=employee_objective_id)
        if key_result_id:
            queryset = queryset.filter(key_result_id=key_result_id)
        user = request.user
        perm = "pms.view_employeekeyresult"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_objective_id=None, key_result_id=None):
        if pk:
            employee_key_result = object_check(EmployeeKeyResult, pk)
            if employee_key_result is None:
                return Response({"error": "EmployeeKeyResult not found"}, status=404)
            serializer = EmployeeKeyResultSerializer(employee_key_result)
            return Response(serializer.data, status=200)

        employee_key_results = self.get_queryset(
            request, employee_objective_id, key_result_id
        )
        filterset = self.filterset_class(request.GET, queryset=employee_key_results)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = EmployeeKeyResultSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_employeekeyresult")
    def post(self, request, employee_objective_id=None, key_result_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_objective_id
            and not data.get("employee_objective_id_write")
            and not data.get("employee_objective_id")
        ):
            data["employee_objective_id_write"] = employee_objective_id
        if (
            key_result_id
            and not data.get("key_result_id_write")
            and not data.get("key_result_id")
        ):
            data["key_result_id_write"] = key_result_id
        serializer = EmployeeKeyResultSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeKeyResultGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        employee_key_result = object_check(EmployeeKeyResult, pk)
        if employee_key_result is None:
            return Response({"error": "EmployeeKeyResult not found"}, status=404)
        serializer = EmployeeKeyResultSerializer(employee_key_result)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_employeekeyresult")
    def put(self, request, pk):
        employee_key_result = object_check(EmployeeKeyResult, pk)
        if employee_key_result is None:
            return Response({"error": "EmployeeKeyResult not found"}, status=404)
        serializer = EmployeeKeyResultSerializer(
            employee_key_result, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_employeekeyresult")
    def delete(self, request, pk):
        employee_key_result = object_check(EmployeeKeyResult, pk)
        if employee_key_result is None:
            return Response({"error": "EmployeeKeyResult not found"}, status=404)
        try:
            employee_key_result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Comment Views
class CommentGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = Comment.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_objective_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Comment.objects.none()
        queryset = Comment.objects.all()
        if employee_objective_id:
            queryset = queryset.filter(employee_objective_id=employee_objective_id)
        user = request.user
        perm = "pms.view_comment"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_objective_id=None):
        if pk:
            comment = object_check(Comment, pk)
            if comment is None:
                return Response({"error": "Comment not found"}, status=404)
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=200)

        comments = self.get_queryset(request, employee_objective_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(comments, request)
        serializer = CommentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_comment")
    def post(self, request, employee_objective_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_objective_id
            and not data.get("employee_objective_id_write")
            and not data.get("employee_objective_id")
        ):
            data["employee_objective_id_write"] = employee_objective_id
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        comment = object_check(Comment, pk)
        if comment is None:
            return Response({"error": "Comment not found"}, status=404)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_comment")
    def put(self, request, pk):
        comment = object_check(Comment, pk)
        if comment is None:
            return Response({"error": "Comment not found"}, status=404)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_comment")
    def delete(self, request, pk):
        comment = object_check(Comment, pk)
        if comment is None:
            return Response({"error": "Comment not found"}, status=404)
        try:
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# QuestionTemplate Views
class QuestionTemplateGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionTemplateFilter
    queryset = QuestionTemplate.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return QuestionTemplate.objects.none()
        queryset = QuestionTemplate.objects.all()
        user = request.user
        perm = "pms.view_questiontemplate"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            template = object_check(QuestionTemplate, pk)
            if template is None:
                return Response({"error": "QuestionTemplate not found"}, status=404)
            serializer = QuestionTemplateSerializer(template)
            return Response(serializer.data, status=200)

        templates = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=templates)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = QuestionTemplateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_questiontemplate")
    def post(self, request, **kwargs):
        serializer = QuestionTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionTemplateGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        template = object_check(QuestionTemplate, pk)
        if template is None:
            return Response({"error": "QuestionTemplate not found"}, status=404)
        serializer = QuestionTemplateSerializer(template)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_questiontemplate")
    def put(self, request, pk):
        template = object_check(QuestionTemplate, pk)
        if template is None:
            return Response({"error": "QuestionTemplate not found"}, status=404)
        serializer = QuestionTemplateSerializer(
            template, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_questiontemplate")
    def delete(self, request, pk):
        template = object_check(QuestionTemplate, pk)
        if template is None:
            return Response({"error": "QuestionTemplate not found"}, status=404)
        try:
            template.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Question Views
class QuestionGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = Question.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, template_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Question.objects.none()
        queryset = Question.objects.all()
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        user = request.user
        perm = "pms.view_question"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, template_id=None):
        if pk:
            question = object_check(Question, pk)
            if question is None:
                return Response({"error": "Question not found"}, status=404)
            serializer = QuestionSerializer(question)
            return Response(serializer.data, status=200)

        questions = self.get_queryset(request, template_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(questions, request)
        serializer = QuestionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_question")
    def post(self, request, template_id=None, **kwargs):
        data = request.data.copy()
        if (
            template_id
            and not data.get("template_id_write")
            and not data.get("template_id")
        ):
            data["template_id_write"] = template_id
        serializer = QuestionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        question = object_check(Question, pk)
        if question is None:
            return Response({"error": "Question not found"}, status=404)
        serializer = QuestionSerializer(question)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_question")
    def put(self, request, pk):
        question = object_check(Question, pk)
        if question is None:
            return Response({"error": "Question not found"}, status=404)
        serializer = QuestionSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_question")
    def delete(self, request, pk):
        question = object_check(Question, pk)
        if question is None:
            return Response({"error": "Question not found"}, status=404)
        try:
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# QuestionOptions Views
class QuestionOptionsGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = QuestionOptions.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, question_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return QuestionOptions.objects.none()
        queryset = QuestionOptions.objects.all()
        if question_id:
            queryset = queryset.filter(question_id=question_id)
        user = request.user
        perm = "pms.view_questionoptions"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, question_id=None):
        if pk:
            options = object_check(QuestionOptions, pk)
            if options is None:
                return Response({"error": "QuestionOptions not found"}, status=404)
            serializer = QuestionOptionsSerializer(options)
            return Response(serializer.data, status=200)

        options_list = self.get_queryset(request, question_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(options_list, request)
        serializer = QuestionOptionsSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_questionoptions")
    def post(self, request, question_id=None, **kwargs):
        data = request.data.copy()
        if (
            question_id
            and not data.get("question_id_write")
            and not data.get("question_id")
        ):
            data["question_id_write"] = question_id
        serializer = QuestionOptionsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionOptionsGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        options = object_check(QuestionOptions, pk)
        if options is None:
            return Response({"error": "QuestionOptions not found"}, status=404)
        serializer = QuestionOptionsSerializer(options)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_questionoptions")
    def put(self, request, pk):
        options = object_check(QuestionOptions, pk)
        if options is None:
            return Response({"error": "QuestionOptions not found"}, status=404)
        serializer = QuestionOptionsSerializer(options, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_questionoptions")
    def delete(self, request, pk):
        options = object_check(QuestionOptions, pk)
        if options is None:
            return Response({"error": "QuestionOptions not found"}, status=404)
        try:
            options.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Feedback Views
class FeedbackGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeedbackFilter
    queryset = Feedback.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Feedback.objects.none()
        queryset = Feedback.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        user = request.user
        perm = "pms.view_feedback"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None):
        if pk:
            feedback = object_check(Feedback, pk)
            if feedback is None:
                return Response({"error": "Feedback not found"}, status=404)
            serializer = FeedbackSerializer(feedback)
            return Response(serializer.data, status=200)

        feedbacks = self.get_queryset(request, employee_id)
        filterset = self.filterset_class(request.GET, queryset=feedbacks)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = FeedbackSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_feedback")
    def post(self, request, employee_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        serializer = FeedbackSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedbackGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        feedback = object_check(Feedback, pk)
        if feedback is None:
            return Response({"error": "Feedback not found"}, status=404)
        serializer = FeedbackSerializer(feedback)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_feedback")
    def put(self, request, pk):
        feedback = object_check(Feedback, pk)
        if feedback is None:
            return Response({"error": "Feedback not found"}, status=404)
        serializer = FeedbackSerializer(feedback, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_feedback")
    def delete(self, request, pk):
        feedback = object_check(Feedback, pk)
        if feedback is None:
            return Response({"error": "Feedback not found"}, status=404)
        try:
            feedback.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Answer Views
class AnswerGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = Answer.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, feedback_id=None, question_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Answer.objects.none()
        queryset = Answer.objects.all()
        if feedback_id:
            queryset = queryset.filter(feedback_id=feedback_id)
        if question_id:
            queryset = queryset.filter(question_id=question_id)
        user = request.user
        perm = "pms.view_answer"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, feedback_id=None, question_id=None):
        if pk:
            answer = object_check(Answer, pk)
            if answer is None:
                return Response({"error": "Answer not found"}, status=404)
            serializer = AnswerSerializer(answer)
            return Response(serializer.data, status=200)

        answers = self.get_queryset(request, feedback_id, question_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(answers, request)
        serializer = AnswerSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_answer")
    def post(self, request, feedback_id=None, question_id=None, **kwargs):
        data = request.data.copy()
        if (
            feedback_id
            and not data.get("feedback_id_write")
            and not data.get("feedback_id")
        ):
            data["feedback_id_write"] = feedback_id
        if (
            question_id
            and not data.get("question_id_write")
            and not data.get("question_id")
        ):
            data["question_id_write"] = question_id
        serializer = AnswerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnswerGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        answer = object_check(Answer, pk)
        if answer is None:
            return Response({"error": "Answer not found"}, status=404)
        serializer = AnswerSerializer(answer)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_answer")
    def put(self, request, pk):
        answer = object_check(Answer, pk)
        if answer is None:
            return Response({"error": "Answer not found"}, status=404)
        serializer = AnswerSerializer(answer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_answer")
    def delete(self, request, pk):
        answer = object_check(Answer, pk)
        if answer is None:
            return Response({"error": "Answer not found"}, status=404)
        try:
            answer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# KeyResultFeedback Views
class KeyResultFeedbackGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = KeyResultFeedback.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, feedback_id=None, key_result_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return KeyResultFeedback.objects.none()
        queryset = KeyResultFeedback.objects.all()
        if feedback_id:
            queryset = queryset.filter(feedback_id=feedback_id)
        if key_result_id:
            queryset = queryset.filter(key_result_id=key_result_id)
        user = request.user
        perm = "pms.view_keyresultfeedback"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, feedback_id=None, key_result_id=None):
        if pk:
            kr_feedback = object_check(KeyResultFeedback, pk)
            if kr_feedback is None:
                return Response({"error": "KeyResultFeedback not found"}, status=404)
            serializer = KeyResultFeedbackSerializer(kr_feedback)
            return Response(serializer.data, status=200)

        kr_feedbacks = self.get_queryset(request, feedback_id, key_result_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(kr_feedbacks, request)
        serializer = KeyResultFeedbackSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_keyresultfeedback")
    def post(self, request, feedback_id=None, key_result_id=None, **kwargs):
        data = request.data.copy()
        if (
            feedback_id
            and not data.get("feedback_id_write")
            and not data.get("feedback_id")
        ):
            data["feedback_id_write"] = feedback_id
        if (
            key_result_id
            and not data.get("key_result_id_write")
            and not data.get("key_result_id")
        ):
            data["key_result_id_write"] = key_result_id
        serializer = KeyResultFeedbackSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KeyResultFeedbackGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        kr_feedback = object_check(KeyResultFeedback, pk)
        if kr_feedback is None:
            return Response({"error": "KeyResultFeedback not found"}, status=404)
        serializer = KeyResultFeedbackSerializer(kr_feedback)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_keyresultfeedback")
    def put(self, request, pk):
        kr_feedback = object_check(KeyResultFeedback, pk)
        if kr_feedback is None:
            return Response({"error": "KeyResultFeedback not found"}, status=404)
        serializer = KeyResultFeedbackSerializer(
            kr_feedback, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_keyresultfeedback")
    def delete(self, request, pk):
        kr_feedback = object_check(KeyResultFeedback, pk)
        if kr_feedback is None:
            return Response({"error": "KeyResultFeedback not found"}, status=404)
        try:
            kr_feedback.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Meetings Views
class MeetingsGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MeetingsFilter
    queryset = Meetings.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Meetings.objects.none()
        queryset = Meetings.objects.all()
        user = request.user
        perm = "pms.view_meetings"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            meeting = object_check(Meetings, pk)
            if meeting is None:
                return Response({"error": "Meetings not found"}, status=404)
            serializer = MeetingsSerializer(meeting)
            return Response(serializer.data, status=200)

        meetings = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=meetings)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = MeetingsSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_meetings")
    def post(self, request, **kwargs):
        serializer = MeetingsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeetingsGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        meeting = object_check(Meetings, pk)
        if meeting is None:
            return Response({"error": "Meetings not found"}, status=404)
        serializer = MeetingsSerializer(meeting)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_meetings")
    def put(self, request, pk):
        meeting = object_check(Meetings, pk)
        if meeting is None:
            return Response({"error": "Meetings not found"}, status=404)
        serializer = MeetingsSerializer(meeting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_meetings")
    def delete(self, request, pk):
        meeting = object_check(Meetings, pk)
        if meeting is None:
            return Response({"error": "Meetings not found"}, status=404)
        try:
            meeting.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# MeetingsAnswer Views
class MeetingsAnswerGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = MeetingsAnswer.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, meeting_id=None, question_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return MeetingsAnswer.objects.none()
        queryset = MeetingsAnswer.objects.all()
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        if question_id:
            queryset = queryset.filter(question_id=question_id)
        user = request.user
        perm = "pms.view_meetingsanswer"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, meeting_id=None, question_id=None):
        if pk:
            answer = object_check(MeetingsAnswer, pk)
            if answer is None:
                return Response({"error": "MeetingsAnswer not found"}, status=404)
            serializer = MeetingsAnswerSerializer(answer)
            return Response(serializer.data, status=200)

        answers = self.get_queryset(request, meeting_id, question_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(answers, request)
        serializer = MeetingsAnswerSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_meetingsanswer")
    def post(self, request, meeting_id=None, question_id=None, **kwargs):
        data = request.data.copy()
        if (
            meeting_id
            and not data.get("meeting_id_write")
            and not data.get("meeting_id")
        ):
            data["meeting_id_write"] = meeting_id
        if (
            question_id
            and not data.get("question_id_write")
            and not data.get("question_id")
        ):
            data["question_id_write"] = question_id
        serializer = MeetingsAnswerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeetingsAnswerGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        answer = object_check(MeetingsAnswer, pk)
        if answer is None:
            return Response({"error": "MeetingsAnswer not found"}, status=404)
        serializer = MeetingsAnswerSerializer(answer)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_meetingsanswer")
    def put(self, request, pk):
        answer = object_check(MeetingsAnswer, pk)
        if answer is None:
            return Response({"error": "MeetingsAnswer not found"}, status=404)
        serializer = MeetingsAnswerSerializer(answer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_meetingsanswer")
    def delete(self, request, pk):
        answer = object_check(MeetingsAnswer, pk)
        if answer is None:
            return Response({"error": "MeetingsAnswer not found"}, status=404)
        try:
            answer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# EmployeeBonusPoint Views
class EmployeeBonusPointGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmployeeBonusPointFilter
    queryset = EmployeeBonusPoint.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, employee_id=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return EmployeeBonusPoint.objects.none()
        queryset = EmployeeBonusPoint.objects.all()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        user = request.user
        perm = "pms.view_employeebonuspoint"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, employee_id=None):
        if pk:
            bonus_point = object_check(EmployeeBonusPoint, pk)
            if bonus_point is None:
                return Response({"error": "EmployeeBonusPoint not found"}, status=404)
            serializer = EmployeeBonusPointSerializer(bonus_point)
            return Response(serializer.data, status=200)

        bonus_points = self.get_queryset(request, employee_id)
        filterset = self.filterset_class(request.GET, queryset=bonus_points)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = EmployeeBonusPointSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_employeebonuspoint")
    def post(self, request, employee_id=None, **kwargs):
        data = request.data.copy()
        if (
            employee_id
            and not data.get("employee_id_write")
            and not data.get("employee_id")
        ):
            data["employee_id_write"] = employee_id
        serializer = EmployeeBonusPointSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeBonusPointGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bonus_point = object_check(EmployeeBonusPoint, pk)
        if bonus_point is None:
            return Response({"error": "EmployeeBonusPoint not found"}, status=404)
        serializer = EmployeeBonusPointSerializer(bonus_point)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_employeebonuspoint")
    def put(self, request, pk):
        bonus_point = object_check(EmployeeBonusPoint, pk)
        if bonus_point is None:
            return Response({"error": "EmployeeBonusPoint not found"}, status=404)
        serializer = EmployeeBonusPointSerializer(
            bonus_point, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_employeebonuspoint")
    def delete(self, request, pk):
        bonus_point = object_check(EmployeeBonusPoint, pk)
        if bonus_point is None:
            return Response({"error": "EmployeeBonusPoint not found"}, status=404)
        try:
            bonus_point.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# BonusPointSetting Views
class BonusPointSettingGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BonusPointSettingFilter
    queryset = BonusPointSetting.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return BonusPointSetting.objects.none()
        return BonusPointSetting.objects.all()

    def get(self, request, pk=None):
        if pk:
            setting = object_check(BonusPointSetting, pk)
            if setting is None:
                return Response({"error": "BonusPointSetting not found"}, status=404)
            serializer = BonusPointSettingSerializer(setting)
            return Response(serializer.data, status=200)

        settings = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=settings)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = BonusPointSettingSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_bonuspointsetting")
    def post(self, request, **kwargs):
        serializer = BonusPointSettingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BonusPointSettingGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        setting = object_check(BonusPointSetting, pk)
        if setting is None:
            return Response({"error": "BonusPointSetting not found"}, status=404)
        serializer = BonusPointSettingSerializer(setting)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_bonuspointsetting")
    def put(self, request, pk):
        setting = object_check(BonusPointSetting, pk)
        if setting is None:
            return Response({"error": "BonusPointSetting not found"}, status=404)
        serializer = BonusPointSettingSerializer(
            setting, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_bonuspointsetting")
    def delete(self, request, pk):
        setting = object_check(BonusPointSetting, pk)
        if setting is None:
            return Response({"error": "BonusPointSetting not found"}, status=404)
        try:
            setting.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# AnonymousFeedback Views
class AnonymousFeedbackGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AnonymousFilter
    queryset = AnonymousFeedback.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        if getattr(self, "swagger_fake_view", False) or request is None:
            return AnonymousFeedback.objects.none()
        queryset = AnonymousFeedback.objects.all()
        user = request.user
        perm = "pms.view_anonymousfeedback"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            feedback = object_check(AnonymousFeedback, pk)
            if feedback is None:
                return Response({"error": "AnonymousFeedback not found"}, status=404)
            serializer = AnonymousFeedbackSerializer(feedback)
            return Response(serializer.data, status=200)

        feedbacks = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=feedbacks)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = AnonymousFeedbackSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("pms.add_anonymousfeedback")
    def post(self, request, **kwargs):
        serializer = AnonymousFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnonymousFeedbackGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        feedback = object_check(AnonymousFeedback, pk)
        if feedback is None:
            return Response({"error": "AnonymousFeedback not found"}, status=404)
        serializer = AnonymousFeedbackSerializer(feedback)
        return Response(serializer.data, status=200)

    @permission_required("pms.change_anonymousfeedback")
    def put(self, request, pk):
        feedback = object_check(AnonymousFeedback, pk)
        if feedback is None:
            return Response({"error": "AnonymousFeedback not found"}, status=404)
        serializer = AnonymousFeedbackSerializer(
            feedback, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("pms.delete_anonymousfeedback")
    def delete(self, request, pk):
        feedback = object_check(AnonymousFeedback, pk)
        if feedback is None:
            return Response({"error": "AnonymousFeedback not found"}, status=404)
        try:
            feedback.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
