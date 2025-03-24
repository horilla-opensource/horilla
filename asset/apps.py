"""
Module: apps.py
Description: Configuration for the 'asset' app.
"""

from django.apps import AppConfig


class AssetConfig(AppConfig):
    """
    Class: AssetConfig
    Description: Configuration class for the 'asset' app.

    Attributes:
        default_auto_field (str): Default auto-generated field type for primary keys.
        name (str): Name of the app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "asset"

    def ready(self):
        from django.urls import include, path

        from horilla.horilla_settings import APP_URLS, APPS
        from horilla.urls import urlpatterns

        APPS.append("asset")
        urlpatterns.append(
            path("asset/", include("asset.urls")),
        )
        APP_URLS.append("asset.urls")
        super().ready()
