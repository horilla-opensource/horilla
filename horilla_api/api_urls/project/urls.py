"""
horilla_api/api_urls/project/urls.py
"""

from django.urls import path

from horilla_api.api_views.project.views import *

urlpatterns = [
    # Project URLs
    path("project/", ProjectGetCreateAPIView.as_view()),
    path("project/<int:pk>/", ProjectGetUpdateDeleteAPIView.as_view()),
    # Project Stage URLs
    path("project-stage/", ProjectStageGetCreateAPIView.as_view()),
    path("project-stage/<int:pk>/", ProjectStageGetUpdateDeleteAPIView.as_view()),
    path("project/<int:project_id>/stage/", ProjectStageGetCreateAPIView.as_view()),
    # Task URLs
    path("task/", TaskGetCreateAPIView.as_view()),
    path("task/<int:pk>/", TaskGetUpdateDeleteAPIView.as_view()),
    path("project/<int:project_id>/task/", TaskGetCreateAPIView.as_view()),
    # TimeSheet URLs
    path("timesheet/", TimeSheetGetCreateAPIView.as_view()),
    path("timesheet/<int:pk>/", TimeSheetGetUpdateDeleteAPIView.as_view()),
    path("project/<int:project_id>/timesheet/", TimeSheetGetCreateAPIView.as_view()),
    path("task/<int:task_id>/timesheet/", TimeSheetGetCreateAPIView.as_view()),
]
