from django.apps import AppConfig


class HydraApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_api"

    def ready(self):
        """
        Initialize API documentation when the app is ready
        """
        # Import and register API documentation components
        import hydra_api.schema  # noqa
