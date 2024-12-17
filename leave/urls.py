from django import views
from django.apps import apps
from django.urls import path

from base.views import object_duplicate
from employee.models import Employee
from leave.forms import RestrictLeaveForm

from . import models, views

urlpatterns = [
    path("type-creation", views.leave_type_creation, name="type-creation"),
    path("type-view/", views.leave_type_view, name="type-view"),
    path(
        "leave-type-individual-view/<int:id>",
        views.leave_type_individual_view,
        name="leave-type-individual-view",
    ),
    path(
        "type-update/<int:id>",
        views.leave_type_update,
        name="type-update",
        kwargs={"model": models.LeaveType},
    ),
    path("type-delete/<int:obj_id>", views.leave_type_delete, name="type-delete"),
    path("type-filter", views.leave_type_filter, name="type-filter"),
    path("request-creation", views.leave_request_creation, name="request-creation"),
    path(
        "get-employee-leave-types",
        views.get_employee_leave_types,
        name="get-employee-leave-types",
    ),
    path(
        "leave-request-creation/<int:type_id>/<int:emp_id>",
        views.leave_request_creation,
        name="leave-request-creation",
    ),
    path(
        "leave-requests-info-export",
        views.leave_requests_export,
        name="leave-requests-info-export",
    ),
    path("request-view/", views.leave_request_view, name="request-view"),
    path(
        "request-approve/<int:id>", views.leave_request_approve, name="request-approve"
    ),
    path(
        "request-approve/<int:id>/<int:emp_id>",
        views.leave_request_approve,
        name="request-approve",
    ),
    path(
        "leave-requests-bulk-approve",
        views.leave_request_bulk_approve,
        name="leave-requests-bulk-approve",
    ),
    path(
        "leave-requests-bulk-reject",
        views.leave_bulk_reject,
        name="leave-requests-bulk-reject",
    ),
    path("request-cancel/<int:id>", views.leave_request_cancel, name="request-cancel"),
    path(
        "request-cancel/<int:id>/<int:emp_id>",
        views.leave_request_cancel,
        name="request-cancel",
    ),
    path("request-update/<int:id>", views.leave_request_update, name="request-update"),
    path("request-delete/<int:id>", views.leave_request_delete, name="request-delete"),
    path("user-request/<int:id>", views.user_leave_request, name="user-request"),
    path("request-filter", views.leave_request_filter, name="request-filter"),
    path("assign", views.leave_assign, name="assign"),
    path("assign-one/<int:obj_id>", views.leave_assign_one, name="assign-one"),
    path("assign-view/", views.leave_assign_view, name="assign-view"),
    path(
        "available-leave-single-view/<int:obj_id>/",
        views.available_leave_single_view,
        name="available-leave-single-view",
    ),
    path(
        "available-leave-update/<int:id>",
        views.available_leave_update,
        name="available-leave-update",
    ),
    path("assign-delete/<int:obj_id>", views.leave_assign_delete, name="assign-delete"),
    path(
        "assigned-leave-bulk-delete",
        views.leave_assign_bulk_delete,
        name="assigned-leave-bulk-delete",
    ),
    path(
        "assign-leave-type-excel",
        views.assign_leave_type_excel,
        name="assign-leave-type-excel",
    ),
    path(
        "assign-leave-type-info-import",
        views.assign_leave_type_import,
        name="assign-leave-type-info-import",
    ),
    path(
        "assigned-leaves-info-export",
        views.assigned_leaves_export,
        name="assigned-leaves-info-export",
    ),
    path("assign-filter", views.leave_assign_filter, name="assign-filter"),
    path(
        "get-restrict-job-positions",
        views.get_job_positions,
        name="get-restrict-job-positions",
    ),
    path("restrict-view", views.restrict_view, name="restrict-view"),
    path("restrict-filter", views.restrict_filter, name="restrict-filter"),
    path("restrict-creation", views.restrict_creation, name="restrict-creation"),
    path("restrict-update/<int:id>", views.restrict_update, name="restrict-update"),
    path("restrict-delete/<int:id>", views.restrict_delete, name="restrict-delete"),
    path(
        "restrict-days-bulk-delete",
        views.restrict_days_bulk_delete,
        name="restrict-days-bulk-delete",
    ),
    path(
        "restrict-day-select-filter",
        views.restrict_day_select_filter,
        name="restrict-day-select-filter",
    ),
    path("restrict-day-select", views.restrict_day_select, name="restrict-day-select"),
    path("user-leave-filter", views.user_leave_filter, name="user-leave-filter"),
    path("user-request-view/", views.user_request_view, name="user-request-view"),
    path(
        "user-request-update/<int:id>",
        views.user_request_update,
        name="user-request-update",
    ),
    path(
        "user-request-delete/<int:id>",
        views.user_request_delete,
        name="user-request-delete",
    ),
    path(
        "user-request-cancel/<int:id>",
        views.user_leave_cancel,
        name="user-request-cancel",
    ),
    path("one-request-view/<int:id>", views.one_request_view, name="one-request-view"),
    path("user-request-filter", views.user_request_filter, name="user-request-filter"),
    path("user-request-one/<int:id>", views.user_request_one, name="user-request-one"),
    path("employee-leave", views.employee_leave, name="employee-leave"),
    path("overall-leave", views.overall_leave, name="overall-leave"),
    path("leave-dashboard", views.dashboard, name="leave-dashboard"),
    path(
        "leave-employee-dashboard",
        views.employee_dashboard,
        name="leave-employee-dashboard",
    ),
    path("available-leaves", views.available_leave_chart, name="available-leaves"),
    path(
        "dashboard-leave-requests",
        views.dashboard_leave_request,
        name="dashboard-leave-requests",
    ),
    path(
        "employee-leave-chart", views.employee_leave_chart, name="employee-leave-chart"
    ),
    path(
        "department-leave-chart",
        views.department_leave_chart,
        name="department-leave-chart",
    ),
    path("leave-type-chart", views.leave_type_chart, name="leave-type-chart"),
    path("leave-over-period", views.leave_over_period, name="leave-over-period"),
    path(
        "leave-request-create", views.leave_request_create, name="leave-request-create"
    ),
    path(
        "leave-allocation-request-view/",
        views.leave_allocation_request_view,
        name="leave-allocation-request-view",
    ),
    path(
        "leave-allocation-request-create",
        views.leave_allocation_request_create,
        name="leave-allocation-request-create",
    ),
    path(
        "leave-allocation-request-filter",
        views.leave_allocation_request_filter,
        name="leave-allocation-request-filter",
    ),
    path(
        "leave-allocation-request-single-view/<int:req_id>",
        views.leave_allocation_request_single_view,
        name="leave-allocation-request-single-view",
    ),
    path(
        "leave-allocation-request-update/<int:req_id>",
        views.leave_allocation_request_update,
        name="leave-allocation-request-update",
    ),
    path(
        "leave-allocation-request-approve/<int:req_id>",
        views.leave_allocation_request_approve,
        name="leave-allocation-request-approve",
    ),
    path(
        "leave-allocation-request-reject/<int:req_id>",
        views.leave_allocation_request_reject,
        name="leave-allocation-request-reject",
    ),
    path(
        "leave-allocation-request-delete/<int:req_id>",
        views.leave_allocation_request_delete,
        name="leave-allocation-request-delete",
    ),
    path(
        "leave-allocation-request-view/",
        views.leave_allocation_request_view,
        name="leave-allocation-request-view",
    ),
    path(
        "leave-allocation-request-filter",
        views.leave_allocation_request_filter,
        name="leave-allocation-request-filter",
    ),
    path(
        "leave-allocation-request-update/<int:req_id>",
        views.leave_allocation_request_update,
        name="leave-allocation-request-update",
    ),
    path(
        "leave-allocation-request-approve/<int:req_id>",
        views.leave_allocation_request_approve,
        name="leave-allocation-request-approve",
    ),
    path(
        "assigned-leave-select/",
        views.assigned_leave_select,
        name="assigned-leave-select",
    ),
    path(
        "assigned-leave-select-filter/",
        views.assigned_leave_select_filter,
        name="assigned-leave-select-filter",
    ),
    path(
        "leave-request-bulk-delete",
        views.leave_request_bulk_delete,
        name="leave-request-bulk-delete",
    ),
    path(
        "leave-request-select",
        views.leave_request_select,
        name="leave-request-select",
    ),
    path(
        "leave-request-select-filter",
        views.leave_request_select_filter,
        name="leave-request-select-filter",
    ),
    path(
        "user-request-bulk-delete",
        views.user_request_bulk_delete,
        name="user-request-bulk-delete",
    ),
    path(
        "user-request-select",
        views.user_request_select,
        name="user-request-select",
    ),
    path(
        "user-request-select-filter",
        views.user_request_select_filter,
        name="user-request-select-filter",
    ),
    path(
        "employee-available-leave-count",
        views.employee_available_leave_count,
        name="employee-available-leave-count",
    ),
    path(
        "leave-request-add-comment/<int:leave_id>/",
        views.create_leaverequest_comment,
        name="leave-request-add-comment",
    ),
    path(
        "leave-request-view-comment/<int:leave_id>/",
        views.view_leaverequest_comment,
        name="leave-request-view-comment",
    ),
    path(
        "leave-request-delete-comment/<int:comment_id>/",
        views.delete_leaverequest_comment,
        name="leave-request-delete-comment",
    ),
    path(
        "delete-leave-comment-file/",
        views.delete_leave_comment_file,
        name="delete-leave-comment-file",
    ),
    path(
        "allocation-request-add-comment/<int:leave_id>/",
        views.create_allocationrequest_comment,
        name="allocation-request-add-comment",
    ),
    path(
        "allocation-request-view-comment/<int:leave_id>/",
        views.view_allocationrequest_comment,
        name="allocation-request-view-comment",
    ),
    path(
        "allocation-request-delete-comment/<int:comment_id>/",
        views.delete_allocationrequest_comment,
        name="allocation-request-delete-comment",
    ),
    path(
        "delete-allocation-comment-file/",
        views.delete_allocation_comment_file,
        name="delete-allocation-comment-file",
    ),
    path(
        "view-clashes/<int:leave_request_id>/", views.view_clashes, name="view-clashes"
    ),
    path(
        "compensatory-leave-settings-view/",
        views.compensatory_leave_settings_view,
        name="compensatory-leave-settings-view",
    ),
    path(
        "enable-compensatory-leave",
        views.enable_compensatory_leave,
        name="enable-compensatory-leave",
    ),
    path(
        "employee-past-leave-restriction/",
        views.employee_past_leave_restriction,
        name="employee-past-leave-restriction",
    ),
    path(
        "leave-tab/<int:obj_id>/",
        views.employee_view_individual_leave_tab,
        name="leave-tab",
        kwargs={"model": Employee},
    ),
    path(
        "leave-request-and-approve",
        views.leave_request_and_approve,
        name="leave-request-and-approve",
    ),
    path(
        "leave-allocation-approve",
        views.leave_allocation_approve,
        name="leave-allocation-approve",
    ),
    path(
        "cut-penalty/<int:instance_id>/",
        views.cut_available_leave,
        name="leave-cut-penalty",
    ),
    path(
        "duplicate-restrict-leave/<int:obj_id>/",
        object_duplicate,
        name="duplicate-restrict-leave",
        kwargs={
            "model": models.RestrictLeave,
            "form": RestrictLeaveForm,
            "template": "leave/restrict/restrict_form.html",
        },
    ),
]

if apps.is_installed("recruitment"):
    urlpatterns.extend(
        [
            path(
                "check-interview-conflicts",
                views.check_interview_conflicts,
                name="check-interview-conflicts",
            ),
        ]
    )

if apps.is_installed("attendance"):

    urlpatterns.extend(
        [
            path(
                "get-leave-attendance-dates",
                views.get_leave_attendance_dates,
                name="get-leave-attendance-dates",
            ),
            path(
                "view-compensatory-leave",
                views.view_compensatory_leave,
                name="view-compensatory-leave",
            ),
            path(
                "filter-compensatory-leave",
                views.filter_compensatory_leave,
                name="filter-compensatory-leave",
            ),
            path(
                "create-compensatory-leave",
                views.create_compensatory_leave,
                name="create-compensatory-leave",
            ),
            path(
                "update-compensatory-leave/<int:comp_id>",
                views.create_compensatory_leave,
                name="update-compensatory-leave",
            ),
            path(
                "delete-compensatory-leave/<int:comp_id>",
                views.delete_compensatory_leave,
                name="delete-compensatory-leave",
            ),
            path(
                "approve-compensatory-leave/<int:comp_id>",
                views.approve_compensatory_leave,
                name="approve-compensatory-leave",
            ),
            path(
                "reject-compensatory-leave/<int:comp_id>",
                views.reject_compensatory_leave,
                name="reject-compensatory-leave",
            ),
            path(
                "compensatory-leave-individual-view/<int:comp_leave_id>",
                views.compensatory_leave_individual_view,
                name="compensatory-leave-individual-view",
            ),
            path(
                "view-compensatory-leave-comment/<int:comp_leave_id>",
                views.view_compensatory_leave_comment,
                name="view-compensatory-leave-comment",
            ),
            path(
                "create-compensatory-leave-comment/<int:comp_leave_id>/",
                views.create_compensatory_leave_comment,
                name="create-compensatory-leave-comment",
            ),
            path(
                "compensatory-request-delete-comment/<int:comment_id>/",
                views.delete_leaverequest_compensatory_comment,
                name="compensatory-request-delete-comment",
            ),
            path(
                "delete-compensatory-comment-file/",
                views.delete_comment_compensatory_file,
                name="delete-compensatory-comment-file",
            ),
        ]
    )
