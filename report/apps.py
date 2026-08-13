from django.apps import AppConfig


class ReportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "report"

    def ready(self) -> None:
        ready = super().ready()
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("report/", include("report.urls")),
        )

        # Load standard report definitions + optional subscription scheduler
        try:
            import report.metrics  # noqa: F401
        except Exception:
            pass
        try:
            import report.scheduler  # noqa: F401
        except Exception:
            pass

        return ready
