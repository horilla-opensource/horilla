from django.urls import path

from base.views import object_delete
from horilla_audit.methods import history_tracking
from pms import cbvs

from . import models, views

urlpatterns = [
    # objectives
    path("objective-list-view/", views.objective_list_view, name="objective-list-view"),
    path("objective-creation/", views.objective_creation, name="objective-creation"),
    path(
        "objective-update/<int:obj_id>", views.objective_update, name="objective-update"
    ),
    path("add-assignees/<int:obj_id>", views.add_assignees, name="add-assignees"),
    # key results
    path("view-key-result/", views.view_key_result, name="view-key-result"),
    path("filter-key-result/", views.filter_key_result, name="filter-key-result"),
    path("create-key-result/", views.kr_create_or_update, name="create-key-result"),
    path(
        "update-key-result/<int:kr_id>",
        views.kr_create_or_update,
        name="update-key-result",
    ),
    path(
        "delete-key-result/<int:obj_id>/",
        object_delete,
        name="delete-key-result",
        kwargs={"model": models.KeyResult, "redirect_path": "/pms/filter-key-result/"},
    ),
    path("key-result-creation", views.key_result_create, name="key-result-creation"),
    path(
        "key-reult-remove/<int:obj_id>/<int:kr_id>",
        views.key_result_remove,
        name="key-result-remove",
    ),
    path(
        "objective-list-search",
        views.objective_list_search,
        name="objective-list-search",
    ),
    path(
        "objective-dashboard-view",
        views.objective_dashboard_view,
        name="objective-dashboard-view",
    ),
    path(
        "objective-delete/<int:obj_id>", views.objective_delete, name="objective-delete"
    ),
    path(
        "objective-archive/<int:id>", views.objective_archive, name="objective-archive"
    ),
    path(
        "objective-detailed-view/<int:obj_id>",
        views.objective_detailed_view,
        name="objective-detailed-view",
        kwargs={"model": models.EmployeeObjective},
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
        "emp-objective-search/<int:obj_id>",
        views.emp_objective_search,
        name="emp-objective-search",
    ),
    path(
        "objective-manager-remove/<int:obj_id>/<int:manager_id>",
        views.objective_manager_remove,
        name="objective-manager-remove",
    ),
    path(
        "assignees-remove/<int:obj_id>/<int:emp_id>",
        views.assignees_remove,
        name="assignees-remove",
    ),
    path(
        "objective-detailed-view-comment/<int:id>",
        views.objective_detailed_view_comment,
        name="objective-detailed-view-comment",
    ),
    path(
        "kr-table-view/<int:emp_objective_id>",
        views.kr_table_view,
        name="kr-table-view",
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
    path("feedback-view/", views.feedback_list_view, name="feedback-view"),
    path(
        "feedback-list-search", views.feedback_list_search, name="feedback-list-search"
    ),
    path("feedback-creation", views.feedback_creation, name="feedback-creation"),
    path(
        "bulk-feedback-create",
        cbvs.BulkFeedbackFormView.as_view(),
        name="bulk-feedback-create",
    ),
    path("feedback-update/<int:id>", views.feedback_update, name="feedback-update"),
    path("feedback-delete/<int:id>", views.feedback_delete, name="feedback-delete"),
    path("feedback-archive/<int:id>", views.feedback_archive, name="feedback-archive"),
    path("get-collegues", views.get_collegues, name="get-collegues"),
    path(
        "share-feedback/<int:pk>/",
        cbvs.FeedbackEmployeeFormView.as_view(),
        name="share-feedback",
    ),
    path(
        "feedback-answer-get/<int:id>",
        views.feedback_answer_get,
        name="feedback-answer-get",
        kwargs={"model": models.Feedback},
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
        kwargs={"model": models.Feedback},
    ),
    path(
        "feedback-detailed-view/<int:id>",
        views.feedback_detailed_view,
        name="feedback-detailed-view",
        kwargs={"model": models.Feedback},
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
    path(
        "get-feedback-overview/<int:obj_id>",
        views.get_feedback_overview,
        name="get-feedback-overview",
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
        "question-template-view/",
        views.question_template_view,
        name="question-template-view",
    ),
    path(
        "question-template-hx-view",
        views.question_template_hx_view,
        name="question-template-hx-view",
    ),
    path(
        "question-template-detailed-view/<int:template_id>",
        views.question_template_detailed_view,
        name="question-template-detailed-view",
        kwargs={"model": models.QuestionTemplate},
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
    path("period-hx-view", views.period_hx_view, name="period-hx-view"),
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
    path(
        "objective-bulk-archive",
        views.objective_bulk_archive,
        name="objective-bulk-archive",
    ),
    path(
        "objective-bulk-delete",
        views.objective_bulk_delete,
        name="objective-bulk-delete",
    ),
    path(
        "feedback-bulk-archive",
        views.feedback_bulk_archive,
        name="feedback-bulk-archive",
    ),
    path(
        "feedback-bulk-delete",
        views.feedback_bulk_delete,
        name="feedback-bulk-delete",
    ),
    path(
        "objective-select",
        views.objective_select,
        name="objective-select",
    ),
    path(
        "objective-select-filter",
        views.objective_select_filter,
        name="objective-select-filter",
    ),
    path(
        "add-anonymous-feedback",
        views.anonymous_feedback_add,
        name="add-anonymous-feedback",
    ),
    path(
        "edit-anonymous-feedback/<int:obj_id>/",
        views.edit_anonymous_feedback,
        name="edit-anonymous-feedback",
    ),
    path(
        "archive-anonymous-feedback/<int:obj_id>/",
        views.archive_anonymous_feedback,
        name="archive-anonymous-feedback",
    ),
    path(
        "delete-anonymous-feedback/<int:obj_id>/",
        views.delete_anonymous_feedback,
        name="delete-anonymous-feedback",
    ),
    path(
        "single-anonymous-feedback-view/<int:obj_id>/",
        views.view_single_anonymous_feedback,
        name="single-anonymous-feedback-view",
    ),
    path(
        "view-employee-objective/<int:emp_obj_id>/",
        views.view_employee_objective,
        name="view-employee-objective",
    ),
    path(
        "create-employee-objective/",
        views.create_employee_objective,
        name="create-employee-objective",
    ),
    path(
        "get-objective-keyresult/",
        views.get_objective_keyresults,
        name="get-objective-keyresult",
    ),
    path(
        "update-employee-objective/<int:emp_obj_id>/",
        views.update_employee_objective,
        name="update-employee-objective",
    ),
    path(
        "archive-employee-objective/<int:emp_obj_id>/",
        views.archive_employee_objective,
        name="archive-employee-objective",
    ),
    path(
        "delete-employee-objective/<int:emp_obj_id>/",
        views.delete_employee_objective,
        name="delete-employee-objective",
    ),
    path(
        "change-employee-objective-status",
        views.change_employee_objective_status,
        name="change-employee-objective-status",
    ),
    path(
        "employee-key-result-creation/<int:emp_obj_id>",
        views.employee_keyresult_creation,
        name="employee-key-result-creation",
    ),
    path(
        "employee-key-result-update/<int:kr_id>",
        views.employee_keyresult_update,
        name="employee-key-result-update",
    ),
    path(
        "delete-employee-keyresult/<int:kr_id>",
        views.delete_employee_keyresult,
        name="delete-employee-keyresult",
    ),
    path(
        "employee-keyresult-update-status/<int:kr_id>",
        views.employee_keyresult_update_status,
        name="employee-keyresult-update-status",
    ),
    path(
        "key-result-current-value-update",
        views.key_result_current_value_update,
        name="key-result-current-value-update",
    ),
    path("get-keyresult-data", views.get_keyresult_data, name="get-keyresult-data"),
    path(
        "view-meetings/",
        views.view_meetings,
        name="view-meetings",
    ),
    path(
        "create-meeting",
        views.create_meetings,
        name="create-meeting",
    ),
    path(
        "meetings-delete/<int:obj_id>/",
        object_delete,
        name="meetings-delete",
        kwargs={"model": models.Meetings, "HttpResponse": True},
    ),
    path(
        "archive-meeting/<int:obj_id>/",
        views.archive_meetings,
        name="archive-meeting",
    ),
    path(
        "filter-meeting",
        views.filter_meetings,
        name="filter-meeting",
    ),
    path(
        "add-response/<int:obj_id>/",
        views.add_response,
        name="add-response",
    ),
    path(
        "meeting-answer-get/<int:id>",
        views.meeting_answer_get,
        name="meeting-answer-get",
    ),
    path(
        "meeting-answer-post/<int:id>",
        views.meeting_answer_post,
        name="meeting-answer-post",
    ),
    path(
        "meeting-answer-view/<int:id>/<int:emp_id>",
        views.meeting_answer_view,
        name="meeting-answer-view",
    ),
    path(
        "meeting-question-template-view/<int:meet_id>",
        views.meeting_question_template_view,
        name="meeting-question-template-view",
    ),
    path(
        "meeting-single-view/<int:id>",
        views.meeting_single_view,
        name="meeting-single-view",
    ),
    path(
        "meeting-manager-remove/<int:meet_id>/<int:manager_id>",
        views.meeting_manager_remove,
        name="meeting-manager-remove",
    ),
    path(
        "meeting-employee-remove/<int:meet_id>/<int:employee_id>",
        views.meeting_employee_remove,
        name="meeting-employee-remove",
    ),
    path("performance-tab/<int:emp_id>", views.performance_tab, name="performance-tab"),
    path(
        "dashboard-feedback-answer",
        views.dashboard_feedback_answer,
        name="dashboard-feedback-answer",
    ),
    # ===========bonus point setting============
    path(
        "bonus-point-setting/",
        cbvs.BonusPointSettingSectionView.as_view(),
        name="bonus-point-setting",
    ),
    path(
        "bonus-point-setting-nav",
        cbvs.BonusPointSettingNavView.as_view(),
        name="bonus-point-setting-nav",
    ),
    path(
        "create-bonus-point-setting",
        cbvs.BonusPointSettingFormView.as_view(),
        name="create-bonus-point-setting",
    ),
    path(
        "update-bonus-point-setting/<int:pk>/",
        cbvs.BonusPointSettingFormView.as_view(),
        name="update-bonus-point-setting",
    ),
    path(
        "delete-bonus-point-setting/<int:pk>/",
        views.delete_bonus_point_setting,
        name="delete-bonus-point-setting",
    ),
    path(
        "bonus-point-setting-list-view",
        cbvs.BonusPointSettingListView.as_view(),
        name="bonus-point-setting-list-view",
    ),
    path(
        "bonus-setting-form-values",
        views.bonus_setting_form_values,
        name="bonus-setting-form-values",
    ),
    path(
        "update-isactive-bonuspoint-setting/<int:obj_id>",
        views.update_isactive_bonuspoint_setting,
        name="update-isactive-bonuspoint-setting",
    ),
    # ===========Employee bonus point============
    path(
        "employee-bonus-point",
        cbvs.EmployeeBonusPointSectionView.as_view(),
        name="employee-bonus-point",
    ),
    path(
        "employee-bonus-point-nav",
        cbvs.EmployeeBonusPointNavView.as_view(),
        name="employee-bonus-point-nav",
    ),
    path(
        "create-employee-bonus-point",
        cbvs.EmployeeBonusPointFormView.as_view(),
        name="create-employee-bonus-point",
    ),
    path(
        "employee-bonus-point-list-view",
        cbvs.EmployeeBonusPointListView.as_view(),
        name="employee-bonus-point-list-view",
    ),
    path(
        "update-employee-bonus-point/<int:pk>/",
        cbvs.EmployeeBonusPointFormView.as_view(),
        name="update-employee-bonus-point",
    ),
    path(
        "delete-employee-bonus-point/<int:pk>/",
        views.delete_employee_bonus_point,
        name="delete-employee-bonus-point",
    ),
    path(
        "history-tracking/<int:obj_id>/",
        history_tracking,
        name="history-tracking",
        kwargs={"model": models.Meetings, "decorators": ["login_required"]},
    ),
]
