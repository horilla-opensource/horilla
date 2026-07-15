from django.urls import path

from hydra_links import views


urlpatterns = [
    path("", views.public_link_list, name="hydra-public-link-list"),
    path("create/", views.public_link_create, name="hydra-public-link-create"),
    path(
        "<uuid:link_uuid>/edit/",
        views.public_link_update,
        name="hydra-public-link-update",
    ),
]
