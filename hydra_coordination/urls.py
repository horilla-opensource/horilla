from django.urls import path

from hydra_coordination import views


urlpatterns = [
    path("coordinator/", views.coordinator_panel, name="hydra-coordinator-panel"),
    path("brigadier/", views.brigadier_panel, name="hydra-brigadier-panel"),
    path("organization/", views.organization, name="hydra-organization"),
    path("locations/create/", views.location_create, name="hydra-location-create"),
    path("sections/create/", views.section_create, name="hydra-section-create"),
    path("teams/create/", views.team_create, name="hydra-team-create"),
    path("scope-grants/create/", views.scope_grant_create, name="hydra-scope-grant-create"),
    path(
        "scope-grants/<int:grant_id>/end/",
        views.scope_grant_end,
        name="hydra-scope-grant-end",
    ),
    path("people/<uuid:person_uuid>/assign/", views.person_assign, name="hydra-person-assign"),
    path(
        "assignments/<int:assignment_id>/end/",
        views.person_assignment_end,
        name="hydra-person-assignment-end",
    ),
]
