# webhook_handler/apps.py
from django.apps import AppConfig

class WebhookHandlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webhook_handler'

    def ready(self):
        import webhook_handler.handlers # noqa
