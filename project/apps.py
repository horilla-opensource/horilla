from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project"

    def ready(self):
        from django.urls import include, path

        from horilla.horilla_settings import APP_URLS, APPS
        from horilla.urls import urlpatterns

        if "project" not in APPS:
            APPS.append("project")
        urlpatterns.append(
            path("project/", include("project.urls")),
        )
        if "project.urls" not in APP_URLS:
            APP_URLS.append("project.urls")
        super().ready()
