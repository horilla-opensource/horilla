from django.urls import path

from project.models import Project
from . import views
urlpatterns = [
    # Dashboard
    path('project-dashboard-view',views.dashboard_view,name='project-dashboard-view'),
    path('project-status-chart',views.project_status_chart,name='project-status-chart'),
    path('task-status-chart',views.task_status_chart,name='task-status-chart'),
    path(
        'project-detailed-view/<int:project_id>/',
        views.project_detailed_view,
        name='project-detailed-view'
    ),
    
    # Project
    path('project-view/',views.project_view,name='project-view'),
    path("create-project", views.create_project, name="create-project"),
    path(
        "update-project/<int:project_id>/",
         views.project_update, 
         name="update-project"
    ),
    path("delete-project/<int:project_id>/", views.project_delete, name="delete-project"),
    path("project-filter", views.project_filter, name="project-filter"),
    path("project-import", views.project_import, name="project-import"),
    path("project-bulk-export",views.project_bulk_export,name="project-bulk-export"),
    path("project-bulk-archive",views.project_bulk_archive,name="project-bulk-archive"),
    path("project-bulk-delete",views.project_bulk_delete,name="project-bulk-delete"),
    path('project-archive/<int:project_id>/',views.project_archive,name='project-archive'),

    
    # Task
    path('task-view/<int:project_id>/',views.task_view,name='task-view',kwargs={"model":Project}),
    path('create-task/<int:stage_id>/',views.create_task,name='create-task'),
    path('create-task-in-project/<int:project_id>/',views.create_task_in_project,name='create-task-in-project'),
    path('update-task/<int:task_id>/',views.update_task,name='update-task'),
    path('delete-task/<int:task_id>/',views.delete_task,name='delete-task'),
    path('task-details/<int:task_id>/',views.task_details,name='task-details'),
    path('task-filter/<int:project_id>/',views.task_filter,name='task-filter'),
    path('task-stage-change',views.task_stage_change,name='task-stage-change'),
    path('task-timesheet/<int:task_id>/',views.task_timesheet,name='task-timesheet'),
    path("create-timesheet-task/<int:task_id>/",views.create_timesheet_task,name="create-timesheet-task"),
    path("update-timesheet-task/<int:timesheet_id>/",views.update_timesheet_task,name="update-timesheet-task"),
    path('drag-and-drop-task',views.drag_and_drop_task,name='drag-and-drop-task'),
 
    # Task-all
    path('task-all',views.task_all,name='task-all'),
    path('create-task-all',views.task_all_create,name='create-task-all'),
    path('update-task-all/<int:task_id>/',views.update_task_all,name='update-task-all'),
    path('task-all-filter/',views.task_all_filter,name='task-all-filter'),
    path("task-all-bulk-archive",views.task_all_bulk_archive,name="task-all-bulk-archive"),
    path("task-all-bulk-delete",views.task_all_bulk_delete,name="task-all-bulk-delete"),
    path('task-all-archive/<int:task_id>/',views.task_all_archive,name='task-all-archive'),

    

    # Project stage
    path('create-project-stage/<int:project_id>/',views.create_project_stage,name='create-project-stage'),
    path('update-project-stage/<int:stage_id>/',views.update_project_stage,name='update-project-stage'),
    path('delete-project-stage/<int:stage_id>/',views.delete_project_stage,name='delete-project-stage'),
    path('get-stages',views.get_stages,name="get-stages"),
    path('create-stage-taskall',views.create_stage_taskall,name='create-stage-taskall'),
    path('drag-and-drop-stage',views.drag_and_drop_stage,name='drag-and-drop-stage'),


    # Timesheet  
    path("view-time-sheet", views.time_sheet_view, name="view-time-sheet"),
    path("create-time-sheet", views.time_sheet_creation, name="create-time-sheet"),
    path(
        "update-time-sheet/<int:time_sheet_id>/",
        views.time_sheet_update,
        name="update-time-sheet",
    ),
    path(
        "delete-time-sheet-ajax/<int:time_sheet_id>/",
        views.time_sheet_delete_ajax,
        name="delete-time-sheet-ajax",
    ),
    path("filter-time-sheet", views.time_sheet_filter, name="filter-time-sheet"),
    path("time-sheet-initial", views.time_sheet_initial, name="time-sheet-initial"),

     path("view-time-sheet", views.time_sheet_view, name="view-time-sheet"),
    path("create-time-sheet", views.time_sheet_creation, name="create-time-sheet"),
    path(
        "create-project-time-sheet",
        views.time_sheet_project_creation,
        name="create-project-time-sheet",
    ),
    path(
        "create-task-time-sheet",
        views.time_sheet_task_creation,
        name="create-task-time-sheet",
    ),
    path(
        "update-time-sheet/<int:time_sheet_id>/",
        views.time_sheet_update,
        name="update-time-sheet",
    ),
    path(
        "delete-time-sheet/<int:time_sheet_id>/",
        views.time_sheet_delete,
        name="delete-time-sheet",
    ),
    path("filter-time-sheet", views.time_sheet_filter, name="filter-time-sheet"),
    path("time-sheet-initial", views.time_sheet_initial, name="time-sheet-initial"),
    path(
        "personal-time-sheet-view/<int:emp_id>/",
        views.personal_time_sheet_view,
        name="personal-time-sheet-view",
    ),
    path("personal-time-sheet/", views.personal_time_sheet, name="personal-time-sheet"),
    path("view-single-time-sheet/<int:time_sheet_id>", views.time_sheet_single_view, name="view-single-time-sheet"),
    path('time-sheet-bulk-delete',views.time_sheet_bulk_delete,name="time-sheet-bulk-delete"),


]
