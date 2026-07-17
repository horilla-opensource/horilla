from django.urls import path

from hydra_people import recruitment_views


urlpatterns = [
    path("", recruitment_views.recruitment_list, name="hydra-recruitment-list"),
    path(
        "applications/<int:candidate_id>/",
        recruitment_views.recruitment_detail,
        name="hydra-recruitment-detail",
    ),
    path(
        "applications/<int:candidate_id>/transition/",
        recruitment_views.recruitment_transition,
        name="hydra-recruitment-transition",
    ),
    path(
        "applications/<int:candidate_id>/link-person/",
        recruitment_views.recruitment_link_person,
        name="hydra-recruitment-link-person",
    ),
    path(
        "people/<uuid:person_uuid>/applications/create/",
        recruitment_views.recruitment_create,
        name="hydra-recruitment-create",
    ),
]
