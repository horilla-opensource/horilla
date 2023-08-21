"""
apps.py
"""
from django.apps import AppConfig


class RecruitmentConfig(AppConfig):
    """
    AppConfig for the 'recruitment' app.

    This class represents the configuration for the 'recruitment' app. It provides
    the necessary settings and metadata for the app.

    Attributes:
        default_auto_field (str): The default auto field to use for model field IDs.
        name (str): The name of the app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "recruitment"
