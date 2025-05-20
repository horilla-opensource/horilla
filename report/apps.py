from django.apps import AppConfig


class ReportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "report"

    def ready(self) -> None:
        ready = super().ready()
        from django.urls import include, path

        from horilla.horilla_settings import APPS
        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("report/", include("report.urls")),
        )

        return ready
