"""
Django application configuration for the biometric app.
"""

from django.apps import AppConfig


class BiometricConfig(AppConfig):
    """
    This class defines the configuration for the biometric Django app. It sets the
    default auto field to use a BigAutoField for model primary keys.

    Attributes:
        default_auto_field (str): The default auto field to use for model primary keys.
        name (str): The name of the Django app, which is 'biometric'.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "biometric"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("biometric/", include("biometric.urls")),
        )

        from biometric import sidebar

        super().ready()
