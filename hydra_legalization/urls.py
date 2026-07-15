from django.urls import path

from hydra_legalization import views


urlpatterns = [
    path("", views.legalization_list, name="hydra-legalization-list"),
    path(
        "people/<uuid:person_uuid>/create/",
        views.legalization_create,
        name="hydra-legalization-create",
    ),
    path(
        "<uuid:case_uuid>/",
        views.legalization_detail,
        name="hydra-legalization-detail",
    ),
    path(
        "<uuid:case_uuid>/edit/",
        views.legalization_update,
        name="hydra-legalization-update",
    ),
    path(
        "<uuid:case_uuid>/transition/",
        views.legalization_transition,
        name="hydra-legalization-transition",
    ),
    path(
        "<uuid:case_uuid>/documents/attach/",
        views.legalization_attach_document,
        name="hydra-legalization-attach-document",
    ),
]
