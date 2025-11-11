from django.apps import AppConfig
from django.conf import settings


class OnboardingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "onboarding"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        settings.APPS.append("onboarding")
        urlpatterns.append(
            path("onboarding/", include("onboarding.urls")),
        )
        super().ready()
