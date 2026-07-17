from django.urls import path

from hydra_tasks import views


urlpatterns = [
    path("", views.task_list, name="hydra-task-list"),
    path(
        "people/<uuid:person_uuid>/create/",
        views.task_create,
        name="hydra-task-create",
    ),
    path("<uuid:task_uuid>/", views.task_detail, name="hydra-task-detail"),
    path("<uuid:task_uuid>/edit/", views.task_update, name="hydra-task-update"),
    path(
        "<uuid:task_uuid>/reassign/",
        views.task_reassign,
        name="hydra-task-reassign",
    ),
    path(
        "<uuid:task_uuid>/transition/",
        views.task_transition,
        name="hydra-task-transition",
    ),
]
