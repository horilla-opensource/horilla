"""
urls.py

This module is used to map url path with view methods.
"""
from django.urls import path
from employee import views
from employee.models import Employee

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
        views.employee_update_personal_info,
        name="employee-create-personal-info",
    ),
    path(
        "employee-update-personal-info/<int:obj_id>/",
        views.employee_update_personal_info,
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
    path("work-info-export", views.work_info_export, name="work-info-export"),
    path("get-birthday", views.get_employees_birthday, name="get-birthday"),
    path("dashboard", views.dashboard, name="dashboard"),
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
    path(
        "dashboard-employee-count",
        views.dashboard_employee_tiles,
        name="dashboard-employee-count",
    ),
    path("employee-widget-filter", views.widget_filter, name="employee-widget-filter"),
    path("asset-tab/<int:emp_id>", views.asset_tab, name="asset-tab"),
    path(
        "profile-asset-tab/<int:emp_id>",
        views.profile_asset_tab,
        name="profile-asset-tab",
    ),
    path(
        "profile-attendance-tab",
        views.profile_attendance_tab,
        name="profile-attendance-tab",
    ),
    path(
        "asset-request-tab/<int:emp_id>",
        views.asset_request_tab,
        name="asset-request-tab",
    ),
    path("performance-tab/<int:emp_id>", views.performance_tab, name="performance-tab"),
    path("attendance-tab/<int:emp_id>", views.attendance_tab, name="attendance-tab"),
    path("shift-tab/<int:emp_id>", views.shift_tab, name="shift-tab"),
    path("contract-tab/<int:obj_id>", views.contract_tab, name="contract-tab",kwargs={'model':Employee}),
    path("employee-select/", views.employee_select, name="employee-select"),
    path(
        "employee-select-filter/",
        views.employee_select_filter,
        name="employee-select-filter",
    ),
]
