from django.apps import AppConfig


class HorillaApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_api"

    def ready(self):
        """
        Initialize API documentation when the app is ready
        """
        # Import and register API documentation components
        import horilla_api.schema  # noqa
