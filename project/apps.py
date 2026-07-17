from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project"

    def ready(self):
        from django.urls import include, path

        from hydra.hydra_settings import APP_URLS, APPS
        from hydra.urls import urlpatterns

        APPS.append("project")
        urlpatterns.append(
            path("project/", include("project.urls")),
        )
        APP_URLS.append("project.urls")
        super().ready()
