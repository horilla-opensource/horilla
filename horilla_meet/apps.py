from django.apps import AppConfig
from django.conf import settings


class HorillaMeetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_meet"
    verbose_name = "Horilla Meet"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns
        from horilla_meet import signals

        settings.APPS.append("horilla_meet")

        urlpatterns.append(
            path("meet/", include("horilla_meet.urls")),
        )
        super().ready()
