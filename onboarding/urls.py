"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path

from onboarding import views
from recruitment.models import Candidate

urlpatterns = [
    path("stage-creation/<str:obj_id>", views.stage_creation, name="stage-creation"),
    path(
        "stage-update/<int:stage_id>/<int:recruitment_id>",
        views.stage_update,
        name="stage-update",
    ),
    path("stage-delete/<int:stage_id>", views.stage_delete, name="stage-delete"),
    path("task-creation", views.task_creation, name="task-creation"),
    path("task-delete/<int:task_id>", views.task_delete, name="task-delete"),
    path(
        "task-update/<int:task_id>/",
        views.task_update,
        name="task-update",
    ),
    path("candidate-creation", views.candidate_creation, name="candidate-creation"),
    path(
        "candidate-update/<int:obj_id>", views.candidate_update, name="candidate-update"
    ),
    path(
        "candidate-delete/<int:obj_id>", views.candidate_delete, name="candidate-delete"
    ),
    path(
        "candidate-single-view/<int:id>",
        views.candidates_single_view,
        name="candidate-single-view",
        kwargs={"model": Candidate},
    ),
    path("candidates-view/", views.candidates_view, name="candidates-view"),
    path(
        "hired-candidates-view",
        views.hired_candidate_view,
        name="hired-candidates-view",
    ),
    path("candidate-filter", views.candidate_filter, name="candidate-filter"),
    path("email-send", views.email_send, name="email-send"),
    path("onboarding-view/", views.onboarding_view, name="onboarding-view"),
    path("kanban-view", views.kanban_view, name="kanban-view"),
    path(
        "candidate-task-update/<int:taskId>",
        views.candidate_task_update,
        name="candidate-task-update",
    ),
    path(
        "get-status/<int:task_id>",
        views.get_status,
        name="get-status",
    ),
    path(
        "assign-task/<int:task_id>",
        views.assign_task,
        name="assign-task",
    ),
    path(
        "candidate-stage-update/<int:candidate_id>/<int:recruitment_id>/",
        views.candidate_stage_update,
        name="candidate-stage-update",
    ),
    path(
        "candidate-stage-bulk-update",
        views.candidate_stage_bulk_update,
        name="candidate-stage-bulk-update",
    ),
    path(
        "candidate-task-bulk-update",
        views.candidate_task_bulk_update,
        name="candidate-task-bulk-update",
    ),
    path(
        "stage-name-update/<int:stage_id>/",
        views.stage_name_update,
        name="stage-name-update",
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
        "onboard-candidate-chart",
        views.onboard_candidate_chart,
        name="onboard-candidate-chart",
    ),
    path("update-joining", views.update_joining, name="update-joining"),
    path(
        "view-onboarding-dashboard",
        views.view_dashboard,
        name="view-onboarding-dashboard",
    ),
    path("stage-chart", views.dashboard_stage_chart, name="stage-chart"),
    path(
        "candidate-sequence-update",
        views.candidate_sequence_update,
        name="onboarding-candidate-sequence-update",
    ),
    path(
        "stage-sequence-update",
        views.stage_sequence_update,
        name="onboarding-stage-sequence-update",
    ),
    path(
        "send-mail/<int:candidate_id>/",
        views.onboarding_send_mail,
        name="onboarding-send-mail",
    ),
    path(
        "update-probotion-end", views.update_probation_end, name="update-probotion-end"
    ),
    path("task-report-onboarding", views.task_report, name="task-report-onboarding"),
    path(
        "candidate-tasks-status",
        views.candidate_tasks_status,
        name="candidate-tasks-status",
    ),
    path("change-task-status", views.change_task_status, name="change-task-status"),
    path(
        "update-offer-letter-status",
        views.update_offer_letter_status,
        name="update-offer-letter-status",
    ),
    path(
        "add-to-rejected-candidates",
        views.add_to_rejected_candidates,
        name="add-to-rejected-candidates",
    ),
    path(
        "candidate-select-filter-onboarding",
        views.candidate_select_filter,
        name="candidate-select-filter-onboarding",
    ),
    path(
        "candidate-select/", views.candidate_select, name="candidate-select-onboarding"
    ),
    path(
        "offer-letter-bulk-status-update/",
        views.offer_letter_bulk_status_update,
        name="offer-letter-bulk-status-update",
    ),
    path(
        "onboarding-candidate-bulk-delete/",
        views.onboarding_candidate_bulk_delete,
        name="onboarding-candidate-bulk-delete",
    ),
]
