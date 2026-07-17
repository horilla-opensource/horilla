from django.apps import AppConfig


class HydraLegalizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_legalization"
    verbose_name = "Hydra Legalization"

    def ready(self):
        from hydra.hydra_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
