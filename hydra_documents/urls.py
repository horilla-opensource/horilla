from django.urls import path

from hydra_documents import views


urlpatterns = [
    path(
        "candidates/<int:candidate_id>/",
        views.candidate_documents,
        name="hydra-candidate-documents",
    ),
    path(
        "<uuid:document_uuid>/download/",
        views.private_document_download,
        name="hydra-private-document-download",
    ),
]
