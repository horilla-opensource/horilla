from django.apps import AppConfig


class HydraBackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_backup"
    label = "horilla_backup"

    def ready(self):
        from django.urls import include, path

        from hydra.urls import urlpatterns
        from hydra_backup import views

        urlpatterns.append(
            path("backup/", include("hydra_backup.urls")),
        )
        # Add root-level callback URL to match OAuth redirect URI
        urlpatterns.append(
            path(
                "google/callback/", views.gdrive_callback, name="gdrive_callback_root"
            ),
        )
        super().ready()
