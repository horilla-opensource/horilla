from django.urls import path

from hydra_templates import views


urlpatterns = [
    path("", views.template_list, name="hydra-template-list"),
    path("create/", views.template_create, name="hydra-template-create"),
    path("export/data/", views.template_data_export, name="hydra-template-data-export"),
    path(
        "<uuid:template_uuid>/edit/",
        views.template_update,
        name="hydra-template-update",
    ),
]
