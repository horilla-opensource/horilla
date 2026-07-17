from django.urls import path

from hydra_documents import views


urlpatterns = [
    path(
        "types/",
        views.private_document_type_list,
        name="hydra-private-document-type-list",
    ),
    path(
        "types/create/",
        views.private_document_type_form,
        name="hydra-private-document-type-create",
    ),
    path(
        "types/<uuid:type_uuid>/edit/",
        views.private_document_type_form,
        name="hydra-private-document-type-update",
    ),
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
    path(
        "<uuid:document_uuid>/legal-hold/",
        views.private_document_legal_hold,
        name="hydra-private-document-legal-hold",
    ),
    path(
        "<uuid:document_uuid>/delete/",
        views.private_document_delete,
        name="hydra-private-document-delete",
    ),
]
