from django.apps import AppConfig


class HorillaApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_api"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("api/", include("horilla_api.urls")),
        )
        super().ready()
