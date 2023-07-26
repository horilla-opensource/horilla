"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path
from recruitment import views

urlpatterns = [
    path("recruitment-create", views.recruitment, name="recruitment-create"),
    path("recruitment-view", views.recruitment_view, name="recruitment-view"),
    path("recruitment-search", views.recruitment_search, name="recruitment-search"),
    path(
        "recruitment-update/<int:rec_id>/",
        views.recruitment_update,
        name="recruitment-update",
    ),
    path(
        "recruitment-update-pipeline/<int:rec_id>/",
        views.recruitment_update_pipeline,
        name="recruitment-update-pipeline",
    ),
    path(
        "recruitment-update-delete/<int:rec_id>/",
        views.recruitment_delete_pipeline,
        name="recruitment-delete-pipeline",
    ),
    path(
        "recruitment-delete/<int:rec_id>/",
        views.recruitment_delete,
        name="recruitment-delete",
    ),
    path("pipeline", views.recruitment_pipeline, name="pipeline"),
    path("pipeline-card", views.recruitment_pipeline_card, name="pipeline-card"),
    path(
        "pipeline-search-candidate",
        views.pipeline_candidate_search,
        name="pipeline-search-candidate",
    ),
    path(
        "candidate-schedule-date-update",
        views.candidate_schedule_date_update,
        name="candidate-schedule-date-update",
    ),
    path("stage-create", views.stage, name="rec-stage-create"),
    path("stage-view", views.stage_view, name="rec-stage-view"),
    path("stage-search", views.stage_search, name="stage-search"),
    path("stage-update/<int:stage_id>/", views.stage_update, name="rec-stage-update"),
    path(
        "stage-update-pipeline/<int:stage_id>/",
        views.stage_update_pipeline,
        name="stage-update-pipeline",
    ),
    path(
        "stage-name-update/<int:stage_id>/", views.stage_name_update, name="stage-name-update"
    ),
    path("stage-delete/<int:stage_id>/", views.stage_delete, name="rec-stage-delete"),
    path(
        "remove-stage-manager/<int:mid>/<int:sid>/",
        views.remove_stage_manager,
        name="rec-remove-stage-manager",
    ),
    path(
        "remove-recruitment-manager/<int:mid>/<int:rid>/",
        views.remove_recruitment_manager,
        name="remove-recruitment-manager",
    ),
    path("candidate-create", views.candidate, name="candidate-create"),
    path(
        "recruitment-stage-get/<int:rec_id>/",
        views.recruitment_stage_get,
        name="recruitment-stage-get",
    ),
    path(
        "candidate-stage-update/<int:cand_id>/",
        views.candidate_stage_update,
        name="candidate-stage-update",
    ),
    path("view-note/<int:cand_id>/", views.view_note, name="view-note"),
    path("note-update/<int:note_id>/", views.note_update, name="note-update"),
    path("note-delete/<int:note_id>/", views.note_delete, name="note-delete"),
    path(
        "stage-note-delete/<int:note_id>/",
        views.candidate_remark_delete,
        name="stage-note-delete",
    ),
    path("add-note/<int:cand_id>/", views.add_note, name="add-note"),
    path("add-note", views.add_note, name="add-note-post"),
    path("send-mail/<int:cand_id>/", views.form_send_mail, name="send-mail"),
    path("candidate-view", views.candidate_view, name="candidate-view"),
    path(
        "candidate-filter-view",
        views.candidate_filter_view,
        name="candidate-filter-view",
    ),
    path("search-candidate", views.candidate_search, name="search-candidate"),
    path("candidate-view-list", views.candidate_view_list, name="candidate-view-list"),
    path("candidate-view-card", views.candidate_view_card, name="candidate-view-card"),
    path(
        "candidate-view/<int:cand_id>/",
        views.candidate_view_individual,
        name="candidate-view-individual",
    ),
    path(
        "candidate-update/<int:cand_id>/",
        views.candidate_update,
        name="rec-candidate-update",
    ),
    path(
        "candidate-delete/<int:cand_id>/",
        views.candidate_delete,
        name="rec-candidate-delete",
    ),
    path(
        "candidate-archive/<int:cand_id>/",
        views.candidate_archive,
        name="rec-candidate-archive",
    ),
    path(
        "candidate-bulk-delete",
        views.candidate_bulk_delete,
        name="candidate-bulk-delete",
    ),
    path(
        "candidate-bulk-archive",
        views.candidate_bulk_archive,
        name="candidate-bulk-archive",
    ),
    path(
        "candidate-history/<int:cand_id>/", views.candidate_history, name="candidate-history"
    ),
    path("application-form", views.application_form, name="application-form"),
    path(
        "send-acknowledgement", views.send_acknowledgement, name="send-acknowledgement"
    ),
    path("dashboard", views.dashboard, name="recruitment-dashboard"),
    path("dashboard-pipeline", views.dashboard_pipeline, name="recruitment-pipeline"),
    path("get-open-positions", views.get_open_position, name="get-open-position"),
    path("candidate-sequence-update", views.candidate_sequence_update, name="candidate-sequence-update"),
]
