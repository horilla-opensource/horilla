from django.urls import path

from hydra_imports import views


urlpatterns = [
    path("candidates/", views.candidate_import_upload, name="hydra-candidate-import"),
    path(
        "candidates/template/",
        views.candidate_import_template,
        name="hydra-candidate-import-template",
    ),
    path(
        "candidates/<uuid:session_uuid>/",
        views.candidate_import_detail,
        name="hydra-candidate-import-detail",
    ),
    path(
        "candidates/<uuid:session_uuid>/apply/",
        views.candidate_import_apply,
        name="hydra-candidate-import-apply",
    ),
]
