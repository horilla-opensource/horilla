from django.apps import AppConfig


class HydraTemplatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_templates"
    verbose_name = "Hydra Templates"

    def ready(self):
        from horilla.horilla_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
