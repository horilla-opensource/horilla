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
]
