from django.urls import path

from hydra_people import views


urlpatterns = [
    path("", views.person_list, name="hydra-person-list"),
    path("create/", views.person_create, name="hydra-person-create"),
    path(
        "duplicates/",
        views.duplicate_suggestion_list,
        name="hydra-duplicate-list",
    ),
    path(
        "duplicates/<uuid:suggestion_uuid>/",
        views.duplicate_suggestion_detail,
        name="hydra-duplicate-detail",
    ),
    path(
        "duplicates/<uuid:suggestion_uuid>/preview/",
        views.duplicate_merge_preview,
        name="hydra-duplicate-preview",
    ),
    path(
        "duplicates/<uuid:suggestion_uuid>/merge/",
        views.duplicate_merge_commit,
        name="hydra-duplicate-commit",
    ),
    path(
        "duplicates/<uuid:suggestion_uuid>/dismiss/",
        views.duplicate_suggestion_dismiss,
        name="hydra-duplicate-dismiss",
    ),
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
