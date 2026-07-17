from django.urls import path

from hydra_arrivals import views


urlpatterns = [
    path("", views.arrival_list, name="hydra-arrival-list"),
    path(
        "people/<uuid:person_uuid>/create/",
        views.arrival_create,
        name="hydra-arrival-create",
    ),
    path(
        "<uuid:plan_uuid>/",
        views.arrival_detail,
        name="hydra-arrival-detail",
    ),
    path(
        "<uuid:plan_uuid>/edit/",
        views.arrival_update,
        name="hydra-arrival-update",
    ),
    path(
        "<uuid:plan_uuid>/transition/",
        views.arrival_transition,
        name="hydra-arrival-transition",
    ),
    path(
        "<uuid:plan_uuid>/onboarding/start/",
        views.onboarding_handoff_start,
        name="hydra-onboarding-handoff-start",
    ),
    path(
        "<uuid:plan_uuid>/onboarding/reconcile/",
        views.onboarding_handoff_reconcile,
        name="hydra-onboarding-handoff-reconcile",
    ),
    path(
        "<uuid:plan_uuid>/onboarding/tasks/<int:task_id>/",
        views.onboarding_task_update,
        name="hydra-onboarding-task-update",
    ),
]
