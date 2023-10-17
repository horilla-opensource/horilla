from django.urls import path
from . import views


urlpatterns = [
    path("objective-creation", views.objective_creation, name="objective-creation"),
    path(
        "objective-list-search",
        views.objective_list_search,
        name="objective-list-search",
    ),
    path("objective-list-view", views.objective_list_view, name="objective-list-view"),
    path(
        "objective-update/<int:obj_id>", views.objective_update, name="objective-update"
    ),
    path(
        "objective-delete/<int:obj_id>", views.objective_delete, name="objective-delete"
    ),
    path(
        "objective-archive/<int:id>", views.objective_archive, name="objective-archive"
    ),
    path(
        "objective-detailed-view/<int:emp_obj_id>",
        views.objective_detailed_view,
        name="objective-detailed-view",
    ),
    path(
        "objective-detailed-view-objective-status/<int:id>",
        views.objective_detailed_view_objective_status,
        name="objective-detailed-view-objective-status",
    ),
    path(
        "objective-detailed-view-key-result-status/<int:obj_id>/<int:kr_id>",
        views.objective_detailed_view_key_result_status,
        name="objective-detailed-view-key-result-status",
    ),
    path(
        "objective-detailed-view-current-value/<int:kr_id>",
        views.objective_detailed_view_current_value,
        name="objective-detailed-view-current-value",
    ),
    path(
        "objective-detailed-view-activity/<int:id>",
        views.objective_detailed_view_activity,
        name="objective-detailed-view-activity",
    ),
    path(
        "objective-detailed-view-comment/<int:id>",
        views.objective_detailed_view_comment,
        name="objective-detailed-view-comment",
    ),
    path(
        "key-result-view",
        views.key_result_view,
        name="key-result-view",
    ),
    path(
        "key-result-creation/<str:obj_id>/<str:obj_type>",
        views.key_result_creation,
        name="key-result-creation",
    ),
    path(
        "key-result-creation-htmx/<int:id>",
        views.key_result_creation_htmx,
        name="key-result-creation-htmx",
    ),
    path(
        "key-result-update/<int:id>", views.key_result_update, name="key-result-update"
    ),
    path("feedback-view", views.feedback_list_view, name="feedback-view"),
    path(
        "feedback-list-search", views.feedback_list_search, name="feedback-list-search"
    ),
    path("feedback-creation", views.feedback_creation, name="feedback-creation"),
    path(
        "feedback-creation-ajax",
        views.feedback_creation_ajax,
        name="feedback-creation-ajax",
    ),
    path("feedback-update/<int:id>", views.feedback_update, name="feedback-update"),
    path("feedback-delete/<int:id>", views.feedback_delete, name="feedback-delete"),
    path("feedback-archive/<int:id>", views.feedback_archive, name="feedback-archive"),
    path(
        "feedback-answer-get/<int:id>",
        views.feedback_answer_get,
        name="feedback-answer-get",
    ),
    path(
        "feedback-answer-post/<int:id>",
        views.feedback_answer_post,
        name="feedback-answer-post",
    ),
    path(
        "feedback-answer-view/<int:id>",
        views.feedback_answer_view,
        name="feedback-answer-view",
    ),
    path(
        "feedback-detailed-view/<int:id>",
        views.feedback_detailed_view,
        name="feedback-detailed-view",
    ),
    path(
        "feedback-detailed-view-answer/<int:id>/<int:emp_id>",
        views.feedback_detailed_view_answer,
        name="feedback-detailed-view-answer",
    ),
    path(
        "feedback-detailed-view-status/<int:id>",
        views.feedback_detailed_view_status,
        name="feedback-detailed-view-status",
    ),
    path("feedback-status", views.feedback_status, name="feedback-status"),
    path(
        "question-creation/<int:id>", views.question_creation, name="question-creation"
    ),
    path("question-view/<int:id>", views.question_view, name="question-view"),
    path(
        "question-update/<int:temp_id>/<int:q_id>",
        views.question_update,
        name="question-update",
    ),
    path("question-delete/<int:id>", views.question_delete, name="question-delete"),
    path(
        "question-template-creation",
        views.question_template_creation,
        name="question-template-creation",
    ),
    path(
        "question-template-view",
        views.question_template_view,
        name="question-template-view",
    ),
    path(
        "question-template-detailed-view/<int:template_id>",
        views.question_template_detailed_view,
        name="question-template-detailed-view",
    ),
    path(
        "question-template-update/<int:template_id>/",
        views.question_template_update,
        name="question-template-update",
    ),
    path(
        "question-template-delete/<int:template_id>",
        views.question_template_delete,
        name="question-template-delete",
    ),
    path("period-create", views.period_create, name="period-create"),
    path("period-view", views.period_view, name="period-view"),
    path("period-delete/<int:period_id>", views.period_delete, name="period-delete"),
    path("period-update/<int:period_id>", views.period_update, name="period-update"),
    path("period-change", views.period_change, name="period-change"),
    path("dashboard-view", views.dashboard_view, name="dashboard-view"),
    path(
        "dashboard-objective-status",
        views.dashboard_objective_status,
        name="dashboard-objective-status",
    ),
    path(
        "dashbord-key-result-status",
        views.dashboard_key_result_status,
        name="dashbord-key-result-status",
    ),
    path(
        "dashboard-feedback-status",
        views.dashboard_feedback_status,
        name="dashboard-feedback-status",
    ),
    path(
        "create-period",
        views.create_period,
        name="create-period",
    ),
]
