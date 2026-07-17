from django.urls import path

from hydra_notifications import views


urlpatterns = [
    path("", views.notification_center, name="hydra-notification-center"),
    path("read-all/", views.notification_read_all, name="hydra-notification-read-all"),
    path("preferences/", views.notification_preferences, name="hydra-notification-preferences"),
    path(
        "<uuid:envelope_uuid>/open/",
        views.notification_open,
        name="hydra-notification-open",
    ),
    path(
        "<uuid:envelope_uuid>/read/",
        views.notification_read,
        name="hydra-notification-read",
    ),
    path(
        "<uuid:envelope_uuid>/unread/",
        views.notification_unread,
        name="hydra-notification-unread",
    ),
    path(
        "<uuid:envelope_uuid>/archive/",
        views.notification_archive,
        name="hydra-notification-archive",
    ),
    path(
        "<uuid:envelope_uuid>/restore/",
        views.notification_restore,
        name="hydra-notification-restore",
    ),
]
