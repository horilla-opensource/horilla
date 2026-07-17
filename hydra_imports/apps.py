from django.apps import AppConfig


class HydraImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_imports"
    verbose_name = "Hydra Imports"

    def ready(self):
        from hydra.hydra_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
