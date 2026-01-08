"""
horilla_api/api_urls/recruitment/urls.py
"""

from django.urls import path

from horilla_api.api_views.recruitment.views import *

urlpatterns = [
    # Recruitment URLs
    path("recruitment/", RecruitmentGetCreateAPIView.as_view()),
    path("recruitment/<int:pk>/", RecruitmentGetUpdateDeleteAPIView.as_view()),
    # Stage URLs
    path("stage/", StageGetCreateAPIView.as_view()),
    path("stage/<int:pk>/", StageGetUpdateDeleteAPIView.as_view()),
    path("recruitment/<int:recruitment_id>/stage/", StageGetCreateAPIView.as_view()),
    # Candidate URLs
    path("candidate/", CandidateGetCreateAPIView.as_view()),
    path("candidate/<int:pk>/", CandidateGetUpdateDeleteAPIView.as_view()),
    path(
        "recruitment/<int:recruitment_id>/candidate/",
        CandidateGetCreateAPIView.as_view(),
    ),
    path("stage/<int:stage_id>/candidate/", CandidateGetCreateAPIView.as_view()),
    # Interview Schedule URLs
    path("interview-schedule/", InterviewScheduleGetCreateAPIView.as_view()),
    path(
        "interview-schedule/<int:pk>/",
        InterviewScheduleGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "candidate/<int:candidate_id>/interview-schedule/",
        InterviewScheduleGetCreateAPIView.as_view(),
    ),
    # Skill URLs
    path("skill/", SkillGetCreateAPIView.as_view()),
    path("skill/<int:pk>/", SkillGetUpdateDeleteAPIView.as_view()),
    # Survey Template URLs
    path("survey-template/", SurveyTemplateGetCreateAPIView.as_view()),
    path("survey-template/<int:pk>/", SurveyTemplateGetUpdateDeleteAPIView.as_view()),
    # Skill Zone URLs
    path("skill-zone/", SkillZoneGetCreateAPIView.as_view()),
    path("skill-zone/<int:pk>/", SkillZoneGetUpdateDeleteAPIView.as_view()),
    # Skill Zone Candidate URLs
    path("skill-zone-candidate/", SkillZoneCandidateGetCreateAPIView.as_view()),
    path(
        "skill-zone-candidate/<int:pk>/",
        SkillZoneCandidateGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "candidate/<int:candidate_id>/skill-zone-candidate/",
        SkillZoneCandidateGetCreateAPIView.as_view(),
    ),
    path(
        "skill-zone/<int:skill_zone_id>/skill-zone-candidate/",
        SkillZoneCandidateGetCreateAPIView.as_view(),
    ),
    # Candidate Rating URLs
    path("candidate-rating/", CandidateRatingGetCreateAPIView.as_view()),
    path("candidate-rating/<int:pk>/", CandidateRatingGetUpdateDeleteAPIView.as_view()),
    path(
        "candidate/<int:candidate_id>/candidate-rating/",
        CandidateRatingGetCreateAPIView.as_view(),
    ),
    # Reject Reason URLs
    path("reject-reason/", RejectReasonGetCreateAPIView.as_view()),
    path("reject-reason/<int:pk>/", RejectReasonGetUpdateDeleteAPIView.as_view()),
    # Rejected Candidate URLs
    path("rejected-candidate/", RejectedCandidateGetCreateAPIView.as_view()),
    path(
        "rejected-candidate/<int:pk>/",
        RejectedCandidateGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "candidate/<int:candidate_id>/rejected-candidate/",
        RejectedCandidateGetCreateAPIView.as_view(),
    ),
    # Candidate Document Request URLs
    path(
        "candidate-document-request/",
        CandidateDocumentRequestGetCreateAPIView.as_view(),
    ),
    path(
        "candidate-document-request/<int:pk>/",
        CandidateDocumentRequestGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "candidate/<int:candidate_id>/candidate-document-request/",
        CandidateDocumentRequestGetCreateAPIView.as_view(),
    ),
    # Candidate Document URLs
    path("candidate-document/", CandidateDocumentGetCreateAPIView.as_view()),
    path(
        "candidate-document/<int:pk>/",
        CandidateDocumentGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "candidate/<int:candidate_id>/candidate-document/",
        CandidateDocumentGetCreateAPIView.as_view(),
    ),
    path(
        "candidate-document-request/<int:document_request_id>/candidate-document/",
        CandidateDocumentGetCreateAPIView.as_view(),
    ),
    # LinkedIn Account URLs
    path("linkedin-account/", LinkedInAccountGetCreateAPIView.as_view()),
    path("linkedin-account/<int:pk>/", LinkedInAccountGetUpdateDeleteAPIView.as_view()),
]
