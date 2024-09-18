from django.apps import AppConfig


class AccessibilityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accessibility"

    def ready(self) -> None:
        from horilla.urls import urlpatterns, include, path
        from accessibility import signals

        urlpatterns.append(
            path("", include("accessibility.urls")),
        )
        return super().ready()
