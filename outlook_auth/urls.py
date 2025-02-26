"""
outlook_auth/urls.py
"""

from django.urls import path

from outlook_auth import views
from outlook_auth.cbv import views as cbv

urlpatterns = [
    path("login/", views.outlook_login, name="outlook_login"),
    path("refresh/<int:pk>/", views.refresh_token, name="refresh_outlook_token"),
    path("callback/", views.outlook_callback, name="outlook_callback"),
    path("send_email/", views.send_outlook_email, name="send_email"),
    path(
        "view-outlook-servers/", views.view_outlook_records, name="outlook_view_records"
    ),
    path("outlook-server-nav/", cbv.ServerNav.as_view(), name="outlook_server_nav"),
    path("outlook-server-list/", cbv.ServerList.as_view(), name="outlook_server_list"),
    path(
        "outlook-server-form/", cbv.ServerForm.as_view(), name="outlook_server_create"
    ),
    path(
        "outlook-server-form/<int:pk>/",
        cbv.ServerForm.as_view(),
        name="outlook_server_change",
    ),
]
