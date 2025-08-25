from django.apps import apps
from django.urls import path

from horilla_meet import cbv

from . import views

urlpatterns = [
    path(
        "gmeet-setting/",
        cbv.GMeetCredentialSectionView.as_view(),
        name="gmeet-setting",
    ),
    path(
        "gmeet-setting-nav",
        cbv.GmeetCredentialNavView.as_view(),
        name="gmeet-setting-nav",
    ),
    path(
        "gmeet-setting-list-view",
        cbv.GmeetCredentialListView.as_view(),
        name="gmeet-setting-list-view",
    ),
    path(
        "create-gmeet-credentials",
        cbv.GoogleCredentialsFormView.as_view(),
        name="create-gmeet-credentials",
    ),
    path(
        "update-gmeet-credentials/<int:pk>/",
        cbv.GoogleCredentialsFormView.as_view(),
        name="update-gmeet-credentials",
    ),
    path(
        "delete-gmeet-credentials/<int:obj_id>/",
        views.delete_google_credentials,
        name="delete-gmeet-credentials",
    ),
    path(
        "gmeet-view/",
        cbv.GmeetSectionView.as_view(),
        name="gmeet-view",
    ),
    path(
        "gmeet-list-view",
        cbv.GmeetListView.as_view(),
        name="gmeet-list-view",
    ),
    path(
        "gmeet-nav-view",
        cbv.GmeetNavView.as_view(),
        name="gmeet-nav-view",
    ),
    path(
        "create-gmeet/",
        cbv.GmeetFormView.as_view(),
        name="create-gmeet",
    ),
    path(
        "update-gmeet/<int:pk>/",
        cbv.GmeetFormView.as_view(),
        name="update-gmeet",
    ),
    path(
        "gmeet-detail-view/<int:pk>/",
        cbv.GmeetDetailedView.as_view(),
        name="gmeet-detail-view",
    ),
    path(
        "delete-gmeet/<int:obj_id>/",
        views.delete_google_credentials,
        name="delete-gmeet",
    ),
    path(
        "authenticate-gmeet/",
        views.google_authenticate,
        name="authenticate-gmeet",
    ),
    path(
        "auth-callback/",
        views.google_auth_callback,
        name="auth-callback",
    ),
    path(
        "create-google-meet/",
        views.create_google_meet_link,
        name="create-google-meet",
    ),
    path(
        "delete-google-meet/<int:id>",
        views.delete_google_meet,
        name="delete-google-meet",
    ),
]

if apps.is_installed("recruitment"):
    urlpatterns += [
        path(
            "create-interview-google-meeting",
            views.create_inteview_google_meeting,
            name="create-interview-google-meeting",
        ),
    ]

if apps.is_installed("pms"):
    urlpatterns += [
        path(
            "create-pms-google-meeting",
            views.create_pms_google_meeting,
            name="create-pms-google-meeting",
        ),
    ]
