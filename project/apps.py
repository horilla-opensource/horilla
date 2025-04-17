from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("project/", include("project.urls")),
        )
        super().ready()
        try:
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path("project/", include("project.urls")),
            )
        except:
            """
            Models not ready yet
            """
