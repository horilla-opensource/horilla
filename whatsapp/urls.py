from django.urls import path

from whatsapp.cbv import whatsapp

from . import views

urlpatterns = [
    path("", views.whatsapp, name="whatsapp"),
    path(
        "template-creation/",
        views.create_flows,
        name="template-creation",
    ),
    path(
        "generic-template-creation/<int:id>/",
        views.create_generic_templates,
        name="generic-template-creation",
    ),
    # path(
    #     "end-point/",
    #     views.end_point,
    #     name="end-point",
    # ),
    # path(
    #     "leave-request/",
    #     views.end_point,
    #     name="leave-request",
    # ),
    path(
        "whatsapp-credential-view/",
        views.whatsapp_credential_view,
        name="whatsapp-credential-view",
    ),
    path(
        "whatsapp-credential-list/",
        whatsapp.CredentialListView.as_view(),
        name="whatsapp-credential-list",
    ),
    path(
        "whatsapp-credential-nav/",
        whatsapp.CredentialNav.as_view(),
        name="whatsapp-credential-nav",
    ),
    path(
        "whatsapp-credential-create/",
        whatsapp.CredentialForm.as_view(),
        name="whatsapp-credential-create",
    ),
    path(
        "whatsapp-credential-update/<int:pk>/",
        whatsapp.CredentialForm.as_view(),
        name="whatsapp-credential-update",
    ),
    path(
        "whatsapp-credential-delete",
        whatsapp.delete_credentials,
        name="whatsapp-credential-delete",
    ),
    path(
        "send-test-message",
        whatsapp.send_test_message,
        name="send-test-message",
    ),
]
