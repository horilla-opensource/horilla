"""
Django application configuration for the PMS (Performance Management System) app.
"""

from django.apps import AppConfig


class PmsConfig(AppConfig):
    """
    This class provides configuration settings for the PMS app, such as the default
    database field type and the app's name.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "pms"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("pms/", include("pms.urls")),
        )
        super().ready()
        try:
            from pms.signals import start_automation

            start_automation()
        except:
            """
            Migrations are not affected yet
            """
