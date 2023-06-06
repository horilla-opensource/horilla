"""
urls.py

This page is used to map request or url path with function

"""
from django.urls import path
from . import views

urlpatterns = [
    path("attendance-create", views.attendance_create, name="attendance-create"),
    path("attendance-view", views.attendance_view, name="attendance-view"),
    path("attendance-search", views.attendance_search, name="attendance-search"),
    path(
        "attendance-update/<int:obj_id>/", views.attendance_update, name="attendance-update"
    ),
    path(
        "attendance-delete/<int:obj_id>/", views.attendance_delete, name="attendance-delete"
    ),
    path(
        "attendance-bulk-delete",
        views.attendance_bulk_delete,
        name="attendance-bulk-delete",
    ),
    path(
        "attendance-overtime-create",
        views.attendance_overtime_create,
        name="attendance-overtime-create",
    ),
    path(
        "attendance-overtime-view",
        views.attendance_overtime_view,
        name="attendance-overtime-view",
    ),
    path(
        "attendance-overtime-search",
        views.attendance_overtime_search,
        name="attendance-ot-search",
    ),
    path(
        "attendance-overtime-update/<int:obj_id>/",
        views.attendance_overtime_update,
        name="attendance-overtime-update",
    ),
    path(
        "attendance-overtime-delete/<int:obj_id>/",
        views.attendance_overtime_delete,
        name="attendance-overtime-delete",
    ),
    path(
        "attendance-activity-view",
        views.attendance_activity_view,
        name="attendance-activity-view",
    ),
    path(
        "attendance-activity-search",
        views.attendance_activity_search,
        name="attendance-activity-search",
    ),
    path(
        "attendance-activity-delete/<int:obj_id>/",
        views.attendance_activity_delete,
        name="attendance-activity-delete",
    ),
    path("view-my-attendance", views.view_my_attendance, name="view-my-attendance"),
    path(
        "filter-own-attendance",
        views.filter_own_attendance,
        name="filter-own-attendance",
    ),
    path(
        "own-attendance-filter", views.own_attendance_sort, name="own-attendance-filter"
    ),
    path("clock-in", views.clock_in, name="clock-in"),
    path("clock-out", views.clock_out, name="clock-out"),
    path(
        "late-come-early-out-view",
        views.late_come_early_out_view,
        name="late-come-early-out-view",
    ),
    path(
        "late-come-early-out-search",
        views.late_come_early_out_search,
        name="late-come-early-out-search",
    ),
    path(
        "late-come-early-out-delete/<int:obj_id>/",
        views.late_come_early_out_delete,
        name="late-come-early-out-delete",
    ),
    path(
        "validation-condition-create",
        views.validation_condition_create,
        name="validation-condition-create",
    ),
    path(
        "validation-condition-update/<int:obj_id>/",
        views.validation_condition_update,
        name="validation-condition-update",
    ),
    path(
        "validation-condition-delete/<int:obj_id>/",
        views.validation_condition_delete,
        name="validation-condition-delete",
    ),
    path(
        "validate-bulk-attendance",
        views.validate_bulk_attendance,
        name="validate-bulk-attendance",
    ),
    path(
        "validate-this-attendance/<int:obj_id>/",
        views.validate_this_attendance,
        name="validate-this-attendance",
    ),
    path(
        "revalidate-this-attendance/<int:obj_id>/",
        views.revalidate_this_attendance,
        name="revalidate-this-attendance",
    ),
    path("approve-overtime/<int:obj_id>/", views.approve_overtime, name="approve-overtime"),
    path(
        "approve-bulk-overtime",
        views.approve_bulk_overtime,
        name="approve-bulk-overtime",
    ),
    path("dashboard", views.dashboard, name="dashboard"),
    path(
        "dashboard-attendance", views.dashboard_attendance, name="dashboard-attendance"
    ),
]
