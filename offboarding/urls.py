"""
offboarding/urls.py

This module is used to register url mappings to functions
"""

from django.apps import apps
from django.urls import path

from horilla_views.cbv_methods import check_feature_enabled
from offboarding import views
from offboarding.cbv import exit_process, resignation, resignation_tab
from offboarding.models import OffboardingGeneralSetting

urlpatterns = [
    path(
        "individual-resignation-tab-list/<int:pk>",
        resignation_tab.ResignationTabView.as_view(),
        name="individual-resignation-tab-list",
    ),
    path(
        "offboarding-pipeline",
        exit_process.OffboardingPipelineView.as_view(),
        name="offboarding-pipeline",
    ),
    # path("create-offboarding", views.create_offboarding, name="create-offboarding"),
    path(
        "create-offboarding",
        exit_process.OffboardingCreateFormView.as_view(),
        name="create-offboarding",
    ),
    path(
        "update-offboarding/<int:pk>/",
        exit_process.OffboardingCreateFormView.as_view(),
        name="update-offboarding",
    ),
    path(
        "delete-offboarding/<int:id>",
        views.delete_offboarding,
        name="delete-offboarding",
    ),
    # path(
    #     "create-offboarding-stage", views.create_stage, name="create-offboarding-stage"
    # ),
    path(
        "get-offboarding-stage/<int:offboarding_id>/",
        exit_process.OffboardingPipelineStage.as_view(),
        name="get-offboarding-stage",
    ),
    path(
        "get-offboarding-employees-cbv",
        exit_process.OffboardingEmployeeList.as_view(),
        name="get-offboarding-employees-cbv",
    ),
    path(
        "get-offboarding-tab",
        exit_process.PipeLineTabView.as_view(),
        name="get-offboarding-tab",
    ),
    path(
        "create-offboarding-stage",
        exit_process.OffboardingStageFormView.as_view(),
        name="create-offboarding-stage",
    ),
    path(
        "create-offboarding-stage/<int:pk>/",
        exit_process.OffboardingStageFormView.as_view(),
        name="create-offboarding-stage",
    ),
    path(
        "update-stage-sequence/<int:pk>/",
        views.update_stage_order,
        name="update-stage-sequence",
    ),
    path(
        "offboarding-pipeline-nav/",
        exit_process.OffboardingPipelineNav.as_view(),
        name="offboarding-pipeline-nav",
    ),
    # path("add-employee", views.add_employee, name="add-employee"),
    path(
        "add-employee",
        exit_process.OffboardingStageAddEmployeeForm.as_view(),
        name="add-employee",
    ),
    path(
        "add-offboarding-employee",
        exit_process.OffboardingStageAddEmployeeForm.as_view(),
        name="add-offboarding-employee",
    ),
    path(
        "add-employee/<int:pk>/",
        exit_process.OffboardingStageAddEmployeeForm.as_view(),
        name="add-employee",
    ),
    path(
        "delete-offboarding-stage", views.delete_stage, name="delete-offboarding-stage"
    ),
    path(
        "offboarding-change-stage", views.change_stage, name="offboarding-change-stage"
    ),
    path(
        "change-offboarding-stage",
        views.change_offboarding_stage,
        name="change-offboarding-stage",
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
    # path("offboarding-add-task", views.add_task, name="offboarding-add-task"),
    path(
        "offboarding-add-task",
        exit_process.OffboardingTaskFormView.as_view(),
        name="offboarding-add-task",
    ),
    path(
        "offboarding-update-task/<int:pk>/",
        exit_process.OffboardingTaskFormView.as_view(),
        name="offboarding-update-task",
    ),
    path("update-task-status", views.update_task_status, name="update-task-status"),
    path("offboarding-assign-task", views.task_assign, name="offboarding-assign-task"),
    path(
        "delete-offboarding-employee",
        views.delete_employee,
        name="delete-offboarding-employee",
    ),
    path("delete-offboarding-task", views.delete_task, name="delete-offboarding-task"),
    # path(
    #     "offboarding-individual-view/<int:emp_id>/",
    #     views.offboarding_individual_view,
    #     name="offboarding-individual-view",
    # ),
    path(
        "offboarding-individual-view/<int:pk>/",
        exit_process.ExitProcessDetailView.as_view(),
        name="offboarding-individual-view",
    ),
    path(
        "offboarding-note-delete/<int:note_id>/",
        views.offboarding_note_delete,
        name="offboarding-note-delete",
    ),
    # path(
    #     "resignation-requests-view/",
    #     views.request_view,
    #     name="resignation-request-view",
    # ),
    path(
        "resignation-requests-view/",
        resignation.ResignationLettersView.as_view(),
        name="resignation-request-view",
    ),
    path(
        "list-resignation-requests/",
        resignation.ResignationListView.as_view(),
        name="list-resignation-request",
    ),
    # path(
    #     "tab-resignation-requests/<int:pk>",
    #     resignation_tab.ResignationTabView.as_view(),
    #     name="tab-resignation-requests",
    # ),
    path(
        "tab-resignation-requests/<int:pk>",
        check_feature_enabled("resignation_request", OffboardingGeneralSetting)(
            resignation_tab.ResignationTabView.as_view()
        ),
        name="tab-resignation-requests",
    ),
    path(
        "tab-resignation-requests-detail-view/<int:pk>",
        resignation_tab.ResignationTabDetailView.as_view(),
        name="tab-resignation-requests-detail-view",
    ),
    path(
        "nav-resignation-requests/",
        resignation.ResinationLettersNav.as_view(),
        name="nav-resignation-request",
    ),
    path(
        "resignation-requests-create/",
        resignation.ResignationLettersFormView.as_view(),
        name="resignation-requests-create",
    ),
    path(
        "resignation-requests-update/<int:pk>",
        resignation.ResignationLettersFormView.as_view(),
        name="resignation-request-update",
    ),
    path(
        "resignation-requests-detail-view/<int:pk>",
        resignation.ResignationLetterDetailView.as_view(),
        name="resignation-requests-detail-view",
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
    path(
        "list-dashboard-task-status/",
        exit_process.DashboardTaskListview.as_view(),
        name="list-dashboard-task-status",
    ),
]

if apps.is_installed("asset"):
    urlpatterns += [
        path(
            "dashboard-asset-table",
            views.dashboard_asset_table,
            name="dashboard-asset-table",
        ),
        path(
            "dashboard-asset-table-cbv",
            exit_process.DashboardNotReturndAsssets.as_view(),
            name="dashboard-asset-table-cbv",
        ),
    ]


if apps.is_installed("pms"):
    urlpatterns += [
        path(
            "dashboard-feedback-table",
            views.dashboard_feedback_table,
            name="dashboard-feedback-table",
        ),
        path(
            "dashboard-feedback-table-cbv/",
            exit_process.DashboardFeedbackView.as_view(),
            name="dashboard-feedback-table-cbv",
        ),
    ]
