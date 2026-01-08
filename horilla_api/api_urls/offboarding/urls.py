"""
horilla_api/api_urls/offboarding/urls.py
"""

from django.urls import path

from horilla_api.api_views.offboarding.views import *

urlpatterns = [
    # Offboarding URLs
    path("offboarding/", OffboardingGetCreateAPIView.as_view()),
    path("offboarding/<int:pk>/", OffboardingGetUpdateDeleteAPIView.as_view()),
    # Offboarding Stage URLs
    path("offboarding-stage/", OffboardingStageGetCreateAPIView.as_view()),
    path(
        "offboarding-stage/<int:pk>/", OffboardingStageGetUpdateDeleteAPIView.as_view()
    ),
    path(
        "offboarding/<int:offboarding_id>/offboarding-stage/",
        OffboardingStageGetCreateAPIView.as_view(),
    ),
    # Offboarding Employee URLs
    path("offboarding-employee/", OffboardingEmployeeGetCreateAPIView.as_view()),
    path(
        "offboarding-employee/<int:pk>/",
        OffboardingEmployeeGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "offboarding-stage/<int:stage_id>/offboarding-employee/",
        OffboardingEmployeeGetCreateAPIView.as_view(),
    ),
    path(
        "offboarding/<int:offboarding_id>/offboarding-employee/",
        OffboardingEmployeeGetCreateAPIView.as_view(),
    ),
    # Resignation Letter URLs
    path("resignation-letter/", ResignationLetterGetCreateAPIView.as_view()),
    path(
        "resignation-letter/<int:pk>/",
        ResignationLetterGetUpdateDeleteAPIView.as_view(),
    ),
    path(
        "employee/<int:employee_id>/resignation-letter/",
        ResignationLetterGetCreateAPIView.as_view(),
    ),
    # Offboarding Task URLs
    path("offboarding-task/", OffboardingTaskGetCreateAPIView.as_view()),
    path("offboarding-task/<int:pk>/", OffboardingTaskGetUpdateDeleteAPIView.as_view()),
    path(
        "offboarding-stage/<int:stage_id>/offboarding-task/",
        OffboardingTaskGetCreateAPIView.as_view(),
    ),
    # Employee Task URLs
    path("employee-task/", EmployeeTaskGetCreateAPIView.as_view()),
    path("employee-task/<int:pk>/", EmployeeTaskGetUpdateDeleteAPIView.as_view()),
    path(
        "offboarding-employee/<int:employee_id>/employee-task/",
        EmployeeTaskGetCreateAPIView.as_view(),
    ),
    path(
        "offboarding-task/<int:task_id>/employee-task/",
        EmployeeTaskGetCreateAPIView.as_view(),
    ),
    # Offboarding Note URLs
    path("offboarding-note/", OffboardingNoteGetCreateAPIView.as_view()),
    path("offboarding-note/<int:pk>/", OffboardingNoteGetUpdateDeleteAPIView.as_view()),
    path(
        "offboarding-employee/<int:employee_id>/offboarding-note/",
        OffboardingNoteGetCreateAPIView.as_view(),
    ),
    path(
        "offboarding-stage/<int:stage_id>/offboarding-note/",
        OffboardingNoteGetCreateAPIView.as_view(),
    ),
]
