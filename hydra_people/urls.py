from django.urls import path

from hydra_people import views


urlpatterns = [
    path("", views.person_list, name="hydra-person-list"),
    path("create/", views.person_create, name="hydra-person-create"),
    path(
        "<uuid:person_uuid>/",
        views.person_detail,
        name="hydra-person-detail",
    ),
    path(
        "<uuid:person_uuid>/edit/",
        views.person_update,
        name="hydra-person-update",
    ),
    path(
        "<uuid:person_uuid>/applications/link/",
        views.candidate_link,
        name="hydra-person-candidate-link",
    ),
    path(
        "<uuid:person_uuid>/convert-to-employee/",
        views.employee_conversion,
        name="hydra-person-employee-conversion",
    ),
]
