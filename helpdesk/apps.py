from django.apps import AppConfig
from django.conf import settings


class HelpdeskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "helpdesk"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        settings.APPS.append("helpdesk")
        urlpatterns.append(
            path("helpdesk/", include("helpdesk.urls")),
        )
        super().ready()
