"""
offboarding/urls.py

This module is used to register url mappings to functions
"""

from django.apps import apps
from django.urls import path

from offboarding import views

urlpatterns = [
    path("offboarding-pipeline", views.pipeline, name="offboarding-pipeline"),
    path("create-offboarding", views.create_offboarding, name="create-offboarding"),
    path(
        "delete-offboarding/<int:id>",
        views.delete_offboarding,
        name="delete-offboarding",
    ),
    path(
        "create-offboarding-stage", views.create_stage, name="create-offboarding-stage"
    ),
    path("add-employee", views.add_employee, name="add-employee"),
    path(
        "delete-offboarding-stage", views.delete_stage, name="delete-offboarding-stage"
    ),
    path(
        "offboarding-change-stage", views.change_stage, name="offboarding-change-stage"
    ),
    path(
        "view-offboarding-note/<int:employee_id>/",
        views.view_notes,
        name="view-offboarding-note",
    ),
    path("add-offboarding-note", views.add_note, name="add-offboarding-note"),
    path(
        "delete-note-attachment", views.delete_attachment, name="delete-note-attachment"
    ),
    path("offboarding-add-task", views.add_task, name="offboarding-add-task"),
    path("update-task-status", views.update_task_status, name="update-task-status"),
    path("offboarding-assign-task", views.task_assign, name="offboarding-assign-task"),
    path(
        "delete-offboarding-employee",
        views.delete_employee,
        name="delete-offboarding-employee",
    ),
    path("delete-offboarding-task", views.delete_task, name="delete-offboarding-task"),
    path(
        "offboarding-individual-view/<int:emp_id>/",
        views.offboarding_individual_view,
        name="offboarding-individual-view",
    ),
    path(
        "offboarding-note-delete/<int:note_id>/",
        views.offboarding_note_delete,
        name="offboarding-note-delete",
    ),
    path(
        "resignation-requests-view/",
        views.request_view,
        name="resignation-request-view",
    ),
    path(
        "resignation-requests-single-view/<int:id>/",
        views.request_single_view,
        name="resignation-request-single-view",
    ),
    path(
        "create-resignation-request",
        views.create_resignation_request,
        name="create-resignation-request",
    ),
    path(
        "search-resignation-request",
        views.search_resignation_request,
        name="search-resignation-request",
    ),
    path(
        "delete-resignation-request",
        views.delete_resignation_request,
        name="delete-resignation-request",
    ),
    path("update-letter-status", views.update_status, name="update-letter-status"),
    path(
        "enable-resignation-request",
        views.enable_resignation_request,
        name="enable-resignation-request",
    ),
    path("get-notice-period", views.get_notice_period, name="get-notice-period"),
    path(
        "get-notice-period-end-date",
        views.get_notice_period_end_date,
        name="get-notice-period-end-date",
    ),
    path(
        "offboarding-pipeline-filter",
        views.filter_pipeline,
        name="offboarding-pipeline-filter",
    ),
    path(
        "dashboard",
        views.offboarding_dashboard,
        name="offboarding-dashboard",
    ),
    path(
        "dashboard-task-table",
        views.dashboard_task_table,
        name="dashboard-task-table",
    ),
    path(
        "dashboard-department-chart",
        views.department_job_postion_chart,
        name="dashboard-department-chart",
    ),
    path(
        "dashboard-join-chart",
        views.dashboard_join_chart,
        name="dashboard-join-chart",
    ),
]

if apps.is_installed("asset"):
    urlpatterns += [
        path(
            "dashboard-asset-table",
            views.dashboard_asset_table,
            name="dashboard-asset-table",
        ),
    ]

if apps.is_installed("pms"):
    urlpatterns += [
        path(
            "dashboard-feedback-table",
            views.dashboard_feedback_table,
            name="dashboard-feedback-table",
        ),
    ]
