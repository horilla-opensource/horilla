from django.urls import path
from base import views
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftSchedule,
    EmployeeType,
    JobPosition,
    JobRole,
    RotatingShift,
    RotatingWorkType,
    WorkType,
)
from django.contrib.auth.models import Group

urlpatterns = [
    path("", views.home, name="home-page"),
    path("login/", views.login_user, name="login"),
    path("forgot-password", views.forgot_password, name="forgot-password"),
    path("reset-password/<uuid>/", views.reset_password, name="reset-password"),
    path("change-password", views.change_password, name="change-password"),
    path("logout", views.logout_user, name="logout"),
    path("settings", views.common_settings, name="settings"),
    path(
        "settings/user-group-create/", views.user_group_table, name="user-group-create"
    ),
    path("user-group-view", views.user_group, name="user-group-view"),
    path(
        "settings/user-group-update/<int:id>/",
        views.user_group_update,
        name="user-group-update",
        kwargs={"model": Group},
    ),
    path(
        "user-group-delete/<int:id>/",
        views.object_delete,
        name="user-group-delete",
        kwargs={"model": Group, "redirect": "user-group-view"},
    ),
    path(
        "group-permission-remove/<int:pid>/<int:gid>/",
        views.user_group_permission_remove,
        name="group-permission-remove",
    ),
    path(
        "user-group-assign-view", views.group_assign_view, name="user-group-assign-view"
    ),
    path("settings/user-group-assign/", views.group_assign, name="user-group-assign"),
    path(
        "group-remove-user/<int:uid>/<int:gid>/",
        views.group_remove_user,
        name="group-remove-user",
    ),
    path(
        "settings/employee-permission-assign/",
        views.employee_permission_assign,
        name="employee-permission-assign",
    ),
    path(
        "employee-permission-search",
        views.employee_permission_search,
        name="permission-search",
    ),
    path(
        "update-user-permission",
        views.update_permission,
        name="update-user-permission",
    ),
    path(
        "update-group-permission",
        views.update_group_permission,
        name="update-group-permission",
    ),
    path(
        "permission-table",
        views.permission_table,
        name="permission-table",
    ),
    path("settings/company-create/", views.company_create, name="company-create"),
    path('company-view', views.company_view,name='company-view'),
    path(
        "settings/company-update/<int:id>/",
        views.company_update,
        name="company-update",
        kwargs={"model": Company},
    ),
    path(
        "company-delete/<int:id>/",
        views.object_delete,
        name="company-delete",
        kwargs={"model": Company, "redirect": "/company-view"},
    ),
    path("settings/department-view/", views.department_view, name="department-view"),
    path("settings/department-creation/", views.department_create, name="department-creation"),
    path(
        "settings/department-update/<int:id>/",
        views.department_update,
        name="department-update",
        kwargs={"model": Department},
    ),
    path(
        "department-delete/<int:id>/",
        views.object_delete,
        name="department-delete",
        kwargs={"model": Department, "redirect": "/settings/department-view"},
    ),
    path(
        "settings/job-position-creation/",
        views.job_position_creation,
        name="job-position-creation",
    ),
    path(
        "settings/job-position-view/",
        views.job_position,
        name="job-position-view",
    ),
    path(
        "settings/job-position-update/<int:id>/",
        views.job_position_update,
        name="job-position-update",
        kwargs={"model": JobPosition},
    ),
    path(
        "job-position-delete/<int:id>/",
        views.object_delete,
        name="job-position-delete",
        kwargs={"model": JobPosition, "redirect": "/settings/job-position-view"},
    ),
    path("settings/job-role-create/", views.job_role_create, name="job-role-create"),
    path("settings/job-role-view/", views.job_role_view, name="job-role-view"),
    path(
        "settings/job-role-update/<int:id>/",
        views.job_role_update,
        name="job-role-update",
        kwargs={"model": JobRole},
    ),
    path(
        "job-role-delete/<int:id>/",
        views.object_delete,
        name="job-role-delete",
        kwargs={"model": JobRole, "redirect": "/settings/job-role-view"},
    ),
    path("settings/work-type-view/", views.work_type_view, name="work-type-view"),
    path("settings/work-type-create/", views.work_type_create, name="work-type-create"),
    path(
        "settings/work-type-update/<int:id>/",
        views.work_type_update,
        name="work-type-update",
        kwargs={"model": WorkType},
    ),
    path(
        "work-type-delete/<int:id>/",
        views.object_delete,
        name="work-type-delete",
        kwargs={"model": WorkType, "redirect": "/settings/work-type-view"},
    ),
    path(
        "settings/rotating-work-type-create/",
        views.rotating_work_type_create,
        name="rotating-work-type-create",
    ),
    path(
        "settings/rotating-work-type-view/",
        views.rotating_work_type_view,
        name="rotating-work-type-view",
    ),
    path(
        "settings/rotating-work-type-update/<int:id>/",
        views.rotating_work_type_update,
        name="rotating-work-type-update",
        kwargs={"model": RotatingWorkType},
    ),
    path(
        "rotating-work-type-delete/<int:id>/",
        views.object_delete,
        name="rotating-work-type-delete",
        kwargs={
            "model": RotatingWorkType,
            "redirect": "/settings/rotating-work-type-view",
        },
    ),
    path(
        "employee/rotating-work-type-assign",
        views.rotating_work_type_assign,
        name="rotating-work-type-assign",
    ),
    path(
        "rotating-work-type-assign-add",
        views.rotating_work_type_assign_add,
        name="rotating-work-type-assign-add",
    ),
    path(
        "rotating-work-type-assign-view",
        views.rotating_work_type_assign_view,
        name="rotating-work-type-assign-view",
    ),
    path(
        "rotating-work-type-assign-export",
        views.rotating_work_type_assign_export,
        name="rotating-work-type-assign-export",
    ),
    path(
        "settings/rotating-work-type-assign-update/<int:id>/",
        views.rotating_work_type_assign_update,
        name="rotating-work-type-assign-update",
    ),
    path(
        "rotating-work-type-assign-archive/<int:id>/",
        views.rotating_work_type_assign_archive,
        name="rotating-work-type-assign-archive",
    ),
    path(
        "rotating-work-type-assign-bulk-archive",
        views.rotating_work_type_assign_bulk_archive,
        name="rotating-shift-work-type-bulk-archive",
    ),
    path(
        "rotating-work-type-assign-bulk-delete",
        views.rotating_work_type_assign_bulk_delete,
        name="rotating-shift-work-type-bulk-delete",
    ),
    path(
        "rotating-work-type-assign-delete/<int:id>/",
        views.rotating_work_type_assign_delete,
        name="rotating-work-type-assign-delete",
    ),
    path(
        "settings/employee-type-view/",
        views.employee_type_view,
        name="employee-type-view",
    ),
    path(
        "settings/employee-type-create/",
        views.employee_type_create,
        name="employee-type-create",
    ),
    path(
        "settings/employee-type-update/<int:id>/",
        views.employee_type_update,
        name="employee-type-update",
        kwargs={"model": EmployeeType},
    ),
    path(
        "employee-type-delete/<int:id>/",
        views.object_delete,
        name="employee-type-delete",
        kwargs={
            "model": EmployeeType,
            "redirect": "/settings/employee-type-view",
        },
    ),
    path(
        "settings/employee-shift-view/",
        views.employee_shift_view,
        name="employee-shift-view",
    ),
    path(
        "settings/employee-shift-create/",
        views.employee_shift_create,
        name="employee-shift-create",
    ),
    path(
        "settings/employee-shift-update/<int:id>/",
        views.employee_shift_update,
        name="employee-shift-update",
        kwargs={"model": EmployeeShift},
    ),
    path(
        "employee-shift-delete/<int:id>/",
        views.object_delete,
        name="employee-shift-delete",
        kwargs={
            "model": EmployeeShift,
            "redirect": "/settings/employee-shift-view",
        },
    ),
    path(
        "settings/employee-shift-schedule-view/",
        views.employee_shift_schedule_view,
        name="employee-shift-schedule-view",
    ),
    path(
        "settings/employee-shift-schedule-create/",
        views.employee_shift_schedule_create,
        name="employee-shift-schedule-create",
    ),
    path(
        "settings/employee-shift-schedule-update/<int:id>/",
        views.employee_shift_schedule_update,
        name="employee-shift-schedule-update",
        kwargs={"model": EmployeeShiftSchedule},
    ),
    path(
        "employee-shift-schedule-delete/<int:id>/",
        views.object_delete,
        name="employee-shift-schedule-delete",
        kwargs={
            "model": EmployeeShiftSchedule,
            "redirect": "/settings/employee-shift-schedule-view",
        },
    ),
    path(
        "settings/rotating-shift-create/",
        views.rotating_shift_create,
        name="rotating-shift-create",
    ),
    path(
        "settings/rotating-shift-view/",
        views.rotating_shift_view,
        name="rotating-shift-view",
    ),
    path(
        "settings/rotating-shift-update/<int:id>/",
        views.rotating_shift_update,
        name="rotating-shift-update",
        kwargs={"model": RotatingShift},
    ),
    path(
        "rotating-shift-delete/<int:id>/",
        views.object_delete,
        name="rotating-shift-delete",
        kwargs={
            "model": RotatingShift,
            "redirect": "/settings/rotating-shift-view",
        },
    ),
    path(
        "employee/rotating-shift-assign",
        views.rotating_shift_assign,
        name="rotating-shift-assign",
    ),
    path(
        "rotating-shift-assign-add",
        views.rotating_shift_assign_add,
        name="rotating-shift-assign-add",
    ),
    path(
        "rotating-shift-assign-view",
        views.rotating_shift_assign_view,
        name="rotating-shift-assign-view",
    ),
    path(
        "rotating-shift-assign-info-export",
        views.rotating_shift_assign_export,
        name="rotating-shift-assign-info-export",
    ),
    path(
        "settings/rotating-shift-assign-update/<int:id>/",
        views.rotating_shift_assign_update,
        name="rotating-shift-assign-update",
    ),
    path(
        "rotating-shift-assign-archive/<int:id>/",
        views.rotating_shift_assign_archive,
        name="rotating-shift-assign-archive",
    ),
    path(
        "rotating-shift-assign-bulk-archive",
        views.rotating_shift_assign_bulk_archive,
        name="rotating-shift-assign-bulk-archive",
    ),
    path(
        "rotating-shift-assign-bulk-delete",
        views.rotating_shift_assign_bulk_delete,
        name="rotating-shift-assign-bulk-delete",
    ),
    path(
        "rotating-shift-assign-delete/<int:id>/",
        views.rotating_shift_assign_delete,
        name="rotating-shift-assign-delete",
    ),
    path("work-type-request", views.work_type_request, name="work-type-request"),
    path(
        "employee/work-type-request-view",
        views.work_type_request_view,
        name="work-type-request-view",
    ),
    path(
        "work-type-request-info-export",
        views.work_type_request_export,
        name="work-type-request-info-export",
    ),
    path(
        "work-type-request-search",
        views.work_type_request_search,
        name="work-type-request-search",
    ),
    path(
        "work-type-request-cancel/<int:id>/",
        views.work_type_request_cancel,
        name="work-type-request-cancel",
    ),
    path(
        "work-type-request-bulk-cancel",
        views.work_type_request_bulk_cancel,
        name="work-type-request-bulk-cancel",
    ),
    path(
        "work-type-request-approve/<int:id>/",
        views.work_type_request_approve,
        name="work-type-request-approve",
    ),
    path(
        "work-type-request-bulk-approve",
        views.work_type_request_bulk_approve,
        name="work-type-request-bulk-approve",
    ),
    path(
        "work-type-request-update/<int:work_type_request_id>/",
        views.work_type_request_update,
        name="work-type-request-update",
    ),
    path(
        "work-type-request-delete/<int:id>/",
        views.work_type_request_delete,
        name="work-type-request-delete",
    ),
    path(
        "work-type-request-single-view/<int:work_type_request_id>/",
        views.work_type_request_single_view,
        name="work-type-request-single-view",
    ),
    path(
        "work-type-request-bulk-delete",
        views.work_type_request_bulk_delete,
        name="work-type-request-bulk-delete",
    ),
    path("shift-request", views.shift_request, name="shift-request"),
    path(
        "employee/shift-request-view",
        views.shift_request_view,
        name="shift-request-view",
    ),
    path(
        "shift-request-info-export",
        views.shift_request_export,
        name="shift-request-info-export",
    ),
    path(
        "shift-request-search", views.shift_request_search, name="shift-request-search"
    ),
    path(
        "shift-request-details/<int:id>/",
        views.shift_request_details,
        name="shift-request-details",
    ),
    path(
        "shift-request-update/<int:shift_request_id>/",
        views.shift_request_update,
        name="shift-request-update",
    ),
    path(
        "shift-request-cancel/<int:id>/",
        views.shift_request_cancel,
        name="shift-request-cancel",
    ),
    path(
        "shift-request-bulk-cancel",
        views.shift_request_bulk_cancel,
        name="shift-request-bulk-cancel",
    ),
    path(
        "shift-request-approve/<int:id>/",
        views.shift_request_approve,
        name="shift-request-approve",
    ),
    path(
        "shift-request-bulk-approve",
        views.shift_request_bulk_approve,
        name="shift-request-bulk-approve",
    ),
    path(
        "shift-request-delete/<int:id>/",
        views.shift_request_delete,
        name="shift-request-delete",
    ),
    path(
        "shift-request-bulk-delete",
        views.shift_request_bulk_delete,
        name="shift-request-bulk-delete",
    ),
    path("notifications", views.notifications, name="notifications"),
    path("clear-notifications", views.clear_notification, name="clear-notifications"),
    path("read-notifications", views.read_notifications, name="read-notifications"),
    path("all-notifications", views.all_notifications, name="all-notifications"),
    path(
        "delete-notifications/<id>/",
        views.delete_notification,
        name="delete-notifications",
    ),
    path("settings/currency/", views.settings, name="currency-settings"),
    path(
        "settings/attendance-settings-view/",
        views.validation_condition_view,
        name="attendance-settings-view",
    ),
    path(
        "settings/attendance-settings-create/",
        views.validation_condition_create,
        name="attendance-settings-create",
    ),
    path(
        "settings/attendance-settings-update/<int:obj_id>/",
        views.validation_condition_update,
        name="attendance-settings-update",
    ),
    path(
        "rwork-individual-view/<int:instance_id>/",
        views.rotating_work_individual_view,
        name="rwork-individual-view",
    ),
    path(
        "rshit-individual-view/<int:instance_id>/",
        views.rotating_shift_individual_view,
        name="rshift-individual-view",
    ),
    path("shift-select/", views.shift_select, name="shift-select"),
    path(
        "shift-select-filter/",
        views.shift_select_filter,
        name="shift-select-filter",
    ),
    path("work-type-select/", views.work_type_select, name="work-type-select"),
    path(
        "work-type-filter/",
        views.work_type_select_filter,
        name="work-type-select-filter",
    ),
    path("r-shift-select/", views.rotating_shift_select, name="r-shift-select"),
    path(
        "r-shift-select-filter/",
        views.rotating_shift_select_filter,
        name="r-shift-select-filter",
    ),
    path(
        "r-work-type-select/",
        views.rotating_work_type_select,
        name="r-work-type-select",
    ),
    path(
        "r-work-type-filter/",
        views.rotating_work_type_select_filter,
        name="r-work-type-select-filter",
    ),
]
