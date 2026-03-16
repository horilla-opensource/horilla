"""
horilla_api/api_views/recruitment/views.py
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
from horilla_api.api_serializers.recruitment.serializers import (
    CandidateDocumentRequestSerializer,
    CandidateDocumentSerializer,
    CandidateRatingSerializer,
    CandidateSerializer,
    InterviewScheduleSerializer,
    LinkedInAccountSerializer,
    RecruitmentSerializer,
    RejectedCandidateSerializer,
    RejectReasonSerializer,
    SkillSerializer,
    SkillZoneCandidateSerializer,
    SkillZoneSerializer,
    StageSerializer,
    SurveyTemplateSerializer,
)
from recruitment.filters import (
    CandidateFilter,
    InterviewFilter,
    LinkedInAccountFilter,
    RecruitmentFilter,
    RejectReasonFilter,
    SkillsFilter,
    SkillZoneCandFilter,
    SkillZoneFilter,
    StageFilter,
    SurveyTemplateFilter,
)
from recruitment.models import (
    Candidate,
    CandidateDocument,
    CandidateDocumentRequest,
    CandidateRating,
    InterviewSchedule,
    LinkedInAccount,
    Recruitment,
    RejectedCandidate,
    RejectReason,
    Skill,
    SkillZone,
    SkillZoneCandidate,
    Stage,
    SurveyTemplate,
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


# Recruitment Views
class RecruitmentGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecruitmentFilter
    queryset = Recruitment.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Recruitment.objects.none()
        queryset = Recruitment.objects.all()
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_recruitment"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            recruitment = object_check(Recruitment, pk)
            if recruitment is None:
                return Response({"error": "Recruitment not found"}, status=404)
            serializer = RecruitmentSerializer(recruitment)
            return Response(serializer.data, status=200)

        recruitments = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=recruitments)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = RecruitmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_recruitment")
    def post(self, request, **kwargs):
        serializer = RecruitmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecruitmentGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        recruitment = object_check(Recruitment, pk)
        if recruitment is None:
            return Response({"error": "Recruitment not found"}, status=404)
        serializer = RecruitmentSerializer(recruitment)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_recruitment")
    def put(self, request, pk):
        recruitment = object_check(Recruitment, pk)
        if recruitment is None:
            return Response({"error": "Recruitment not found"}, status=404)
        serializer = RecruitmentSerializer(recruitment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_recruitment")
    def delete(self, request, pk):
        recruitment = object_check(Recruitment, pk)
        if recruitment is None:
            return Response({"error": "Recruitment not found"}, status=404)
        try:
            recruitment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Stage Views
class StageGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = StageFilter
    queryset = Stage.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, recruitment_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Stage.objects.none()
        queryset = Stage.objects.all()
        if recruitment_id:
            queryset = queryset.filter(recruitment_id=recruitment_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_stage"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, recruitment_id=None):
        if pk:
            stage = object_check(Stage, pk)
            if stage is None:
                return Response({"error": "Stage not found"}, status=404)
            serializer = StageSerializer(stage)
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
        serializer = StageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_stage")
    def post(self, request, recruitment_id=None, **kwargs):
        data = request.data.copy()
        if (
            recruitment_id
            and not data.get("recruitment_id_write")
            and not data.get("recruitment_id")
        ):
            data["recruitment_id_write"] = recruitment_id
        serializer = StageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StageGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        stage = object_check(Stage, pk)
        if stage is None:
            return Response({"error": "Stage not found"}, status=404)
        serializer = StageSerializer(stage)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_stage")
    def put(self, request, pk):
        stage = object_check(Stage, pk)
        if stage is None:
            return Response({"error": "Stage not found"}, status=404)
        serializer = StageSerializer(stage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_stage")
    def delete(self, request, pk):
        stage = object_check(Stage, pk)
        if stage is None:
            return Response({"error": "Stage not found"}, status=404)
        try:
            stage.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Views
class CandidateGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CandidateFilter
    queryset = Candidate.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, recruitment_id=None, stage_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Candidate.objects.none()
        queryset = Candidate.objects.all()
        if recruitment_id:
            queryset = queryset.filter(recruitment_id=recruitment_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_candidate"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, recruitment_id=None, stage_id=None):
        if pk:
            candidate = object_check(Candidate, pk)
            if candidate is None:
                return Response({"error": "Candidate not found"}, status=404)
            serializer = CandidateSerializer(candidate)
            return Response(serializer.data, status=200)

        candidates = self.get_queryset(request, recruitment_id, stage_id)
        filterset = self.filterset_class(request.GET, queryset=candidates)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = CandidateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_candidate")
    def post(self, request, recruitment_id=None, stage_id=None, **kwargs):
        data = request.data.copy()
        if (
            recruitment_id
            and not data.get("recruitment_id_write")
            and not data.get("recruitment_id")
        ):
            data["recruitment_id_write"] = recruitment_id
        if stage_id and not data.get("stage_id_write") and not data.get("stage_id"):
            data["stage_id_write"] = stage_id
        serializer = CandidateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        candidate = object_check(Candidate, pk)
        if candidate is None:
            return Response({"error": "Candidate not found"}, status=404)
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_candidate")
    def put(self, request, pk):
        candidate = object_check(Candidate, pk)
        if candidate is None:
            return Response({"error": "Candidate not found"}, status=404)
        serializer = CandidateSerializer(candidate, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_candidate")
    def delete(self, request, pk):
        candidate = object_check(Candidate, pk)
        if candidate is None:
            return Response({"error": "Candidate not found"}, status=404)
        try:
            candidate.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Interview Schedule Views
class InterviewScheduleGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = InterviewFilter
    queryset = InterviewSchedule.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return InterviewSchedule.objects.none()
        queryset = InterviewSchedule.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_interviewschedule"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None):
        if pk:
            interview = object_check(InterviewSchedule, pk)
            if interview is None:
                return Response({"error": "InterviewSchedule not found"}, status=404)
            serializer = InterviewScheduleSerializer(interview)
            return Response(serializer.data, status=200)

        interviews = self.get_queryset(request, candidate_id)
        filterset = self.filterset_class(request.GET, queryset=interviews)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = InterviewScheduleSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_interviewschedule")
    def post(self, request, candidate_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        serializer = InterviewScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InterviewScheduleGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        interview = object_check(InterviewSchedule, pk)
        if interview is None:
            return Response({"error": "InterviewSchedule not found"}, status=404)
        serializer = InterviewScheduleSerializer(interview)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_interviewschedule")
    def put(self, request, pk):
        interview = object_check(InterviewSchedule, pk)
        if interview is None:
            return Response({"error": "InterviewSchedule not found"}, status=404)
        serializer = InterviewScheduleSerializer(
            interview, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_interviewschedule")
    def delete(self, request, pk):
        interview = object_check(InterviewSchedule, pk)
        if interview is None:
            return Response({"error": "InterviewSchedule not found"}, status=404)
        try:
            interview.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Skill Views
class SkillGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SkillsFilter
    queryset = Skill.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return Skill.objects.none()
        return Skill.objects.all()

    def get(self, request, pk=None):
        if pk:
            skill = object_check(Skill, pk)
            if skill is None:
                return Response({"error": "Skill not found"}, status=404)
            serializer = SkillSerializer(skill)
            return Response(serializer.data, status=200)

        skills = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=skills)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = SkillSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_skill")
    def post(self, request, **kwargs):
        serializer = SkillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SkillGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        skill = object_check(Skill, pk)
        if skill is None:
            return Response({"error": "Skill not found"}, status=404)
        serializer = SkillSerializer(skill)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_skill")
    def put(self, request, pk):
        skill = object_check(Skill, pk)
        if skill is None:
            return Response({"error": "Skill not found"}, status=404)
        serializer = SkillSerializer(skill, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_skill")
    def delete(self, request, pk):
        skill = object_check(Skill, pk)
        if skill is None:
            return Response({"error": "Skill not found"}, status=404)
        try:
            skill.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Survey Template Views
class SurveyTemplateGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SurveyTemplateFilter
    queryset = SurveyTemplate.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return SurveyTemplate.objects.none()
        queryset = SurveyTemplate.objects.all()
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_surveytemplate"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            template = object_check(SurveyTemplate, pk)
            if template is None:
                return Response({"error": "SurveyTemplate not found"}, status=404)
            serializer = SurveyTemplateSerializer(template)
            return Response(serializer.data, status=200)

        templates = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=templates)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = SurveyTemplateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_surveytemplate")
    def post(self, request, **kwargs):
        serializer = SurveyTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SurveyTemplateGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        template = object_check(SurveyTemplate, pk)
        if template is None:
            return Response({"error": "SurveyTemplate not found"}, status=404)
        serializer = SurveyTemplateSerializer(template)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_surveytemplate")
    def put(self, request, pk):
        template = object_check(SurveyTemplate, pk)
        if template is None:
            return Response({"error": "SurveyTemplate not found"}, status=404)
        serializer = SurveyTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_surveytemplate")
    def delete(self, request, pk):
        template = object_check(SurveyTemplate, pk)
        if template is None:
            return Response({"error": "SurveyTemplate not found"}, status=404)
        try:
            template.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Skill Zone Views
class SkillZoneGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SkillZoneFilter
    queryset = SkillZone.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return SkillZone.objects.none()
        queryset = SkillZone.objects.all()
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_skillzone"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            skill_zone = object_check(SkillZone, pk)
            if skill_zone is None:
                return Response({"error": "SkillZone not found"}, status=404)
            serializer = SkillZoneSerializer(skill_zone)
            return Response(serializer.data, status=200)

        skill_zones = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=skill_zones)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = SkillZoneSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_skillzone")
    def post(self, request, **kwargs):
        serializer = SkillZoneSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SkillZoneGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        skill_zone = object_check(SkillZone, pk)
        if skill_zone is None:
            return Response({"error": "SkillZone not found"}, status=404)
        serializer = SkillZoneSerializer(skill_zone)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_skillzone")
    def put(self, request, pk):
        skill_zone = object_check(SkillZone, pk)
        if skill_zone is None:
            return Response({"error": "SkillZone not found"}, status=404)
        serializer = SkillZoneSerializer(skill_zone, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_skillzone")
    def delete(self, request, pk):
        skill_zone = object_check(SkillZone, pk)
        if skill_zone is None:
            return Response({"error": "SkillZone not found"}, status=404)
        try:
            skill_zone.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Skill Zone Candidate Views
class SkillZoneCandidateGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SkillZoneCandFilter
    queryset = SkillZoneCandidate.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None, skill_zone_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return SkillZoneCandidate.objects.none()
        queryset = SkillZoneCandidate.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if skill_zone_id:
            queryset = queryset.filter(skill_zone_id=skill_zone_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_skillzonecandidate"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None, skill_zone_id=None):
        if pk:
            skill_zone_candidate = object_check(SkillZoneCandidate, pk)
            if skill_zone_candidate is None:
                return Response({"error": "SkillZoneCandidate not found"}, status=404)
            serializer = SkillZoneCandidateSerializer(skill_zone_candidate)
            return Response(serializer.data, status=200)

        skill_zone_candidates = self.get_queryset(request, candidate_id, skill_zone_id)
        filterset = self.filterset_class(request.GET, queryset=skill_zone_candidates)

        # groupby section
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = SkillZoneCandidateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_skillzonecandidate")
    def post(self, request, candidate_id=None, skill_zone_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        if (
            skill_zone_id
            and not data.get("skill_zone_id_write")
            and not data.get("skill_zone_id")
        ):
            data["skill_zone_id_write"] = skill_zone_id
        serializer = SkillZoneCandidateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SkillZoneCandidateGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        skill_zone_candidate = object_check(SkillZoneCandidate, pk)
        if skill_zone_candidate is None:
            return Response({"error": "SkillZoneCandidate not found"}, status=404)
        serializer = SkillZoneCandidateSerializer(skill_zone_candidate)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_skillzonecandidate")
    def put(self, request, pk):
        skill_zone_candidate = object_check(SkillZoneCandidate, pk)
        if skill_zone_candidate is None:
            return Response({"error": "SkillZoneCandidate not found"}, status=404)
        serializer = SkillZoneCandidateSerializer(
            skill_zone_candidate, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_skillzonecandidate")
    def delete(self, request, pk):
        skill_zone_candidate = object_check(SkillZoneCandidate, pk)
        if skill_zone_candidate is None:
            return Response({"error": "SkillZoneCandidate not found"}, status=404)
        try:
            skill_zone_candidate.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Rating Views
class CandidateRatingGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = CandidateRating.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return CandidateRating.objects.none()
        queryset = CandidateRating.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_candidaterating"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None):
        if pk:
            rating = object_check(CandidateRating, pk)
            if rating is None:
                return Response({"error": "CandidateRating not found"}, status=404)
            serializer = CandidateRatingSerializer(rating)
            return Response(serializer.data, status=200)

        ratings = self.get_queryset(request, candidate_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(ratings, request)
        serializer = CandidateRatingSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_candidaterating")
    def post(self, request, candidate_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        serializer = CandidateRatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateRatingGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        rating = object_check(CandidateRating, pk)
        if rating is None:
            return Response({"error": "CandidateRating not found"}, status=404)
        serializer = CandidateRatingSerializer(rating)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_candidaterating")
    def put(self, request, pk):
        rating = object_check(CandidateRating, pk)
        if rating is None:
            return Response({"error": "CandidateRating not found"}, status=404)
        serializer = CandidateRatingSerializer(rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_candidaterating")
    def delete(self, request, pk):
        rating = object_check(CandidateRating, pk)
        if rating is None:
            return Response({"error": "CandidateRating not found"}, status=404)
        try:
            rating.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Reject Reason Views
class RejectReasonGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RejectReasonFilter
    queryset = RejectReason.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return RejectReason.objects.none()
        queryset = RejectReason.objects.all()
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_rejectreason"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            reason = object_check(RejectReason, pk)
            if reason is None:
                return Response({"error": "RejectReason not found"}, status=404)
            serializer = RejectReasonSerializer(reason)
            return Response(serializer.data, status=200)

        reasons = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=reasons)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = RejectReasonSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_rejectreason")
    def post(self, request, **kwargs):
        serializer = RejectReasonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RejectReasonGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reason = object_check(RejectReason, pk)
        if reason is None:
            return Response({"error": "RejectReason not found"}, status=404)
        serializer = RejectReasonSerializer(reason)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_rejectreason")
    def put(self, request, pk):
        reason = object_check(RejectReason, pk)
        if reason is None:
            return Response({"error": "RejectReason not found"}, status=404)
        serializer = RejectReasonSerializer(reason, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_rejectreason")
    def delete(self, request, pk):
        reason = object_check(RejectReason, pk)
        if reason is None:
            return Response({"error": "RejectReason not found"}, status=404)
        try:
            reason.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Rejected Candidate Views
class RejectedCandidateGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = RejectedCandidate.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return RejectedCandidate.objects.none()
        queryset = RejectedCandidate.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_rejectedcandidate"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None):
        if pk:
            rejected = object_check(RejectedCandidate, pk)
            if rejected is None:
                return Response({"error": "RejectedCandidate not found"}, status=404)
            serializer = RejectedCandidateSerializer(rejected)
            return Response(serializer.data, status=200)

        rejected_candidates = self.get_queryset(request, candidate_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(rejected_candidates, request)
        serializer = RejectedCandidateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_rejectedcandidate")
    def post(self, request, candidate_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        serializer = RejectedCandidateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RejectedCandidateGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        rejected = object_check(RejectedCandidate, pk)
        if rejected is None:
            return Response({"error": "RejectedCandidate not found"}, status=404)
        serializer = RejectedCandidateSerializer(rejected)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_rejectedcandidate")
    def put(self, request, pk):
        rejected = object_check(RejectedCandidate, pk)
        if rejected is None:
            return Response({"error": "RejectedCandidate not found"}, status=404)
        serializer = RejectedCandidateSerializer(
            rejected, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_rejectedcandidate")
    def delete(self, request, pk):
        rejected = object_check(RejectedCandidate, pk)
        if rejected is None:
            return Response({"error": "RejectedCandidate not found"}, status=404)
        try:
            rejected.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Document Request Views
class CandidateDocumentRequestGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = CandidateDocumentRequest.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return CandidateDocumentRequest.objects.none()
        queryset = CandidateDocumentRequest.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_candidatedocumentrequest"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None):
        if pk:
            doc_request = object_check(CandidateDocumentRequest, pk)
            if doc_request is None:
                return Response(
                    {"error": "CandidateDocumentRequest not found"}, status=404
                )
            serializer = CandidateDocumentRequestSerializer(doc_request)
            return Response(serializer.data, status=200)

        doc_requests = self.get_queryset(request, candidate_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(doc_requests, request)
        serializer = CandidateDocumentRequestSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_candidatedocumentrequest")
    def post(self, request, candidate_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        serializer = CandidateDocumentRequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateDocumentRequestGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc_request = object_check(CandidateDocumentRequest, pk)
        if doc_request is None:
            return Response({"error": "CandidateDocumentRequest not found"}, status=404)
        serializer = CandidateDocumentRequestSerializer(doc_request)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_candidatedocumentrequest")
    def put(self, request, pk):
        doc_request = object_check(CandidateDocumentRequest, pk)
        if doc_request is None:
            return Response({"error": "CandidateDocumentRequest not found"}, status=404)
        serializer = CandidateDocumentRequestSerializer(
            doc_request, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_candidatedocumentrequest")
    def delete(self, request, pk):
        doc_request = object_check(CandidateDocumentRequest, pk)
        if doc_request is None:
            return Response({"error": "CandidateDocumentRequest not found"}, status=404)
        try:
            doc_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Candidate Document Views
class CandidateDocumentGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = CandidateDocument.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None, candidate_id=None, document_request_id=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return CandidateDocument.objects.none()
        queryset = CandidateDocument.objects.all()
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if document_request_id:
            queryset = queryset.filter(document_request_id=document_request_id)
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_candidatedocument"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None, candidate_id=None, document_request_id=None):
        if pk:
            document = object_check(CandidateDocument, pk)
            if document is None:
                return Response({"error": "CandidateDocument not found"}, status=404)
            serializer = CandidateDocumentSerializer(document)
            return Response(serializer.data, status=200)

        documents = self.get_queryset(request, candidate_id, document_request_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(documents, request)
        serializer = CandidateDocumentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_candidatedocument")
    def post(self, request, candidate_id=None, document_request_id=None, **kwargs):
        data = request.data.copy()
        if (
            candidate_id
            and not data.get("candidate_id_write")
            and not data.get("candidate_id")
        ):
            data["candidate_id_write"] = candidate_id
        if (
            document_request_id
            and not data.get("document_request_id_write")
            and not data.get("document_request_id")
        ):
            data["document_request_id_write"] = document_request_id
        serializer = CandidateDocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CandidateDocumentGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        document = object_check(CandidateDocument, pk)
        if document is None:
            return Response({"error": "CandidateDocument not found"}, status=404)
        serializer = CandidateDocumentSerializer(document)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_candidatedocument")
    def put(self, request, pk):
        document = object_check(CandidateDocument, pk)
        if document is None:
            return Response({"error": "CandidateDocument not found"}, status=404)
        serializer = CandidateDocumentSerializer(
            document, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_candidatedocument")
    def delete(self, request, pk):
        document = object_check(CandidateDocument, pk)
        if document is None:
            return Response({"error": "CandidateDocument not found"}, status=404)
        try:
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# LinkedIn Account Views
class LinkedInAccountGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LinkedInAccountFilter
    queryset = LinkedInAccount.objects.none()  # For drf-yasg schema generation

    def get_queryset(self, request=None):
        # Handle schema generation for DRF-YASG
        if getattr(self, "swagger_fake_view", False) or request is None:
            return LinkedInAccount.objects.none()
        queryset = LinkedInAccount.objects.all()
        user = request.user
        # checking user level permissions
        perm = "recruitment.view_linkedinaccount"
        queryset = permission_based_queryset(user, perm, queryset, user_obj=True)
        return queryset

    def get(self, request, pk=None):
        if pk:
            account = object_check(LinkedInAccount, pk)
            if account is None:
                return Response({"error": "LinkedInAccount not found"}, status=404)
            serializer = LinkedInAccountSerializer(account)
            return Response(serializer.data, status=200)

        accounts = self.get_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=accounts)

        # pagination section
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = LinkedInAccountSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @permission_required("recruitment.add_linkedinaccount")
    def post(self, request, **kwargs):
        serializer = LinkedInAccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LinkedInAccountGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        account = object_check(LinkedInAccount, pk)
        if account is None:
            return Response({"error": "LinkedInAccount not found"}, status=404)
        serializer = LinkedInAccountSerializer(account)
        return Response(serializer.data, status=200)

    @permission_required("recruitment.change_linkedinaccount")
    def put(self, request, pk):
        account = object_check(LinkedInAccount, pk)
        if account is None:
            return Response({"error": "LinkedInAccount not found"}, status=404)
        serializer = LinkedInAccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @permission_required("recruitment.delete_linkedinaccount")
    def delete(self, request, pk):
        account = object_check(LinkedInAccount, pk)
        if account is None:
            return Response({"error": "LinkedInAccount not found"}, status=404)
        try:
            account.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
