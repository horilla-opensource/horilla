"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path

from base.views import object_delete, object_duplicate
from employee import not_in_out_dashboard, policies, views
from employee.forms import DisciplinaryActionForm
from employee.models import DisciplinaryAction, Employee, EmployeeTag
from horilla_documents.models import DocumentRequest

urlpatterns = [
    path("get-language-code/", views.get_language_code, name="get-language-code"),
    path("employee-profile/", views.employee_profile, name="employee-profile"),
    path(
        "employee-view/<int:obj_id>/",
        views.employee_view_individual,
        name="employee-view-individual",
        kwargs={"model": Employee},
    ),
    path("edit-profile", views.self_info_update, name="edit-profile"),
    path(
        "profile-edit-access/<int:emp_id>/",
        views.profile_edit_access,
        name="profile-edit-access",
    ),
    path(
        "update-profile-image/<int:obj_id>/",
        views.update_profile_image,
        name="update-profile-image",
    ),
    path(
        "update-own-profile-image",
        views.update_own_profile_image,
        name="update-own-profile-image",
    ),
    path(
        "remove-profile-image/<int:obj_id>/",
        views.remove_profile_image,
        name="remove-profile-image",
    ),
    path(
        "remove-own-profile-image",
        views.remove_own_profile_image,
        name="remove-own-profile-image",
    ),
    path(
        "employee-profile-bank-details",
        views.employee_profile_bank_details,
        name="employee-profile-bank-update",
    ),
    path("employee-view/", views.employee_view, name="employee-view"),
    path("employee-view-new", views.employee_view_new, name="employee-view-new"),
    path(
        "employee-view-update/<int:obj_id>/",
        views.employee_view_update,
        name="employee-view-update",
        kwargs={"model": Employee},
    ),
    path(
        "employee-create-personal-info",
        views.employee_create_update_personal_info,
        name="employee-create-personal-info",
    ),
    path(
        "employee-update-personal-info/<int:obj_id>/",
        views.employee_create_update_personal_info,
        name="employee-update-personal-info",
    ),
    path(
        "employee-create-work-info",
        views.employee_update_work_info,
        name="employee-create-work-info",
    ),
    path(
        "employee-update-work-info/<int:obj_id>/",
        views.employee_update_work_info,
        name="employee-update-work-info",
    ),
    path(
        "employee-create-bank-details",
        views.employee_update_bank_details,
        name="employee-create-bank-details",
    ),
    path(
        "employee-update-bank-details/<int:obj_id>/",
        views.employee_update_bank_details,
        name="employee-update-bank-details",
    ),
    path(
        "employee-filter-view", views.employee_filter_view, name="employee-filter-view"
    ),
    path("employee-view-card", views.employee_card, name="employee-view-card"),
    path("employee-view-list", views.employee_list, name="employee-view-list"),
    path("search-employee", views.employee_search, name="search-employee"),
    path(
        "employee-update/<int:obj_id>/", views.employee_update, name="employee-update"
    ),
    path(
        "employee-delete/<int:obj_id>/", views.employee_delete, name="employee-delete"
    ),
    path(
        "employee-bulk-update",
        views.view_employee_bulk_update,
        name="employee-bulk-update",
    ),
    path(
        "save-employee-bulk-update",
        views.save_employee_bulk_update,
        name="save-employee-bulk-update",
    ),
    path(
        "employee-account-block-unblock/<int:emp_id>/",
        views.employee_account_block_unblock,
        name="employee-account-block-unblock",
    ),
    path(
        "employee-bulk-delete", views.employee_bulk_delete, name="employee-bulk-delete"
    ),
    path(
        "employee-bulk-archive",
        views.employee_bulk_archive,
        name="employee-bulk-archive",
    ),
    path(
        "employee-archive/<int:obj_id>/",
        views.employee_archive,
        name="employee-archive",
    ),
    path(
        "replace-employee/<int:emp_id>/",
        views.replace_employee,
        name="replace-employee",
    ),
    path(
        "employee-user-group-assign-delete/<int:obj_id>/",
        views.employee_user_group_assign_delete,
        name="employee-user-group-assign-delete",
    ),
    path(
        "employee-work-info-view-create/<int:obj_id>/",
        views.employee_work_info_view_create,
        name="employee-work-info-view-create",
    ),
    path(
        "employee-bank-details-view-create/<int:obj_id>/",
        views.employee_bank_details_view_create,
        name="employee-bank-details-view-create",
    ),
    path(
        "employee-bank-details-view-update/<int:obj_id>/",
        views.employee_bank_details_view_update,
        name="employee-bank-details-view-update",
    ),
    path(
        "employee-work-info-view-update/<int:obj_id>/",
        views.employee_work_info_view_update,
        name="employee-work-info-view-update",
    ),
    path(
        "employee-work-information-delete/<int:obj_id>/",
        views.employee_work_information_delete,
        name="employee-work-information-delete",
    ),
    path("employee-import", views.employee_import, name="employee-import"),
    path("employee-export", views.employee_export, name="employee-export"),
    path("work-info-import", views.work_info_import, name="work-info-import"),
    path(
        "work-info-import-file",
        views.work_info_import_file,
        name="work-info-import-file",
    ),
    path("work-info-export", views.work_info_export, name="work-info-export"),
    path("get-birthday", views.get_employees_birthday, name="get-birthday"),
    path("dashboard", views.dashboard, name="dashboard"),
    path(
        "total-employees-count",
        views.total_employees_count,
        name="total-employees-count",
    ),
    path("joining-today-count", views.joining_today_count, name="joining-today-count"),
    path("joining-week-count", views.joining_week_count, name="joining-week-count"),
    path("dashboard-employee", views.dashboard_employee, name="dashboard-employee"),
    path(
        "dashboard-employee-gender",
        views.dashboard_employee_gender,
        name="dashboard-employee-gender",
    ),
    path(
        "dashboard-employee-department",
        views.dashboard_employee_department,
        name="dashboard-employee-department",
    ),
    path("employee-widget-filter", views.widget_filter, name="employee-widget-filter"),
    path("note-tab/<int:emp_id>", views.note_tab, name="note-tab"),
    path("add-employee-note/<int:emp_id>/", views.add_note, name="add-employee-note"),
    path("add-employee-note-post", views.add_note, name="add-employee-note-post"),
    path(
        "employee-note-update/<int:note_id>/",
        views.employee_note_update,
        name="employee-note-update",
    ),
    path(
        "add-more-files-employee/<int:note_id>/",
        views.add_more_employee_files,
        name="add-more-files-employee",
    ),
    path(
        "delete-employee-note-file/<int:note_file_id>/",
        views.delete_employee_note_file,
        name="delete-employee-note-file",
    ),
    path(
        "employee-note-delete/<int:note_id>/",
        views.employee_note_delete,
        name="employee-note-delete",
    ),
    path("shift-tab/<int:emp_id>", views.shift_tab, name="shift-tab"),
    path(
        "about-tab/<int:obj_id>",
        views.about_tab,
        name="about-tab",
        kwargs={"model": Employee},
    ),
    path("document-tab/<int:emp_id>", views.document_tab, name="document-tab"),
    path(
        "bonus-points-tab/<int:emp_id>", views.bonus_points_tab, name="bonus-points-tab"
    ),
    path(
        "add-bonus-points/<int:emp_id>", views.add_bonus_points, name="add-bonus-points"
    ),
    path("redeem-points/<int:emp_id>", views.redeem_points, name="redeem-points"),
    path("employee-select/", views.employee_select, name="employee-select"),
    path(
        "employee-select-filter/",
        views.employee_select_filter,
        name="employee-select-filter",
    ),
    path("not-in-yet/", not_in_out_dashboard.not_in_yet, name="not-in-yet"),
    path("not-out-yet/", not_in_out_dashboard.not_out_yet, name="not-out-yet"),
    path(
        "send-mail/<int:emp_id>/",
        not_in_out_dashboard.send_mail,
        name="send-mail-employee",
    ),
    path(
        "export-data-employee/<int:emp_id>/",
        not_in_out_dashboard.employee_data_export,
        name="export-data-employee",
    ),
    path(
        "employee-bulk-mail", not_in_out_dashboard.send_mail, name="employee-bulk-mail"
    ),
    path(
        "send-mail",
        not_in_out_dashboard.send_mail_to_employee,
        name="send-mail-to-employee",
    ),
    path(
        "get-template/<int:emp_id>/",
        not_in_out_dashboard.get_template,
        name="get-template-employee",
    ),
    path(
        "get-employee-mail-preview",
        not_in_out_dashboard.get_mail_preview,
        name="get-employee-mail-preview",
    ),
    path("view-policies/", policies.view_policies, name="view-policies"),
    path("search-policies", policies.search_policies, name="search-policies"),
    path("create-policy", policies.create_policy, name="create-policy"),
    path("view-policy", policies.view_policy, name="view-policy"),
    path(
        "add-attachment-policy", policies.add_attachment, name="add-attachment-policy"
    ),
    path(
        "remove-attachment-policy",
        policies.remove_attachment,
        name="remove-attachment-policy",
    ),
    path(
        "get-attachments-policy",
        policies.get_attachments,
        name="get-attachments-policy",
    ),
    path("file-upload/<int:id>", views.file_upload, name="file-upload"),
    path("view-file/<int:id>", views.view_file, name="view-file"),
    path("document-create/<int:emp_id>", views.document_create, name="document-create"),
    path(
        "update-document-title/<int:id>",
        views.update_document_title,
        name="update-document-title",
    ),
    path("document-approve/<int:id>", views.document_approve, name="document-approve"),
    path(
        "document-bulk-approve",
        views.document_bulk_approve,
        name="document-bulk-approve",
    ),
    path(
        "document-bulk-reject", views.document_bulk_reject, name="document-bulk-reject"
    ),
    path("document-reject/<int:id>", views.document_reject, name="document-reject"),
    path(
        "document-request-view/",
        views.document_request_view,
        name="document-request-view",
    ),
    path(
        "document-request-filter-view",
        views.document_filter_view,
        name="document-request-filter-view",
    ),
    path(
        "document-request-create",
        views.document_request_create,
        name="document-request-create",
    ),
    path(
        "document-request-update/<int:id>",
        views.document_request_update,
        name="document-request-update",
    ),
    path(
        "document-request-delete/<int:obj_id>/",
        object_delete,
        name="document-request-delete",
        kwargs={
            "model": DocumentRequest,
            "redirect_path": "/employee/document-request-view/",
        },
    ),
    path(
        "document-delete/<int:id>/",
        views.document_delete,
        name="document-delete",
    ),
    path("organisation-chart/", views.organisation_chart, name="organisation-chart"),
    path("delete-policies", policies.delete_policies, name="delete-policies"),
    path(
        "disciplinary-actions/",
        policies.disciplinary_actions,
        name="disciplinary-actions",
    ),
    path(
        "duplicate-disciplinary-actions/<int:obj_id>/",
        object_duplicate,
        name="duplicate-disciplinary-actions",
        kwargs={
            "model": DisciplinaryAction,
            "form": DisciplinaryActionForm,
            "template": "disciplinary_actions/form.html",
        },
    ),
    path("create-actions", policies.create_actions, name="create-actions"),
    path(
        "update-actions/<int:action_id>/",
        policies.update_actions,
        name="update-actions",
    ),
    path(
        "remove-employee-disciplinary-action/<int:action_id>/<int:emp_id>",
        policies.remove_employee_disciplinary_action,
        name="remove-employee-disciplinary-action",
    ),
    path(
        "delete-actions/<int:action_id>/",
        policies.delete_actions,
        name="delete-actions",
    ),
    path(
        "action-type-details",
        policies.action_type_details,
        name="action-type-details",
    ),
    path(
        "action-type-name",
        policies.action_type_name,
        name="action-type-name",
    ),
    path(
        "disciplinary-filter-view",
        policies.disciplinary_filter_view,
        name="disciplinary-filter-view",
    ),
    path(
        "search-disciplinary", policies.search_disciplinary, name="search-disciplinary"
    ),
    path(
        "encashment-condition-create",
        views.encashment_condition_create,
        name="encashment-condition-create",
    ),
    path("initial-prefix", views.initial_prefix, name="initial-prefix"),
    path(
        "get-first-last-badge-id",
        views.first_last_badge,
        name="get-first-last-badge-id",
    ),
    path(
        "employee-get-mail-log",
        views.employee_get_mail_log,
        name="employee-get-mail-log",
    ),
    path(
        "get-manage-in",
        views.get_manager_in,
        name="get-manager-in",
    ),
    path("get-job-positions", views.get_job_positions, name="get-job-positions"),
    path("get-job-roles", views.get_job_roles, name="get-job-roles"),
    path("employee-tag-view/", views.employee_tag_view, name="employee-tag-view"),
    path("employee-tag-create", views.employee_tag_create, name="employee-tag-create"),
    path(
        "employee-tag-update/<int:tag_id>",
        views.employee_tag_update,
        name="employee-tag-update",
    ),
    path(
        "employee-tag-delete/<int:obj_id>/",
        object_delete,
        name="employee-tag-delete",
        kwargs={"model": EmployeeTag, "HttpResponse": True},
    ),
]
