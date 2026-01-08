"""
horilla_api/api_urls/onboarding/urls.py
"""

from django.urls import path

from horilla_api.api_views.onboarding.views import *

urlpatterns = [
    # Onboarding Stage URLs
    path("onboarding-stage/", OnboardingStageGetCreateAPIView.as_view()),
    path("onboarding-stage/<int:pk>/", OnboardingStageGetUpdateDeleteAPIView.as_view()),
    path(
        "recruitment/<int:recruitment_id>/onboarding-stage/",
        OnboardingStageGetCreateAPIView.as_view(),
    ),
    # Onboarding Task URLs
    path("onboarding-task/", OnboardingTaskGetCreateAPIView.as_view()),
    path("onboarding-task/<int:pk>/", OnboardingTaskGetUpdateDeleteAPIView.as_view()),
    path(
        "onboarding-stage/<int:stage_id>/onboarding-task/",
        OnboardingTaskGetCreateAPIView.as_view(),
    ),
    # Candidate Stage URLs
    path("candidate-stage/", CandidateStageGetCreateAPIView.as_view()),
    path("candidate-stage/<int:pk>/", CandidateStageGetUpdateDeleteAPIView.as_view()),
    path(
        "candidate/<int:candidate_id>/candidate-stage/",
        CandidateStageGetCreateAPIView.as_view(),
    ),
    path(
        "onboarding-stage/<int:stage_id>/candidate-stage/",
        CandidateStageGetCreateAPIView.as_view(),
    ),
    # Candidate Task URLs
    path("candidate-task/", CandidateTaskGetCreateAPIView.as_view()),
    path("candidate-task/<int:pk>/", CandidateTaskGetUpdateDeleteAPIView.as_view()),
    path(
        "candidate/<int:candidate_id>/candidate-task/",
        CandidateTaskGetCreateAPIView.as_view(),
    ),
    path(
        "onboarding-task/<int:task_id>/candidate-task/",
        CandidateTaskGetCreateAPIView.as_view(),
    ),
    path(
        "onboarding-stage/<int:stage_id>/candidate-task/",
        CandidateTaskGetCreateAPIView.as_view(),
    ),
    # Onboarding Portal URLs
    path("onboarding-portal/", OnboardingPortalGetCreateAPIView.as_view()),
    path(
        "onboarding-portal/<int:pk>/", OnboardingPortalGetUpdateDeleteAPIView.as_view()
    ),
    path(
        "candidate/<int:candidate_id>/onboarding-portal/",
        OnboardingPortalGetCreateAPIView.as_view(),
    ),
]
