from django.apps import AppConfig


class BackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_backup"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns
        from horilla_backup import views

        urlpatterns.append(
            path("backup/", include("horilla_backup.urls")),
        )
        # Add root-level callback URL to match OAuth redirect URI
        urlpatterns.append(
            path(
                "google/callback/", views.gdrive_callback, name="gdrive_callback_root"
            ),
        )
        super().ready()
