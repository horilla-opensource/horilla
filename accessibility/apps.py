from django.apps import AppConfig


class AccessibilityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accessibility"

    def ready(self) -> None:
        from accessibility import signals
        from horilla.urls import include, path, urlpatterns

        urlpatterns.append(
            path("", include("accessibility.urls")),
        )
        return super().ready()
