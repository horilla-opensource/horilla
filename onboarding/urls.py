"""
urls.py

This module is used to map url path with view methods.
"""
from django.urls import path
from onboarding import views

urlpatterns = [
    path("stage-creation/<str:obj_id>", views.stage_creation, name="stage-creation"),
    path(
        "stage-update/<int:stage_id>/<int:recruitment_id>",
        views.stage_update,
        name="stage-update",
    ),
    path("stage-delete/<int:stage_id>", views.stage_delete, name="stage-delete"),
    path("task-creation/<str:obj_id>", views.task_creation, name="task-creation"),
    path("task-delete/<int:task_id>", views.task_delete, name="task-delete"),
    path(
        "task-update/<int:task_id>/<int:recruitment_id>",
        views.task_update,
        name="task-update",
    ),
    path("candidate-creation", views.candidate_creation, name="candidate-creation"),
    path("candidate-update/<int:obj_id>", views.candidate_update, name="candidate-update"),
    path("candidate-delete/<int:obj_id>", views.candidate_delete, name="candidate-delete"),
    path("candidates-view", views.candidates_view, name="candidates-view"),
    path("candidate-filter", views.candidate_filter, name="candidate-filter"),
    path("email-send", views.email_send, name="email-send"),
    path("onboarding-view", views.onboarding_view, name="onboarding-view"),
    path(
        "candidate-task-update/<int:obj_id>",
        views.candidate_task_update,
        name="candidate-task-update",
    ),
    path(
        "candidate-stage-update/<int:candidate_id>/<int:recruitment_id>/",
        views.candidate_stage_update,
        name="candidate-stage-update",
    ),
    path("user-creation/<str:token>", views.user_creation, name="user-creation"),
    path("profile-view/<str:token>", views.profile_view, name="profile-view"),
    path(
        "employee-creation/<str:token>",
        views.employee_creation,
        name="employee-creation",
    ),
    path(
        "employee-bank-details/<str:token>",
        views.employee_bank_details,
        name="employee-bank-details",
    ),
    path("welcome-aboard", views.welcome_aboard, name="welcome-aboard"),
    path(
        "hired-candidate-chart",
        views.hired_candidate_chart,
        name="hired-candidate-chart",
    ),
    path(
        "onboard-candidate-chart",
        views.onboard_candidate_chart,
        name="onboard-candidate-chart",
    ),
    path("update-joining",views.update_joining,name="update-joining")
]
