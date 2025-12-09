from django.urls import path
from django.views.generic import TemplateView

from horilla.decorators import login_required
from whatsapp import views
from whatsapp.cbv import whatsapp

urlpatterns = [
    path("", views.whatsapp, name="whatsapp"),
    path(
        "generic-template-creation/<int:id>/",
        views.create_generic_templates,
        name="generic-template-creation",
    ),
    path(
        "whatsapp-credential-view/",
        login_required(
            TemplateView.as_view(template_name="whatsapp/credentials_view.html")
        ),
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
        "whatsapp-credential-delete/",
        whatsapp.delete_credentials,
        name="whatsapp-credential-delete",
    ),
    path(
        "send-test-message/",
        whatsapp.send_test_message,
        name="send-test-message",
    ),
]
