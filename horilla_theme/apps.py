"""
AppConfig for the horilla_theme app
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaThemeConfig(AppConfig):
    """App configuration class for horilla_theme."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_theme"
    verbose_name = _("Theme Manager")

    def ready(self):
        """Run app initialization logic (executed after Django setup).
        Used to auto-register URLs and connect signals if required.
        """
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("theme/", include("horilla_theme.urls")),
            )

            __import__("horilla_theme.signals")
        except Exception as e:
            import logging

            logging.warning("HorillaThemeConfig.ready failed: %s", e)

        super().ready()
